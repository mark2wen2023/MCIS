from urllib.parse import quote
import pytest
from .test_knowledge_w19 import c,H,B,content
from .test_knowledge_archive import counts
from .test_knowledge_actor import archive

@pytest.mark.parametrize('actor', ['x'*161, '海'*161, '\r', 'x\x85y', 'x\x1fy', ' \t\n '])
@pytest.mark.parametrize('stage',['create','review'])
def test_encoded_header_rejected_atomically(c,actor,stage):
    card=c.post(B+'/cards',headers=H('Investigator'),json=content()).json()
    before=counts(c)
    headers={**H('LeadInvestigator'),'X-MCIS-Operator':quote(actor)}
    if stage=='create':r=c.post(B+'/cards',headers=headers,json=content())
    else:r=c.post(B+'/cards/'+card['cardId']+'/review',headers=headers,json={'decision':'Rejected','expectedDigest':card['contentDigest'],'note':'synthetic'})
    assert r.status_code==422,r.text
    assert counts(c)==before
    archive(c)

@pytest.mark.parametrize('actor',['海'*160,'🙂'*160,' e\u0301\n\t '])
def test_header_decode_and_archive_exact(c,actor):
    r=c.post(B+'/cards',headers={**H('Investigator'),'X-MCIS-Operator':quote(actor)},json=content())
    assert r.status_code==201,r.text
    assert r.json()['createdBy']==actor
    assert archive(c)['cards'][0]['doc']['createdBy']==actor

def test_role_denial_still_precedes_actor_check(c):
    before=counts(c)
    r=c.post(B+'/cards',headers={**H('Public'),'X-MCIS-Operator':'x'*161},json=content())
    assert r.status_code==403 and counts(c)==before
