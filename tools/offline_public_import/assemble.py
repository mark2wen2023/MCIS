"""Single admitted public PDF -> local pending review packet. No HTTP/DB/model."""
import argparse,hashlib,json,os,re,subprocess,sys,tempfile,uuid,shutil,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/offline_public_import'))
sys.path.insert(0,str(ROOT/'service'))
sys.path.insert(0,str(ROOT/'tools/pdf_text_layer'))
from derive import run_bounded, DerivationError
import manifest as source_manifest
from mcis_service.knowledge.router import digest
from mcis_service.knowledge.freshness import preview as freshness,PROFILE as FRESH_PROFILE
from mcis_service.knowledge.review_worksheet import build as worksheet
MATERIAL='yangze22-public-report-v1'
SHA='99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f'
PDF=ROOT/'reports/yangze22/report.pdf'
URL='https://www.sh.msa.gov.cn/u/cms/www/202505/191445221747637122775.pdf'
TITLE='长江口深水航道“12·30”“YANGZE 22”轮与“VEGA DREAM”轮碰撞事故调查报告'
class Rejected(ValueError):pass

def sha(raw):return hashlib.sha256(raw).hexdigest()
def assemble(material_id, derivative=None):
 if material_id!=MATERIAL:raise Rejected('UNKNOWN_MATERIAL')
 raw=source_manifest.read_file(PDF,8*1024*1024)
 if sha(raw)!=SHA:raise Rejected('SOURCE_BYTES_CHANGED')
 if derivative is not None:
  try:
   page=derivative['pages'][23]['text'];tool=derivative['tool']
   if type(page)is not str or type(tool)is not str:raise ValueError()
  except (KeyError,IndexError,TypeError,ValueError):raise Rejected('W4_ARTIFACT_INVALID') from None
  if page.count('（四）结论。')!=1 or page.count('八、')!=1:raise Rejected('PAGE_ANCHORS_AMBIGUOUS')
  excerpt=page.split('（四）结论。',1)[1].split('八、',1)[0].strip()
  if not excerpt or '工况正常' not in excerpt:raise Rejected('EXCERPT_NOT_FOUND')
 else:
  # Parse only the checked snapshot; original path cannot change bytes between check and parser.
  with tempfile.TemporaryDirectory() as d:
   local=Path(d)/'source.pdf';local.write_bytes(raw);local.chmod(0o400)
   texttool=shutil.which('pdftotext')
   if not texttool:raise Rejected('TEXT_TOOL_UNAVAILABLE')
   deadline=time.monotonic()+20
   try:
    output,warnings=run_bounded([texttool,'-f','24','-l','24','-layout',str(local),'-'],deadline=deadline,limit=2*1024*1024)
    if warnings.strip():raise Rejected('TEXT_EXTRACTION_WARNING')
    page=output.decode('utf-8','strict')
    if not re.search(r'\n\s*22\s*\f?\s*$',page):raise Rejected('PRINTED_PAGE_NOT_FOUND')
    if page.count('（四）结论。')!=1 or page.count('八、')!=1:raise Rejected('PAGE_ANCHORS_AMBIGUOUS')
    excerpt=page.split('（四）结论。',1)[1].split('八、',1)[0].strip()
    if not excerpt or '工况正常' not in excerpt:raise Rejected('EXCERPT_NOT_FOUND')
    version_out,version_err=run_bounded([texttool,'-v'],deadline=deadline,limit=16384)
    version_lines=(version_err or version_out).decode('utf-8','strict').splitlines()
    if not version_lines:raise Rejected('EXTRACTION_VERSION_UNAVAILABLE')
    tool=version_lines[0]
    if local.read_bytes()!=raw:raise Rejected('SOURCE_BYTES_CHANGED')
   except (DerivationError,UnicodeError) as e:
    raise Rejected('TEXT_EXTRACTION_FAILED') from e
 captured=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
 declaration={'profile':source_manifest.PROFILE,'title':TITLE,'publisher':'上海海事局（既有来源声明，未联网复核）','sourceUrl':URL,'publicationDate':None,'fileSha256':SHA,'locators':[{'pdfPage':24,'printedPage':'22','label':'七、“YANGZE 22”轮操舵系统状况综合分析 / （四）结论。'}]}
 checked=source_manifest.preview(json.dumps(declaration,ensure_ascii=False).encode(),raw)
 content={'kind':'Case','title':'公开报告原文摘录：操舵系统工况结论','summary':excerpt,'body':excerpt,'tags':['公开报告摘录'],
 'applicability':'仅待审原文摘录，不推断本案或其他事故；尚未核实来源及使用范围',
 'source':{'type':'Public','title':TITLE,'url':URL,'locator':'PDF第24页；正文第22页','excerpt':excerpt,'rightsNote':'用户明确授权本报告离线研究使用；非机构发布或训练授权'}}
 cd=digest(content);ss=digest(content['source'])
 packet={'profile':'MCIS-OFFLINE-PENDING-PACKET-1','materialId':MATERIAL,'materialVersion':SHA,
 'sourceDeclaration':declaration,'declarationMeaning':'用户指定的公开研究材料，不等于来源认证或正式发布授权',
 'sourcePreview':checked,'captureUtc':captured,'sourceAuthenticity':'not_verified',
 'locator':{'pdfPage':24,'printedPage':22,'pageExtractedText':page,'pageTextSha256':sha(page.encode()),'exactExcerpt':excerpt,'excerptSha256':sha(excerpt.encode()),'extractionTool':tool,'extractionMode':'embedded_text_not_OCR','visualReview':'pending','note':'标题和适用说明是整理标签；summary/body/excerpt均为同一提取原文，不混入人工判断'},
 'candidate':{'status':'Candidate','content':content,'contentDigest':cd,'creatorIdentity':'not_authenticated','method':'deterministic_original_excerpt_not_LLM'},
 'bindings':{'candidateDigest':cd,'sourceSnapshotDigest':ss,'sourceFileSha256':SHA,'excerptSha256':sha(excerpt.encode())},
 'freshness':freshness({'profile':FRESH_PROFILE,'candidateContent':content,'expectedContentDigest':cd,'candidateSourceCapturedUtc':captured,'observation':{'status':'provided','source':content['source'],'capturedUtc':captured}}),
 'worksheet':worksheet({'content':content,'expectedDigest':cd}),'reviewRecords':[],
 'authorizationVerified':False,'approvalGranted':False,'modelUsed':False,'ocrUsed':False,'networkUsed':False,'formalDatabaseUsed':False,'distribution':'research_internal_pending'}
 if derivative is not None:
  _link(packet,raw,derivative) # reject mismatched/unknown artifacts before returning a packet
 return packet

def _link(packet,raw,derivative):
 # PR74 and existing adapter reused; no second candidate validator.
 try:
  from adapter import consume
 except ImportError:raise Rejected('W4_DEPENDENCY_UNAVAILABLE') from None
 try:return consume(json.dumps(packet,ensure_ascii=False).encode(),raw,derivative,expected_tool='pdftotext version 25.03.0')
 except Exception:raise Rejected('W4_LINK_REJECTED') from None

def assemble_bundle(material_id,derivative=None):
 packet=assemble(material_id,derivative)
 if derivative is None:
  linkage={'linkStatus':'unknown_no_derivative','admissionAllowed':False,'authorizationVerified':False,'sourceAuthenticity':'not_verified','persisted':False}
 else:
  raw=source_manifest.read_file(PDF,8*1024*1024)
  linkage=_link(packet,raw,derivative)
  linkage={k:v for k,v in linkage.items() if k not in ('originalPacketBytes','candidateContent')}
 return {'profile':'MCIS-OFFLINE-PENDING-W4-BUNDLE-1','packet':packet,'derivativeArtifact':derivative,'linkage':linkage,'admissionAllowed':False,'authorizationVerified':False,'formalDatabaseUsed':False}

def write_new(path,packet):
 # Temp file + same-directory link: final name appears complete, never overwrites existing.
 data=json.dumps(packet,ensure_ascii=True,sort_keys=True,indent=2,allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026').encode()+b'\n'
 parent,name=source_manifest.parent_fd(path);temp='.pending-'+uuid.uuid4().hex;created=False
 try:
  fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
  created=True
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.link(temp,name,src_dir_fd=parent,dst_dir_fd=parent,follow_symlinks=False)
  os.fsync(parent)
 finally:
  if created:
   try:os.unlink(temp,dir_fd=parent)
   except FileNotFoundError:pass
  os.close(parent)

def main(args=None):
 p=argparse.ArgumentParser();p.add_argument('--material-id',required=True);p.add_argument('--output',required=True)
 p.add_argument('--bundle',action='store_true',help='Explicit versioned bundle output; legacy output remains unchanged')
 p.add_argument('--derivative',help='Completed local W4 JSON artifact; requires --bundle')
 a=p.parse_args(args)
 if a.derivative and not a.bundle:p.error('--derivative requires explicit --bundle')
 try:
  derivative=None
  if a.derivative:
   from mcis_service.knowledge_archive.validation import strict
   try:derivative=strict(source_manifest.read_file(Path(a.derivative),8*1024*1024))
   except Exception:raise Rejected('W4_ARTIFACT_JSON_INVALID') from None
   if type(derivative)is not dict:raise Rejected('W4_ARTIFACT_OBJECT_REQUIRED')
  result=assemble_bundle(a.material_id,derivative) if a.bundle else assemble(a.material_id)
  write_new(a.output,result)
  print('Pending research output written; no admission/authentication/OCR/LLM. '+('W4 link is byte consistency only.' if derivative is not None else 'W4 linkage UNKNOWN: no derivative provided.'))
  return 0
 except (Rejected,source_manifest.Invalid,ValueError,OSError,subprocess.SubprocessError) as e:
  print('Packet not confirmed: '+type(e).__name__+'; no automatic retry. Inspect destination if I/O failed.',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
