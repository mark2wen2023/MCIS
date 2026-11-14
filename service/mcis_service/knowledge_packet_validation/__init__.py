"""Isolated strict mapping; no routes, writes, or permission grants."""
import copy,hashlib,json,re
from pathlib import Path
from jsonschema import Draft202012Validator
from ..knowledge.router import validate_content,digest
from ..knowledge_archive.validation import strict,utc
class InvalidPacket(ValueError):pass
SCHEMA=json.loads(Path(__file__).with_name('packet-v1.schema.json').read_text())

def sha(raw):return hashlib.sha256(raw).hexdigest()
def check(condition,code):
 if not condition:raise InvalidPacket(code)

def map_packet(raw:bytes):
 """Validate consistency only. Retain complete source packet, refuse formal admission."""
 check(type(raw)is bytes and 0<len(raw)<=262144,'PACKET_BUDGET')
 try:
  p=strict(raw)
  Draft202012Validator(SCHEMA).validate(p)
  content=p['candidate']['content'];validate_content(content)
  utc(p['captureUtc'])
 except Exception as e:raise InvalidPacket('PACKET_SCHEMA') from None
 cd=digest(content);source=content['source'];ss=digest(source)
 b=p['bindings'];loc=p['locator'];decl=p['sourceDeclaration'];pv=p['sourcePreview'];w=p['worksheet'];f=p['freshness']
 check(content['source']['type']=='Public','PUBLIC_DECLARATION_REQUIRED')
 check(p['candidate']['contentDigest']==b['candidateDigest']==w['contentDigest']==f['candidateContentDigest']==cd,'CANDIDATE_BINDING')
 check(w['content']==content,'WORKSHEET_CONTENT')
 check(b['sourceSnapshotDigest']==f['originalSourceDigest']==f['observedSourceDigest']==ss,'SOURCE_SNAPSHOT_BINDING')
 check(content['body']==content['summary']==source['excerpt']==loc['exactExcerpt'],'EXCERPT_BINDING')
 check(loc['exactExcerpt'] in loc['pageExtractedText'],'PAGE_EXCERPT_MISMATCH')
 check(sha(loc['exactExcerpt'].encode())==b['excerptSha256']==loc['excerptSha256'],'EXCERPT_DIGEST')
 check(sha(loc['pageExtractedText'].encode())==loc['pageTextSha256'],'PAGE_DIGEST')
 check(p['materialVersion']==b['sourceFileSha256']==decl['fileSha256']==pv['fileSha256'],'FILE_BINDING')
 check(re.fullmatch('[a-f0-9]{64}',p['materialVersion']) is not None,'FILE_DIGEST')
 check(pv['manifest']==decl,'MANIFEST_BINDING')
 check(sha(json.dumps(decl,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())==pv['manifestDigest'],'MANIFEST_DIGEST')
 check(decl['sourceUrl']==source['url'] and decl['title']==source['title'],'SOURCE_DECLARATION_BINDING')
 check(decl['locators'][0]['pdfPage']==loc['pdfPage'] and decl['locators'][0]['printedPage']==str(loc['printedPage']),'PAGE_LOCATOR_BINDING')
 check(source['locator']==f"PDF第{loc['pdfPage']}页；正文第{loc['printedPage']}页",'LOCATOR_TEXT_BINDING')
 check(f['candidateSourceCapturedUtc']==f['observedSourceCapturedUtc']==p['captureUtc'],'CAPTURE_BINDING')
 return {'profile':'MCIS-PENDING-PACKET-MAPPING-1','candidateContent':copy.deepcopy(content),
 'originEnvelope':copy.deepcopy(p),'originalPacketBytes':raw,'packetSha256':sha(raw),
 'admissionAllowed':False,'authorizationVerified':False,'sourceAuthenticity':'not_verified',
 'sourceBytesChecked':False,'pageContentIndependentlyVerified':False,'persisted':False,
 'missingPrerequisites':['trusted principal and scope','trusted source registration/bytes resolver','atomic origin plus candidate persistence']}
