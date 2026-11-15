"""Ordinary synthetic report source coverage diagnostic, not integrity probes.
No original files, permission mutation, corrupted history, ECFC or model calls.
"""
import json
from .test_working_record_archive import client_at,ROOT,HEAD
from .test_conflict_source_receipt_submit import seed,prepare,change


def report(client):
    r=client.post(ROOT+'/reports',headers=HEAD,json={'templateId':'imo-cic','lang':'bilingual'})
    assert r.status_code==201,r.text
    loaded=client.get(ROOT+'/reports/'+r.json()['reportId'],headers=HEAD)
    assert loaded.status_code==200,loaded.text
    return loaded.json()


def test_saved_observation_missing_from_report_citations(tmp_path):
    with client_at(tmp_path/'case',True) as c:
        initial=seed(c)
        request,receipt=prepare(c,initial)
        saved=c.post(ROOT+'/conflicts',headers=HEAD,json=request)
        assert saved.status_code==201,saved.text
        history=c.get(ROOT+'/conflicts/C-01/revisions',headers=HEAD)
        assert history.status_code==200,history.text
        revision=history.json()['revisions'][-1]
        assert revision['revision']==2
        assert revision['sourceReceiptId']==receipt['receiptId']
        assert revision['after']['a']['valueText']==request['a']['valueText']
        assert revision['afterSources']['a']['sha256']=='a'*64
        first=report(c)
        sentences=[sentence for section in first['sections'] for sentence in section['sentences']]
        citations=[citation for sentence in sentences for citation in sentence['citations']]
        assert any(x['kind']=='evidence' and x['id']=='EV-A' for x in citations)
        assert not any(x['kind']=='conflict' or x['id']=='C-01' for x in citations)
        assert request['a']['valueText'] not in json.dumps(sentences,ensure_ascii=False)
        # Registry moves A->B without changing the captured historical observation.
        change(c,'EV-A')
        second=report(c)
        other=[x for section in second['sections'] for sentence in section['sentences'] for x in sentence['citations']]
        assert [x for x in citations if x['id']=='EV-A']==[x for x in other if x['id']=='EV-A']
        current_history=c.get(ROOT+'/conflicts/C-01/revisions',headers=HEAD)
        assert current_history.status_code==200,current_history.text
        assert current_history.json()['revisions'][-1]==revision
        # No claims that either report contains or version-binds the observation.
