from .conflict_version_helpers import checked
"""Ordinary synthetic conflict writes; no report-integrity or ECFC probes."""
import json
from sqlalchemy import select
from mcis_service.timeline.models import ConflictRow
from .test_working_record_archive import client_at,ROOT,CID,snapshot
from .test_consultation_archive_readiness import state


def body(value='Synthetic A'):
    return {'conflictId':'C-01','summary':'Synthetic conflict','status':'Open',
            'a':{'sourceLabel':'Synthetic source A','valueText':value},
            'b':{'sourceLabel':'Synthetic source B','valueText':'Synthetic B'}}


def test_replaced_long_resolution_now_has_full_forward_history(tmp_path):
    with client_at(tmp_path/'a',True) as c:
        checked(c,'post',ROOT+'/conflicts',body(),201)
        original='Synthetic long explanation '*30+'SYNTHETIC_TAIL_NOT_RETAINED'
        checked(c,'patch',ROOT+'/conflicts/C-01',{'status':'Annotated','resolution':original})
        checked(c,'patch',ROOT+'/conflicts/C-01',{'status':'Resolved','resolution':'Synthetic final explanation'})
        events=checked(c,'get',ROOT+'/audit?action=conflict.update').json()
        assert len(events)==2
        assert len(events[0]['after'])==400 and len(events[1]['before'])==400
        assert original not in json.dumps(events)
        # Plain temporary database snapshot: no private case source is read.
        revisions=checked(c,'get',ROOT+'/conflicts/C-01/revisions').json()['revisions']
        assert revisions[1]['after']['resolution']==original
        assert revisions[2]['before']['resolution']==original
        current=checked(c,'get',ROOT+'/conflicts').json()[0]
        assert current['resolution']=='Synthetic final explanation'
        assert checked(c,'get',ROOT+'/audit:verify').json()['valid']
        before=state(c);checked(c,'get',ROOT+'/export',status=409);assert state(c)==before


def test_existing_id_post_now_preserves_prior_observation(tmp_path):
    with client_at(tmp_path/'a',True) as c:
        checked(c,'post',ROOT+'/conflicts',body('SYNTHETIC_OLD_OBSERVATION'),201)
        checked(c,'post',ROOT+'/conflicts',body('Synthetic replacement observation'),201)
        with c.app.state.db.session() as s:
            rows=list(s.scalars(select(ConflictRow).where(ConflictRow.case_id==CID)))
            assert len(rows)==1 and rows[0].doc['a']['valueText']=='Synthetic replacement observation'
        events=checked(c,'get',ROOT+'/audit?action=conflict.add').json()
        assert len(events)==2
        revisions=checked(c,'get',ROOT+'/conflicts/C-01/revisions').json()['revisions']
        assert revisions[0]['after']['a']['valueText']=='SYNTHETIC_OLD_OBSERVATION'
        assert revisions[1]['before']['a']['valueText']=='SYNTHETIC_OLD_OBSERVATION'
        assert checked(c,'get',ROOT+'/audit:verify').json()['valid']


def test_evidence_identifier_is_unverified_declaration(tmp_path):
    with client_at(tmp_path/'a',True) as c:
        value=body();value['a']['evidenceId']='EV-999'
        result=checked(c,'post',ROOT+'/conflicts',value,201).json()
        assert result['a']['evidenceId']=='EV-999'
        assert checked(c,'get',ROOT+'/evidence').json()==[]
        assert 'sha256' not in result['a']
        before=state(c);checked(c,'get',ROOT+'/export',status=409);assert state(c)==before
