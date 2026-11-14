"""Synthetic current-product probes, not an implemented recommendation archive."""
import base64,json
from pathlib import Path
import pytest
from sqlalchemy import select
from fastapi import HTTPException
from tests.test_working_record_archive import client_at,checked,CID,ROOT,HEAD,snapshot
from mcis_service.recommendations.models import RecommendationRow
from mcis_service.colreg.models import ColregAnalysisRow
from mcis_service.hfacs_drafts.models import HfacsWorksheetRow
from mcis_service.timeline.models import TimelineEventRow
from mcis_service.working_records_archive.validation import citations
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.db import put_doc


def create_rec(c,causes=None,status=201):
    return checked(c,'post',ROOT+'/recommendations',{
        'title':'Synthetic safety draft','body':'Synthetic only; no accident facts',
        'addressee':'Synthetic party','causeNodeIds':causes if causes is not None else ['NO-SUCH-CAUSE'],
        'dueUtc':'2099-01-01T00:00:00Z'},status).json()


def stored(c):
    with c.app.state.db.session() as s:
        return [(r.key,r.doc) for r in s.scalars(select(RecommendationRow).where(RecommendationRow.case_id==CID))]


@pytest.mark.parametrize('labels',[['NO-SUCH-CAUSE'],['COLREG-R19'],['','']])
def test_labels_are_not_resolved_to_local_cause_objects(tmp_path,labels):
    with client_at(tmp_path,True) as c:
        rec=create_rec(c,labels)
        assert rec['causeNodeIds']==labels
        with c.app.state.db.session() as s:
            for model in (ColregAnalysisRow,HfacsWorksheetRow,TimelineEventRow):
                assert s.scalars(select(model).where(model.case_id==CID)).first() is None
        assert stored(c)[0][1]['causeNodeIds']==labels
        print(json.dumps({'labels':labels,'create':201,'localColregHfacsTimelineAbsent':True}))


def find_citations(value):
    if isinstance(value,dict):
        for item in value.get('citations',[]):
            if item.get('kind')=='recommendation':yield item
        for item in value.values():yield from find_citations(item)
    elif isinstance(value,list):
        for item in value:yield from find_citations(item)


@pytest.mark.parametrize('issued',[False,True])
def test_report_combination_rejects_with_originals_and_audit_unchanged(tmp_path,issued):
    with client_at(tmp_path,True)as c:
        rec=create_rec(c)
        if issued:checked(c,'post',ROOT+'/recommendations/'+rec['id']+':transition',{'to':'Issued','note':'Synthetic test'})
        report=checked(c,'post',ROOT+'/reports',{'templateId':'cn-msa','lang':'en'},201).json()
        refs=list(find_citations(report));assert refs
        assert all(r['registration']=='registered' and r['id']==rec['id'] for r in refs)
        # Current closure refuses registered recommendation sources. No bypass.
        with pytest.raises(HTTPException)as exc:citations(report,CID,{}, {})
        assert exc.value.status_code==422
        before=snapshot(c)
        rejected=checked(c,'get',ROOT+'/export',status=409)
        assert rejected.json()['code']=='ARCHIVE_RESTORE_UNSUPPORTED'
        assert snapshot(c)==before
        checked(c,'get',ROOT+'/export',status=403,headers={'X-MCIS-Role':'Investigator'})
        assert snapshot(c)==before


def test_legacy_restoration_is_active_not_history_only(tmp_path):
    with client_at(tmp_path/'source',True)as c:
        rec=create_rec(c);raw=checked(c,'get',ROOT+'/export').content;original=stored(c)
    with client_at(tmp_path/'dest')as c:
        r=c.post('/api/v1/cases:import',headers=HEAD,files={'file':('synthetic.mcase',raw)})
        assert r.status_code==201,r.text
        assert stored(c)==original
        changed=checked(c,'post',ROOT+'/recommendations/'+rec['id']+':transition',{'to':'Issued','note':'Synthetic post-import action'}).json()
        assert changed['status']=='Issued'
        response=checked(c,'post',ROOT+'/recommendations/'+rec['id']+'/responses',{'party':'Synthetic','text':'Synthetic response'},201).json()
        assert response['status']=='Responded'
        assert response['causeNodeIds']==['NO-SUCH-CAUSE']
        events=checked(c,'get',ROOT+'/audit').json()
        assert any(e['action']=='safetyrec.response' for e in events)
    with client_at(tmp_path/'new-intake')as c:
        before=snapshot(c)
        checked(c,'post','/api/v1/packages/intakes:commit',{'contentBase64':base64.b64encode(raw).decode(),'sourceSha256':__import__('hashlib').sha256(raw).hexdigest(),'confirmed':True},422)
        assert snapshot(c)==before
        assert not(c.app.state.settings.blob_dir/CID).exists()


@pytest.mark.parametrize('level,status',[('Deny',403),('ReadOnly',409)])
def test_revoked_or_nondefault_policy_not_exported(tmp_path,level,status):
    with client_at(tmp_path,True)as c:
        create_rec(c)
        checked(c,'post',ROOT+'/reports',{'templateId':'cn-msa','lang':'en'},201)
        policy=default_policy();policy['matrix']['LeadInvestigator']['recommendations']=level
        with c.app.state.db.session()as s:put_doc(s,AccessPolicyRow,CID,'policy',policy)
        before=snapshot(c);checked(c,'get',ROOT+'/export',status=status);assert snapshot(c)==before


def test_failure_during_recommendation_audit_rolls_back_row(tmp_path,monkeypatch):
    from mcis_service.audit import service as audit
    with client_at(tmp_path,True)as c:
        before=snapshot(c);original=audit.append
        def failed(*args,**kwargs):
            if kwargs.get('action')=='safetyrec.create':raise RuntimeError('SYNTHETIC_AUDIT_FAILURE')
            return original(*args,**kwargs)
        monkeypatch.setattr(audit,'append',failed)
        error=create_rec(c,status=500)
        assert error['code']=='INTERNAL_ERROR' and 'SYNTHETIC_AUDIT_FAILURE' not in str(error)
        assert snapshot(c)==before
        assert stored(c)==[]


def test_proposed_future_version_is_not_silently_accepted(tmp_path):
    from tests.test_report_timeline_archive import rewrite
    with client_at(tmp_path/'source',True)as c:
        create_rec(c);raw=checked(c,'get',ROOT+'/export').content
    def future(files,manifest):manifest['packageVersion']='1.5.0'
    raw=rewrite(raw,future)
    with client_at(tmp_path/'target')as c:
        before=snapshot(c)
        checked(c,'post','/api/v1/packages/intakes:preview',{'contentBase64':base64.b64encode(raw).decode()},422)
        assert snapshot(c)==before
