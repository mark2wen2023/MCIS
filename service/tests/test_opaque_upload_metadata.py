"""Synthetic opaque files; no OCR, decoder or inference invoked."""
import pytest
from mcis_service.evidence_intake import parser
from .test_evidence_intake_w42 import local,body,URL,counts,save

BIDI=[chr(c) for c in [0x61c,0x200e,0x200f,*range(0x202a,0x202f),*range(0x2066,0x206a)]]

@pytest.mark.parametrize('control',BIDI)
def test_new_bidi_filename_rejected_before_write(local,control):
 c,app=local
 value=body(fileName='photo'+control+'gpj.exe')
 for route in [':preview',':commit']:
  request=value if route==':preview' else {**value,'confirmed':True,'requestDigest':'0'*64}
  response=c.post(URL+route,json=request)
  assert response.status_code==422
  assert response.json()['code']=='INTAKE_FILENAME_DIRECTION'
  assert control not in response.text
 assert counts(app)==(0,0,0)
 assert not list(app.state.settings.blob_dir.rglob('source.bin'))

@pytest.mark.parametrize('field,value',[('mimeType','image/png'),('parsed',True),('ocrStatus','completed')])
def test_caller_cannot_claim_type_or_parsing(local,field,value):
 c,app=local
 assert c.post(URL+':preview',json=body(**{field:value})).status_code==422
 assert counts(app)==(0,0,0)

@pytest.mark.parametrize('name',['photo.png','照片 😀.png','تقرير.pdf','report\u0301.pdf'])
def test_opaque_bytes_never_treated_as_declared_photo(local,name):
 c,_=local;raw=b'<html><script>synthetic-do-not-execute</script></html>'
 request,receipt=save(c,body(raw,fileName=name,category='Photo'))
 assert receipt['metadata']['category']=='Photo'
 assert not any(k in receipt for k in ('mimeType','parsed','ocrStatus'))
 response=c.post(URL+'/'+receipt['requestDigest']+':download',json={'purpose':'synthetic'})
 assert response.content==raw
 assert response.headers['content-type']=='application/octet-stream'
 assert response.headers['x-content-type-options']=='nosniff'


def test_historical_binding_stays_valid():
 # Existing historical validator is intentionally compatible; new ingress is not.
 raw=b'synthetic';metadata=body(raw,fileName='old\u202efile.bin')
 result,binding=parser.preview(metadata,raw,'SYN','Synthetic','Investigator')
 assert binding['fileName']==metadata['fileName']
 assert result['requestDigest']==parser.sha(parser.canonical(binding))
 with pytest.raises(Exception) as err:parser.inputs(metadata)
 assert err.value.status_code==422


def test_legacy_receipt_read_without_new_upload_replay(local,monkeypatch):
 from mcis_service.evidence_intake import router
 c,_=local
 original=router.inputs
 def historical_ingress(request,*,commit=False):
  # Fixture stands in for the previous ingress version, without altering binding bytes.
  return original({**request,'fileName':'fixture-safe.bin'},commit=commit)
 with monkeypatch.context() as patch:
  patch.setattr(router,'inputs',historical_ingress)
  request,receipt=save(c,body(fileName='legacy\u202efile.png'))
 response=c.get(URL+'/'+receipt['requestDigest'])
 assert response.status_code==200 and response.json()['fileName']=='legacy\u202efile.png'
 assert c.post(URL+':commit',json=request).status_code==422
 download=c.post(URL+'/'+receipt['requestDigest']+':download',json={'purpose':'historical read'})
 assert download.status_code==200
