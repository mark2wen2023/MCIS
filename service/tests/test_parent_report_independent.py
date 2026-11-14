"""Independent parent-reference probes; synthetic source semantics only."""
from .conftest import H
from .test_registered_parent_report import parent, body, stub, CTX, PDF
from .test_registered_align_preview import register, request, URL, RAW
from .test_binding_review_independent import snapshot


def test_mixed_linked_unlinked_scoped_sources_are_explicit(client, monkeypatch):
    a=register(client); b=register(client, RAW.replace(b'45',b'50'),'independent.csv'); p=parent(client)
    linked=body(a,p)['sources'][0]; unlinked=request(b)['sources'][0]
    unlinked['comparisonContext']=CTX.copy()
    stub(monkeypatch); before=snapshot(client)
    r=client.post(URL,headers=H(),json={'sources':[linked,unlinked]})
    assert r.status_code==200,r.text
    assert snapshot(client)==before
    assert [x['extractEvidenceId'] for x in r.json()['reportSnapshots']]==[a['evidenceId']]
    assert len(r.json()['sourceSnapshots'])==2
    assert r.json()['reportSnapshots'][0]['relationshipStatus']=='user_declared_not_verified'


def test_distinct_parent_per_source_not_collapsed(client, monkeypatch):
    a=register(client); b=register(client, RAW.replace(b'45',b'50'),'second.csv')
    p=parent(client); q=parent(client,PDF+b'other','other.pdf')
    stub(monkeypatch)
    r=client.post(URL,headers=H(),json={'sources':body(a,p)['sources']+body(b,q)['sources']})
    assert r.status_code==200,r.text
    assert [(x['extractEvidenceId'],x['evidenceId']) for x in r.json()['reportSnapshots']]==[(a['evidenceId'],p['evidenceId']),(b['evidenceId'],q['evidenceId'])]


def test_pdf_extension_is_deliberately_not_content_validation(client,monkeypatch):
    a=register(client); p=parent(client,b'Not PDF bytes','not-valid.pdf');stub(monkeypatch)
    r=client.post(URL,headers=H(),json=body(a,p))
    assert r.status_code==200,r.text
    assert r.json()['reportSnapshots'][0]['relationshipStatus']=='user_declared_not_verified'
    assert r.json()['observationApproval']=='not_assessed'
