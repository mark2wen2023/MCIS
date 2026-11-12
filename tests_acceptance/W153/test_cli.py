"""Independent synthetic Bow-tie CLI tests, to run after implementation readiness."""
import copy,json,os,subprocess
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
CLI=ROOT/'tools/mcis-bowtie/mcis-bowtie.sh'
def node(ident,kind,barrier=None):return {'id':ident,'label':'合成 '+ident,'kind':kind,'barrierId':barrier}
def model():
    return {'hazard':'合成危险源 🛳','topEvent':{'id':'TOP','label':'假设失控事件'},
            'nodes':[node('T','Threat'),node('P','PreventionBarrier'),node('M','MitigationBarrier'),node('C','Consequence')],
            'edges':[{'fromId':a,'toId':b} for a,b in [('T','P'),('P','TOP'),('TOP','M'),('M','C')]]}
def run(m):
    r=subprocess.run([str(CLI)],input=json.dumps(m,ensure_ascii=False).encode(),capture_output=True,timeout=60)
    assert r.returncode==0,r.stderr.decode()
    out=json.loads(r.stdout);assert out['ok'] is True
    return out['result']
def test_valid_is_only_hypothesis_structure():
    d=run(model());assert d['structureValid'] is True and d['notCheckedRefCount']==0
    assert d['mode']=='hypothesis-structure-only' and d['nodeCount']==5 and d['edgeCount']==4
    assert not d['constructionErrors'] and not d['validationIssues']
@pytest.mark.parametrize('kind',['duplicate-node','duplicate-edge','unknown-endpoint','wrong-direction','cycle','mixed-threat'])
def test_construction_failure_never_partial_success(kind):
    m=model()
    if kind=='duplicate-node':m['nodes'].append(node('T','Threat'))
    if kind=='duplicate-edge':m['edges'].append(m['edges'][0].copy())
    if kind=='unknown-endpoint':m['edges'].append({'fromId':'GHOST','toId':'TOP'})
    if kind=='wrong-direction':m['edges'].append({'fromId':'C','toId':'TOP'})
    if kind in ['cycle','mixed-threat']:
        m['nodes'].append(node('T2','Threat'))
        m['edges']=[{'fromId':'T','toId':'T2'},{'fromId':'T2' if kind=='cycle' else 'T','toId':'T' if kind=='cycle' else 'TOP'}]
    d=run(m)
    assert d['constructionErrors'] and d['structureValid'] is False
    assert d['validationIssues']==[]
    assert all(e['code'].startswith('sys_') for e in d['constructionErrors'])
def test_direct_no_barrier_path_not_effectiveness_assessment():
    m=model();m['nodes']=[node('T','Threat'),node('C','Consequence')]
    m['edges']=[{'fromId':'T','toId':'TOP'},{'fromId':'TOP','toId':'C'}]
    d=run(m);assert d['structureValid'] is True
    assert 'effective' not in d and 'riskScore' not in d
@pytest.mark.parametrize('field',['state','strength','refs'])
def test_client_cannot_assert_verification(field):
    m=model();m['nodes'][0][field]='Effective'
    r=subprocess.run([str(CLI)],input=json.dumps(m).encode(),capture_output=True,timeout=60)
    assert r.returncode==4 and json.loads(r.stdout)['ok'] is False
