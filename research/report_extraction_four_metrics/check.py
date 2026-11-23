"""Visible developer controls only; no blind data, product service, or model."""
import argparse,hashlib,importlib.util,json,sys,unittest
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parent

def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

p=argparse.ArgumentParser();p.add_argument('--dependencies',type=Path,required=True);args=p.parse_args()
for pin in json.loads((ROOT/'pins.json').read_text()):
    b=(args.dependencies/pin['path']).read_bytes()
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==pin['blob'],pin['path']
f=module('visible_fixed_fixture',args.dependencies/'tests_acceptance/synthetic-report-draft/check_utf8_joined.py')
l=module('fixed_locator',args.dependencies/'tests_acceptance/synthetic-utf8-locator/check.py')
s=module('research_score',ROOT/'score.py')
RESULT={}

def fixture(mode='full'):
    # Existing publicly developer-visible three-line control; no new blind source.
    host,rubric,proposal=f.fixture()
    claims=['甲报告该时段有雾。','乙报告同段无雾，待核。','停车命令时刻未知，执行未确认。']
    atoms=[{'id':f'a{i+1}','claim':claims[i],'citations':[{'id':f'c{i+1}','atomId':f'a{i+1}','span':span}]} for i,span in enumerate(proposal['items'])]
    if mode=='unsupported':atoms[2]['claim']='停车命令已执行。'
    if mode=='one_side':atoms=[atoms[0],atoms[2]]
    if mode=='empty':atoms=[]
    output={'status':'valid','atoms':atoms}
    review={'sourceSha256':f.PIN,'outputDigest':s.digest(output),'required':['m1','m2','m3'],
            'conflicts':{'fog':['m1','m2']},'pendingRequired':[],'complete':True,
            'atoms':{a['id']:{'support':'U' if mode=='unsupported' and a['id']=='a3' else 'S',
                             'matches':[] if mode=='unsupported' and a['id']=='a3' else ['m'+a['id'][1:]]} for a in atoms}}
    return output,review

def run(o,r):return s.evaluate(f.RAW,f.PIN,o,r,l.locate)
def bind(o,r):r['outputDigest']=s.digest(o)

class Checks(unittest.TestCase):
    def test_full_control(self):
        o,r=fixture();v=run(o,r);RESULT['full']=v
        self.assertEqual(v['controlFailures'],[])
        for k in ('locatorAccuracy','semanticSupport','mandatoryRecall','conflictRetention'):self.assertEqual(v['metrics'][k]['value'],1)
    def test_exact_quote_not_support(self):
        o,r=fixture('unsupported');v=run(o,r);RESULT['exact_but_unsupported']=v
        self.assertEqual(v['metrics']['locatorAccuracy']['value'],1)
        self.assertEqual(v['metrics']['semanticSupport'],s.ratio(2,3))
        self.assertIn('semantic_not_supported',v['controlFailures'])
    def test_one_conflict_side(self):
        o,r=fixture('one_side');v=run(o,r);RESULT['one_side']=v
        self.assertEqual(v['metrics']['locatorAccuracy'],s.ratio(2,2));self.assertEqual(v['metrics']['semanticSupport'],s.ratio(2,2))
        self.assertEqual(v['metrics']['mandatoryRecall'],s.ratio(2,3));self.assertEqual(v['metrics']['conflictRetention'],s.ratio(0,1))
        bundle=f.fixture();del bundle[2]['items'][1]
        with self.assertRaisesRegex(ValueError,'incomplete conflict group'):f.run(bundle)
    def test_empty(self):
        o,r=fixture('empty');v=run(o,r);RESULT['valid_empty']=v
        self.assertIsNone(v['metrics']['semanticSupport']['value']);self.assertEqual(v['metrics']['mandatoryRecall'],s.ratio(0,3))
    def test_no_applicable(self):
        o,r=fixture('empty');r['required']=[];r['conflicts']={};v=run(o,r)
        self.assertIsNone(v['metrics']['mandatoryRecall']['value']);self.assertIsNone(v['metrics']['conflictRetention']['value'])
    def test_pending(self):
        o,r=fixture('one_side');r['complete']=False;r['pendingRequired']=['m2'];v=run(o,r);RESULT['pending']=v
        self.assertIsNone(v['metrics']['mandatoryRecall']);self.assertEqual(v['pendingMandatory'],['m2'])
    def test_failed(self):
        o,r=fixture();o['status']='failed';self.assertEqual(run(o,r),{'status':'failed','metrics':None})
    def test_orphan_duplicate_binding_denominator(self):
        for damage in ('orphan','duplicate','binding','denominator','complete_pending','duplicate_citation'):
            o,r=fixture()
            if damage=='orphan':o['atoms'][0]['citations'][0]['atomId']='absent'
            if damage=='duplicate':o['atoms'].append(deepcopy(o['atoms'][0]))
            if damage=='denominator':r['required'].remove('m3')
            if damage=='complete_pending':r['pendingRequired']=['m3']
            if damage=='duplicate_citation':o['atoms'][1]['citations'][0]['id']='c1'
            if damage!='binding':bind(o,r)
            else:r['outputDigest']='0'*64
            with self.subTest(damage=damage):self.assertEqual(run(o,r),{'status':'malformed','metrics':None})
    def test_bad_locator_and_uncited_denominators(self):
        o,r=fixture();o['atoms'][0]['citations'][0]['span']['start']=1;o['atoms'][2]['citations']=[];bind(o,r)
        v=run(o,r);self.assertEqual(v['metrics']['citationCoverage'],s.ratio(2,3));self.assertEqual(v['metrics']['locatorAccuracy'],s.ratio(1,2))
    def test_duplicate_locator_new_citation_id(self):
        o,r=fixture();c=deepcopy(o['atoms'][0]['citations'][0]);c['id']='alias-citation'
        o['atoms'][0]['citations'].append(c);bind(o,r)
        self.assertEqual(run(o,r),{'status':'malformed','metrics':None})
    def test_duplicate_atom_new_ids_and_reordered_citations(self):
        for mode in ('normal','reordered','uncited','invalid'):
            o,r=fixture()
            if mode=='reordered':
                extra=deepcopy(o['atoms'][1]['citations'][0]);extra.update(id='extra',atomId='a1')
                o['atoms'][0]['citations'].append(extra)
            if mode=='uncited':o['atoms'][0]['citations']=[]
            if mode=='invalid':o['atoms'][0]['citations'][0]['span']['start']=999
            clone=deepcopy(o['atoms'][0]);clone['id']='alias-atom'
            clone['citations'].reverse()
            for i,c in enumerate(clone['citations']):c.update(id=f'alias-c{i}',atomId='alias-atom')
            o['atoms'].append(clone);r['atoms']['alias-atom']=deepcopy(r['atoms']['a1']);bind(o,r)
            with self.subTest(mode=mode):self.assertEqual(run(o,r),{'status':'malformed','metrics':None})
    def test_single_atom_cannot_match_both_conflict_sides(self):
        o,r=fixture('one_side');r['atoms']['a1']['matches']=['m1','m2']
        self.assertEqual(run(o,r),{'status':'malformed','metrics':None})
    def test_conflict_sides_require_located_citations(self):
        for damage in ('uncited','invalid'):
            o,r=fixture()
            if damage=='uncited':o['atoms'][1]['citations']=[]
            else:o['atoms'][1]['citations'][0]['span']['start']=999
            bind(o,r);v=run(o,r)
            with self.subTest(damage=damage):
                self.assertEqual(v['metrics']['conflictRetention'],s.ratio(0,1))
                self.assertIn('conflict_not_preserved',v['controlFailures'])
    def test_distinct_claims_may_share_a_located_span(self):
        o,r=fixture();a=deepcopy(o['atoms'][0]);a.update(id='optional',claim='甲有一条关于雾的报告。')
        a['citations'][0].update(id='optional-cite',atomId='optional');o['atoms'].append(a)
        r['atoms']['optional']={'support':'S','matches':[]};bind(o,r)
        v=run(o,r);self.assertEqual(v['status'],'complete')
        self.assertEqual(v['metrics']['mandatoryRecall'],s.ratio(3,3))
        self.assertEqual(v['metrics']['conflictRetention'],s.ratio(1,1))

    def test_inputs_unchanged(self):
        o,r=fixture();before=deepcopy((o,r));run(o,r);self.assertEqual((o,r),before)

if __name__=='__main__':
    if not sys.flags.isolated or sys.flags.optimize:raise SystemExit('Use -I -B without -O')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    print(json.dumps({'tests':result.testsRun,'passed':result.wasSuccessful(),'controls':RESULT},ensure_ascii=False,indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
