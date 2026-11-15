"""Synthetic ordinary business characterization, not archive implementation/security tests."""
from sqlalchemy import select,func
from mcis_service.reports.models import ReportRow
from mcis_service.recommendations.models import ConsultationRoundRow
from .test_working_record_archive import client_at,checked,ROOT,snapshot
from .test_bounded_timeline_archive_increment import commit
from mcis_service.package.mcase import read_zip
import json


def open_round(c,sha=''):
    return checked(c,'post',ROOT+'/consultation/rounds',{'draftVersion':'SYNTHETIC-NO-STORED-REPORT',
        'draftSha256':sha,'parties':[{'partyId':'SYN','name':'Synthetic party'}]},201).json()


def test_round_accepts_declared_version_without_stored_report(tmp_path):
    with client_at(tmp_path/'a',True) as c:
        opened=open_round(c)
        assert opened['draftSha256']==''
        with c.app.state.db.session() as s:
            assert s.scalar(select(func.count()).select_from(ReportRow))==0
            doc=s.scalars(select(ConsultationRoundRow)).one().doc
            assert 'reportId' not in doc and doc['draftVersion']=='SYNTHETIC-NO-STORED-REPORT'
        # Inherited gap: legacy export succeeds but restricted intake cannot restore it.
        raw=checked(c,'get',ROOT+'/export').content
        assert json.loads(read_zip(raw)['manifest.json'])['packageVersion']=='1.0.0'
    with client_at(tmp_path/'target') as target:
        before=snapshot(target)
        rejected=commit(target,raw,422)
        assert rejected.json()['code']=='PACKAGE_INTAKE_INVALID'
        assert snapshot(target)==before


def test_optional_digest_is_declaration_not_stored_source_binding(tmp_path):
    with client_at(tmp_path/'a',True) as c:
        opened=open_round(c,'a'*64)
        assert opened['draftSha256']=='a'*64
        with c.app.state.db.session() as s:
            assert s.scalar(select(func.count()).select_from(ReportRow))==0


def test_full_feedback_survives_summary_and_second_decision_refused(tmp_path):
    with client_at(tmp_path/'a',True) as c:
        open_round(c)
        reply=checked(c,'post',ROOT+'/consultation/rounds/1/replies',
            {'partyId':'SYN','text':'Synthetic full reply','comments':['Synthetic comment']},201).json()
        ident=reply['comments'][0]['commentId'];feedback='Synthetic long feedback '*30
        path=ROOT+'/consultation/rounds/1/comments/'+ident
        checked(c,'patch',path,{'decision':'NotAdopted','feedback':feedback})
        current=checked(c,'get',ROOT+'/consultation/rounds').json()[0]
        assert current['comments'][0]['feedback']==feedback
        events=checked(c,'get',ROOT+'/audit?action=consultation.decide').json()
        assert len(events)==1 and len(events[0]['after'])==400
        assert feedback not in events[0]['after']
        before=snapshot(c)
        checked(c,'patch',path,{'decision':'Adopted','feedback':'Synthetic replacement'},409)
        assert snapshot(c)==before
        assert checked(c,'get',ROOT+'/audit:verify').json()['valid']


def test_timeline_plus_consultation_remains_whole_package_refusal(tmp_path):
    with client_at(tmp_path/'a',True) as c:
        open_round(c)
        checked(c,'post',ROOT+'/timeline/events',{'eventId':'TE-01','timeSec':1,
            'kind':'Observation','title':'Synthetic'},201)
        before=snapshot(c)
        r=checked(c,'get',ROOT+'/export',status=409)
        assert r.json()['code']=='ARCHIVE_RESTORE_UNSUPPORTED'
        assert not r.content.startswith(b'PK') and snapshot(c)==before
