import copy
import pytest
from .conftest import H
from .test_registered_align_preview import register, request, URL
from .test_align_preview_w41 import result
from .test_binding_review_independent import snapshot
from mcis_service.timeline import align_preview

CTX={'vesselLabel':'SHIP-A','sourceNature':'report_extract','sourceTitle':'Public report','citation':'p17 fig6','timeBasis':'UTC supplied by investigator; unverified','headingReference':'true'}
def scoped(client):
    a=register(client);b=register(client,filename='other.csv')
    # distinct registration requests, same fictional bytes are permitted
    body={'sources':request(a)['sources']+request(b)['sources']}
    for s in body['sources']:s['comparisonContext']=copy.deepcopy(CTX)
    return body

def test_scope_and_legacy_no_database_write(client,monkeypatch):
    monkeypatch.setattr(align_preview,'core_run',lambda *a:result(a[2]))
    body=scoped(client);before=snapshot(client)
    r=client.post(URL,headers=H(),json=body)
    assert r.status_code==200,r.text
    assert r.json()['comparisonScope']['status']=='user_declared_not_verified'
    assert r.json()['comparisonScope']['sources'][0]['context']==CTX
    assert snapshot(client)==before
    for s in body['sources']:del s['comparisonContext']
    r=client.post(URL,headers=H(),json=body)
    assert r.status_code==200,r.text
    assert r.json()['comparisonScope']['status']=='unscoped'
    assert snapshot(client)==before

@pytest.mark.parametrize('mutation',['mixed','ship','kind','columns','unknown','magnetic','unknownref','blankcitation','blanktitle','falseauthority','cogref'])
def test_rejected_scope_no_core_or_writes(client,monkeypatch,mutation):
    body=scoped(client);s=body['sources'][1];c=s['comparisonContext']
    if mutation=='mixed':del s['comparisonContext']
    elif mutation=='ship':c['vesselLabel']='SHIP-B'
    elif mutation=='kind':s['csvMapping']['columns'][0]['kind']='CourseOverGround';c['headingReference']=None
    elif mutation=='columns':s['csvMapping']['columns'].append({'column':'cog','kind':'CourseOverGround'})
    elif mutation=='unknown':c['surprise']='x'
    elif mutation=='magnetic':c['headingReference']='magnetic'
    elif mutation=='unknownref':c['headingReference']='unknown'
    elif mutation=='blankcitation':c['citation']=' '
    elif mutation=='blanktitle':c['sourceTitle']=' '
    elif mutation=='falseauthority':c['verified']=True
    elif mutation=='cogref':
        for source in body['sources']:source['csvMapping']['columns'][0]['kind']='CourseOverGround'
    def unexpected(*a):raise AssertionError('core must not run')
    monkeypatch.setattr(align_preview,'core_run',unexpected)
    before=snapshot(client)
    r=client.post(URL,headers=H(),json=body)
    assert r.status_code==422,r.text
    assert snapshot(client)==before
