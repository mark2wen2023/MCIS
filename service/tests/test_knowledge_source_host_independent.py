import pytest
from .test_knowledge_w19 import c,H,B,content
from .test_knowledge_archive import counts

@pytest.mark.parametrize('host', ['.'.join(['a'*63]*3+['b'*62]), 'a'*64+'.com', 'example..com.', 'example_com.test', 'example.com..'])
def test_independent_dns_limits_no_writes(c,host):
    data=content();data['source'].update(type='Public',url='https://'+host+'/report.pdf')
    before=counts(c)
    response=c.post(B+'/cards',headers=H('Investigator'),json=data)
    assert response.status_code==422,response.text
    assert counts(c)==before

@pytest.mark.parametrize('host', ['.'.join(['a'*63]*3+['b'*61]), '.'.join(['a'*63]*3+['b'*61])+'.', '例子.中国', 'EXAMPLE.COM.'])
def test_independent_boundary_valid_hosts_preserved(c,host):
    data=content();data['source'].update(type='Public',url='https://'+host+'/report.pdf')
    response=c.post(B+'/cards',headers=H('Investigator'),json=data)
    assert response.status_code==201,response.text
    assert response.json()['content']==data
    assert response.json()['status']=='Candidate'
