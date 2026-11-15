"""Synthetic legacy-ingress simulation followed by real current read/replay paths."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'service'))
from tests.test_evidence_intake_w42 import local,body,URL,save,counts
from mcis_service.evidence_intake import parser,router

@pytest.mark.parametrize('control',[chr(x) for x in [0x61c,0x200e,0x200f,*range(0x202a,0x202f),*range(0x2066,0x206a)]])
def test_old_receipt_recovery_without_rename(local,monkeypatch,control):
    c,app=local
    original=parser.inputs
    # Simulate only the pre-change ingress policy. Binding/storage remain actual production code.
    def legacy(body,**kwargs):
        return original({**body,'fileName':'safe-placeholder.bin'},**kwargs)
    with monkeypatch.context() as m:
        m.setattr(router,'inputs',legacy)
        request,receipt=save(c,body(fileName='old'+control+'name.bin'))
    before=counts(app)
    result=c.get(URL+'/'+receipt['requestDigest'])
    assert result.status_code==200,result.text
    assert result.json()['fileName']=='old'+control+'name.bin'
    assert result.json()['requestDigest']==receipt['requestDigest']
    assert counts(app)==before
    replay=c.post(URL+':commit',json=request)
    assert replay.status_code==422
    assert replay.json()['code']=='INTAKE_FILENAME_DIRECTION'
    assert counts(app)==before
