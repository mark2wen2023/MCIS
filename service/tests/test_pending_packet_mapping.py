import copy,json
from pathlib import Path
import pytest
from mcis_service.knowledge_packet_validation import map_packet,InvalidPacket
SAMPLE=Path(__file__).resolve().parent/'fixtures/pending_packet/yangze22-pending.json'
def raw(p):return json.dumps(p,ensure_ascii=False).encode()
@pytest.fixture
def packet():return json.loads(SAMPLE.read_bytes())
def test_real_sample_lossless_and_not_admitted(packet):
 original=SAMPLE.read_bytes();out=map_packet(original)
 assert out['originalPacketBytes']==original and out['originEnvelope']==packet
 assert out['candidateContent']==packet['candidate']['content']
 assert not out['admissionAllowed'] and not out['sourceBytesChecked'] and not out['authorizationVerified'] and not out['persisted']
 assert out['originEnvelope']['sourceDeclaration']==packet['sourceDeclaration']
@pytest.mark.parametrize('path,value',[
 (('approvalGranted',),True),(('authorizationVerified',),True),(('candidate','status'),'Published'),
 (('candidate','contentDigest'),'f'*64),(('bindings','sourceSnapshotDigest'),'0'*64),
 (('locator','exactExcerpt'),'fake'),(('locator','pageExtractedText'),'fake'),
 (('sourceDeclaration','fileSha256'),'f'*64),(('sourcePreview','manifestDigest'),'0'*64),
 (('worksheet','approvalGranted'),True),(('freshness','sourceCurrentnessVerified'),True),
 (('captureUtc',),'invalid'),(('candidate','content','source','url'),'https://example.com'),
])
def test_reject_without_partial_projection_or_mutation(packet,path,value):
 p=copy.deepcopy(packet);node=p
 for key in path[:-1]:node=node[key]
 node[path[-1]]=value;b=raw(p);before=bytes(b)
 with pytest.raises(InvalidPacket):map_packet(b)
 assert b==before and packet==json.loads(SAMPLE.read_bytes())
def test_missing_provenance_not_silently_dropped(packet):
 del packet['sourcePreview']
 with pytest.raises(InvalidPacket):map_packet(raw(packet))
def test_extra_untrusted_fields_rejected(packet):
 packet['approvedBy']='chief'
 with pytest.raises(InvalidPacket):map_packet(raw(packet))
def test_duplicate_json_keys_rejected():
 with pytest.raises(InvalidPacket):map_packet(b'{"profile":1,"profile":2}')
def test_output_mutation_does_not_change_other_fields(packet):
 out=map_packet(raw(packet));out['candidateContent']['title']='changed'
 assert out['originEnvelope']['candidate']['content']['title']==packet['candidate']['content']['title']
 assert json.loads(out['originalPacketBytes'])==packet
def test_no_claim_of_authentication_for_consistent_input(packet):
 out=map_packet(raw(packet));assert out['sourceAuthenticity']=='not_verified'
 assert out['missingPrerequisites'] and not out['pageContentIndependentlyVerified']
@pytest.mark.parametrize('data',[b'',b'x'*262145,'not-bytes'])
def test_budget(data):
 with pytest.raises(InvalidPacket):map_packet(data)

def test_packaged_fixture_integrity_and_scope():
 import hashlib
 manifest=json.loads(SAMPLE.with_name('manifest.json').read_bytes())
 data=SAMPLE.read_bytes()
 assert len(data)==manifest['bytes']
 assert hashlib.sha256(data).hexdigest()==manifest['sha256']
 assert manifest['authorityVerified'] is False and manifest['admissionAllowed'] is False
 p=json.loads(data)
 assert p['locator']['pdfPage']==24 and p['locator']['printedPage']==22
 assert p['materialVersion']=='99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f'
 assert p['candidate']['content']['source']['url']=='https://www.sh.msa.gov.cn/u/cms/www/202505/191445221747637122775.pdf'
 assert map_packet(data)['admissionAllowed'] is False
