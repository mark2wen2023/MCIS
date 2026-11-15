"""Ordinary synthetic states; COLREG rows are storage fixtures, not core output."""
import json
import pytest
from mcis_service.db import put_doc
from mcis_service.colreg.models import ColregAnalysisRow
from mcis_service.package.mcase import read_zip
from .test_working_record_archive import client_at,checked,ROOT,CID
from .test_consultation_archive_readiness import state
from .test_bounded_timeline_archive_increment import commit
from .conftest import H

KINDS=('recommendation','conflict','agent','colreg-current','colreg-inputs','sim-command')


def populate(c,kind):
    if kind=='recommendation':
        checked(c,'post',ROOT+'/recommendations',{'title':'Synthetic','addressee':'Synthetic',
            'causeNodeIds':['SYN'],'dueUtc':'2099-01-01T00:00:00Z'},201)
    elif kind=='conflict':
        checked(c,'post',ROOT+'/conflicts',{'summary':'Synthetic conflict',
            'a':{'sourceLabel':'Synthetic A','valueText':'A'},
            'b':{'sourceLabel':'Synthetic B','valueText':'B'}},201)
    elif kind=='agent':
        checked(c,'post',ROOT+'/agents/drafts',{'agent':'timeline','kind':'timeline_anchor',
            'payload':{'title':'Synthetic, no model executed'},'citations':[{'quote':'Synthetic quote'}]},201)
    elif kind.startswith('colreg-'):
        # Storage-only selector fixture. Does not simulate or claim a C# computation.
        with c.app.state.db.session() as s:
            put_doc(s,ColregAnalysisRow,CID,kind.split('-',1)[1],{'caseId':CID,'syntheticFixture':True})
    elif kind=='sim-command':
        checked(c,'post',ROOT+'/sim/commands',{'type':'pause','reason':'Synthetic command; no Unity connection'},201)


@pytest.mark.parametrize('kind',KINDS)
def test_standalone_unsupported_state_refused(tmp_path,kind):
    with client_at(tmp_path/'source',True) as c:
        populate(c,kind);before=state(c)
        response=c.get(ROOT+'/export',headers=H('LeadInvestigator','Synthetic'))
        assert response.status_code==409, (kind,response.status_code)
        assert response.json()['code']=='ARCHIVE_RESTORE_UNSUPPORTED'
        assert not response.content.startswith(b'PK') and state(c)==before


@pytest.mark.parametrize('kind',KINDS)
def test_public_not_granted_by_export_guard(tmp_path,kind):
    with client_at(tmp_path/'source',True) as c:
        populate(c,kind);before=state(c)
        checked(c,'get',ROOT+'/export',status=403,headers=H('Public','Synthetic'))
        assert state(c)==before


def test_other_case_state_does_not_block_empty_case(tmp_path):
    from mcis_service.cases.models import CaseRow
    from mcis_service.db import get_doc
    with client_at(tmp_path/'source',True) as c:
        with c.app.state.db.session() as s:
            doc=get_doc(s,CaseRow,CID,CID)
            put_doc(s,CaseRow,'OTHER','OTHER',{**doc,'caseId':'OTHER'})
            put_doc(s,ColregAnalysisRow,'OTHER','inputs',{'syntheticFixture':True})
        raw=checked(c,'get',ROOT+'/export').content
        assert json.loads(read_zip(raw)['manifest.json'])['packageVersion']=='1.0.0'
    with client_at(tmp_path/'target') as target:
        commit(target,raw)
