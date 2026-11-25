import pytest
from mcis_service.agents.skills.ship_reconstruction.table_extraction import cluster_rows

def cell(x,y,h,text='0'):
    return dict(x=x,y=y,handle=h,text=text)

def test_order_and_evidence():
    rows=cluster_rows([cell(2,9.9,'B'),cell(1,10,'A'),cell(1,5,'C')],0.2)
    assert [[c['handle'] for c in r] for r in rows]==[['A','B'],['C']]

def test_no_chaining():
    assert len(cluster_rows([cell(1,10,'A'),cell(1,9.9,'B'),cell(1,9.8,'C')],0.15))==2

def test_empty():
    assert cluster_rows([],1)==[]

@pytest.mark.parametrize('tol',[0,-1,float('nan'),True])
def test_bad_tolerance(tol):
    with pytest.raises(ValueError):
        cluster_rows([],tol)

def test_invalid_anchor():
    with pytest.raises(ValueError):
        cluster_rows([cell(float('inf'),0,'A')],1)

def test_missing_handle():
    with pytest.raises(ValueError):
        cluster_rows([cell(0,0,'')],1)
