"""Offline linkage only. Does not import/execute W4, write files or grant admission."""
import hashlib,json
from mcis_service.knowledge_packet_validation import map_packet
class Rejected(ValueError): pass
def sha(b): return hashlib.sha256(b).hexdigest()
def require(ok,code):
 if not ok: raise Rejected(code)
def consume(packet_bytes,pdf_bytes=None,artifact=None,*,expected_tool=None):
 mapped=map_packet(packet_bytes)  # reuse the existing strict packet validator
 p=mapped['originEnvelope']; l=p['locator']
 out={'profile':'MCIS-PENDING-W4-LINK-1','originalPacketBytes':packet_bytes,'candidateContent':mapped['candidateContent'],
      'status':'Candidate','linkStatus':'unknown_no_derivative','sourceAuthenticity':'not_verified',
      'authorizationVerified':False,'admissionAllowed':False,'persisted':False,'parserExecutionVerified':False,
      'printedPageVerified':False,'originalPacketSha256':sha(packet_bytes),'derivativeLink':None}
 if artifact is None:
  require(pdf_bytes is None and expected_tool is None,'PARTIAL_LINK_INPUT');return out
 require(type(pdf_bytes) is bytes and 0<len(pdf_bytes)<=8*1024*1024,'PDF_BYTES_REQUIRED')
 require(type(artifact) is dict,'ARTIFACT_REQUIRED')
 require(artifact.get('format')=='mcis-digital-pdf-text-layer' and type(artifact.get('version')) is int and artifact['version']==1,'DERIVATIVE_VERSION')
 require(artifact.get('method')=='embedded_text_only','METHOD')
 require(type(expected_tool) is str and bool(expected_tool),'TOOL_POLICY_REQUIRED')
 require(artifact.get('tool')==expected_tool==l['extractionTool'],'TOOL_VERSION')
 require(artifact.get('parameters')==['-layout','-enc','UTF-8'],'PARAMETERS')
 require(sha(pdf_bytes)==artifact.get('sourcePdfSha256')==p['materialVersion'],'PDF_SHA')
 require(type(artifact.get('sourceByteLength')) is int and artifact['sourceByteLength']==len(pdf_bytes)==p['sourcePreview']['byteLength'],'PDF_LENGTH')
 pages=artifact.get('pages'); n=artifact.get('pageCount')
 require(type(n) is int and 0<n<=200 and type(pages) is list and len(pages)==n,'PAGE_COUNT')
 total=0
 for index,page in enumerate(pages,1):
  require(type(page) is dict and type(page.get('physicalPage')) is int and page['physicalPage']==index,'PHYSICAL_PAGE_SEQUENCE')
  require(set(page)=={'physicalPage','text','textSha256','byteLength','status'},'PAGE_FIELDS')
  text=page.get('text');require(type(text) is str,'PAGE_TEXT')
  try: raw=text.encode('utf-8')
  except UnicodeError: raise Rejected('PAGE_ENCODING') from None
  total+=len(raw);require(len(raw)<=512*1024 and total<=4*1024*1024,'TEXT_BUDGET')
  require(sha(raw)==page.get('textSha256'),'PAGE_SHA')
  require(type(page.get('byteLength')) is int and len(raw)==page['byteLength'],'PAGE_BYTES')
  require(page.get('status')==('text_layer_present' if text.strip() else 'no_selectable_text'),'PAGE_STATUS')
 require(1<=l['pdfPage']<=n,'PAGE_MISSING'); page=pages[l['pdfPage']-1]
 require(page['text']==l['pageExtractedText'] and page['textSha256']==l['pageTextSha256'],'PACKET_PAGE_BINDING')
 require(page['text'].count(l['exactExcerpt'])==1,'EXCERPT_UNIQUE')
 # Hash defined subset, not arbitrary extension fields or a producer authenticity claim.
 projection={k:artifact[k] for k in ('format','version','sourcePdfSha256','sourceByteLength','method','tool','parameters','pageCount')}
 projection['pages']=[{k:page[k] for k in ('physicalPage','text','textSha256','byteLength','status')} for page in pages]
 digest=sha(json.dumps(projection,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
 out.update(linkStatus='supplied_bytes_aligned_not_authenticated',derivativeLink={
 'format':artifact['format'],'version':1,'artifactProjectionSha256':digest,'tool':expected_tool,
 'parameters':list(artifact['parameters']),'physicalPage':l['pdfPage'],'pageTextSha256':page['textSha256'],
 'excerptSha256':l['excerptSha256'],'sourcePdfSha256':sha(pdf_bytes)})
 return out
