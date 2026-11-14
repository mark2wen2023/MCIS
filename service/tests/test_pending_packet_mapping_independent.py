"""Independent pure mapping acceptance; no source authenticity claim."""
import copy,json,socket
import pytest
from mcis_service.knowledge_packet_validation import map_packet,InvalidPacket,sha
from tests.test_pending_packet_mapping import packet,raw,SAMPLE


@pytest.mark.parametrize('path,value',[
 (('approvalGranted',),0),(('authorizationVerified',),0),(('locator','pdfPage'),True),
 (('sourcePreview','byteLength'),True),(('reviewRecords',),[{'approved':True}]),
 (('worksheet','checks'),[]),(('worksheet','requiredReleaseApprovals'),[]),
 (('freshness','changedFields'),['excerpt']),
])
def test_boolean_and_array_confusion_rejected(packet,path,value):
    node=packet
    for k in path[:-1]:node=node[k]
    node[path[-1]]=value
    with pytest.raises(InvalidPacket):map_packet(raw(packet))


def test_self_consistent_forged_pdf_hash_never_authenticates(packet):
    forged='0'*64
    packet['materialVersion']=forged
    packet['bindings']['sourceFileSha256']=forged
    packet['sourceDeclaration']['fileSha256']=forged
    packet['sourcePreview']['fileSha256']=forged
    packet['sourcePreview']['manifest']=copy.deepcopy(packet['sourceDeclaration'])
    packet['sourcePreview']['manifestDigest']=sha(json.dumps(packet['sourceDeclaration'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
    packet['sourcePreview']['byteLength']=1
    out=map_packet(raw(packet))
    assert out['originEnvelope']['materialVersion']==forged
    assert out['sourceAuthenticity']=='not_verified'
    for key in ('admissionAllowed','authorizationVerified','sourceBytesChecked','pageContentIndependentlyVerified','persisted'):
        assert out[key] is False


def test_path_looking_declarations_are_retained_data_never_opened(packet,monkeypatch):
    packet['materialId']='../../private/data'
    packet['locator']['extractionTool']='$(touch /tmp/DO_NOT_EXECUTE)'
    def forbidden(*a,**k):raise AssertionError('No file or network access')
    import builtins
    monkeypatch.setattr(builtins,'open',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    out=map_packet(raw(packet))
    assert out['originEnvelope']['materialId']=='../../private/data'
    assert out['originEnvelope']['locator']['extractionTool']==packet['locator']['extractionTool']
    assert not out['admissionAllowed']


def test_every_original_field_and_bytes_retained_without_aliasing(packet):
    data=json.dumps(packet,ensure_ascii=True,indent=3).encode()+b'\n'
    out=map_packet(data)
    assert out['originalPacketBytes']==data and out['packetSha256']==sha(data)
    assert out['originEnvelope']==packet
    out['originEnvelope']['candidate']['content']['title']='changed'
    assert out['candidateContent']['title']==packet['candidate']['content']['title']
    assert json.loads(out['originalPacketBytes'])==packet


def test_nested_unknown_field_rejected(packet):
    packet['sourcePreview']['manifest']['path']='/private/anything'
    with pytest.raises(InvalidPacket):map_packet(raw(packet))


def test_duplicate_nested_key_rejected(packet):
    data=raw(packet)
    needle=b'"approvalGranted": false'
    assert needle in data
    data=data.replace(needle,b'"approvalGranted": false, "approvalGranted": false',1)
    with pytest.raises(InvalidPacket):map_packet(data)


@pytest.mark.parametrize('data',[bytearray(b'{}'),memoryview(b'{}'),b'{"x":NaN}',b'\xff'])
def test_wrong_input_type_invalid_json_rejected(data):
    with pytest.raises(InvalidPacket):map_packet(data)
