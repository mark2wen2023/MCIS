"""Independent W5 case-scope tests over real TCP HTTP, temporary database."""
import copy,pytest
from fixtures import servers,request,case,record,getdoc,DEMO
@pytest.fixture(scope='module')
def api():
    with servers() as (base,_):yield base

@pytest.mark.parametrize('fictional',[True,False])
def test_empty_case_provenance(api,fictional):
    cid='W5-empty-'+str(fictional);case(api,cid,fictional)
    status,data=request(api,f'/cases/{cid}/interview-compare')
    assert status==200 and data['caseId']==cid and data['records']==[]
    assert data['fictional'] is fictional
    assert not any(x in data['disclaimer'] for x in ['Lily','Mary','公开报告'])
    assert request(api,f'/cases/{cid}/interview-compare/IR-03')[0]==404

@pytest.mark.parametrize('action,sid,body',[('confirm','S-confirm',{'note':'independent'}),('reject','S-reject',{'reason':'independent'}),('revise','S-revise',{'summary':'changed independently','reason':'independent'}),('recheck','S-recheck',{'outcome':'Consistent','observedText':'independent','sourceLabel':'synthetic','reason':'independent'})])
def test_same_named_ids_mutate_only_target_case(api,action,sid,body):
    a,b='W5-A-'+action,'W5-B-'+action
    for cid in [a,b]:case(api,cid);record(api,cid)
    before=getdoc(api,b)
    part='statements' if action=='revise' else 'rows'
    status,data=request(api,f'/cases/{a}/interview-compare/IR-01/{part}/{sid}:{action}',body)
    assert status==200,(status,data)
    assert getdoc(api,b)==before
    assert getdoc(api,a)!=before
    assert request(api,f'/cases/{a}/interview-compare')[1]['caseId']==a
    assert request(api,f'/cases/{b}/interview-compare/IR-01')[1]['caseId']==b
    assert len(request(api,f'/cases/{b}/audit')[1])==2

@pytest.mark.parametrize('role',['Public','ExternalExpert','InterestedState'])
def test_role_boundary_remains_server_enforced(api,role):
    cid='W5-role-'+role;case(api,cid);record(api,cid)
    before=getdoc(api,cid)
    status,data=request(api,f'/cases/{cid}/interview-compare/IR-01/rows/S-confirm:confirm',{},role)
    assert status==403,(status,data)
    assert getdoc(api,cid)==before
    status,data=request(api,f'/cases/{cid}/interview-compare/IR-01',role=role)
    if role=='Public':assert status==403
    else:
        assert status==200
        assert 'SYNTHETIC-PRIVATE' not in data['turns'][0]['answer']

def test_demo_disclaimer_and_default_records_remain(api):
    case(api,DEMO,True);record(api,DEMO,'IR-01');record(api,DEMO,'IR-03')
    status,data=request(api,f'/cases/{DEMO}/interview-compare')
    assert status==200 and 'Lily' in data['disclaimer'] and '虚构' in data['disclaimer']
    assert [r['recordId'] for r in data['records']]==['IR-01','IR-03']
