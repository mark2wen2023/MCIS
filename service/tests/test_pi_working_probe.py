import pytest
from .test_host_extraction import extraction_case
from .test_extraction_working_store import working
from .test_pi_working_host import accepted
from mcis_service.agents.pi_remote_public_probe import working_acceptance

def test_public_working_probe_helper_reopens_persistent_record(working,monkeypatch):
 h,result=accepted(working,monkeypatch)
 summary=working_acceptance(h,working[0],result)
 assert summary=={'workingSaved':True,'reopenedRead':True,'reviewRevision':1,'reviewActor':'scripted_test_not_human','factActivated':False,'persistentDuringProbe':True,'storage':'temporary_sqlite_deleted_after_probe'}
