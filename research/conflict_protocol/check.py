"""Developer protocol controls; unchanged scorer, no semantic classifier/model."""
import argparse,hashlib,importlib.util,json,sys,unittest
from pathlib import Path
from copy import deepcopy
P=Path(__file__).resolve().parent
MANIFEST_PIN='5d34c0053abb164f2981c08c7f4802d30d7a22bc3913b7a3da44d05ec18944a3'
SCORE_PIN='11b1b98fd925adda8228489d842e2a766b04b85d1f2d5aa86bd24832cdef77ec'
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
parser=argparse.ArgumentParser();parser.add_argument('--score-root',type=Path,default=P.parent/'report_extraction_four_metrics');parser.add_argument('--dependency-root',type=Path,default=P.parents[1]);args=parser.parse_args()
sp=args.score_root/'score.py';assert hashlib.sha256(sp.read_bytes()).hexdigest()==SCORE_PIN
s=load(sp,'fixed_score')
pins=json.loads((args.score_root/'pins.json').read_text());lp='tests_acceptance/synthetic-utf8-locator/check.py'
# Pin fixed dependency through the inherited manifest as well as its fixed digest.
assert hashlib.sha256((args.score_root/'pins.json').read_bytes()).hexdigest()=='dbdba53d127e18af202b8b1a6c86f52433fccb9282cd3c7f8b40a5fd3f9ccdf5'
pin=next(x for x in pins if x['path']==lp);b=(args.dependency_root/lp).read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==pin['blob']
l=load(args.dependency_root/lp,'fixed_locator')

def manifest(raw):
    if hashlib.sha256(raw).hexdigest()!=MANIFEST_PIN:raise ValueError('frozen control changed')
    return json.loads(raw)
M=manifest((P/'manifest.json').read_bytes())
def verify(output,review,raw_manifest):
    m=manifest(raw_manifest)
    if review['manifestSha256']!=MANIFEST_PIN or review['outputDigest']!=s.digest(output):raise ValueError('review binding')
    if set(output)!={'extraction','resolution'}:raise ValueError('output shape')
    # Required universe and conflict policy are never supplied by output or reviewer.
    r={'outputDigest':s.digest(output['extraction']),'sourceSha256':m['sourceSha256'],
       'required':m['required'],'conflicts':m['conflicts'],'pendingRequired':review['pendingRequired'],
       'complete':review['complete'],'atoms':review['atoms']}
    scored=s.evaluate(m['sourceText'].encode(),m['sourceSha256'],output['extraction'],r,l.locate)
    if scored['status'] in ('malformed','failed'):return {'protocol':'rejected','scorer':scored}
    violations=[]
    if output['resolution']!=m['policy']['allowedResolution']:violations.append('invented_resolution')
    if review['complete']:
        missing=scored['missingMandatory']
        if m['policy']['requiredQualifier'] in missing:violations.append('confirmed_missing_unresolved_qualifier')
        if scored['controlFailures'] or missing:violations.append('incomplete_or_unsupported_extraction')
    status='fail' if violations else ('pending_human_decision' if not review['complete'] else 'developer_control_pass')
    return {'protocol':status,'violations':violations,'scorer':scored,'humanAuthorityVerified':False,'modelRun':False}

def fixture(include=True,pending=False,resolution='unresolved'):
    atoms=[];marks={}
    for i,(line,key) in enumerate(zip(M['sourceText'].splitlines(),M['required']),1):
        if not include and key=='unresolved':continue
        atoms.append({'id':key,'claim':line,'citations':[{'id':'cite-'+key,'atomId':key,'span':{'paragraph':i,'start':0,'length':len(line),'quote':line}}]})
        marks[key]={'support':'S','matches':[key]}
    out={'extraction':{'status':'valid','atoms':atoms},'resolution':resolution}
    review={'manifestSha256':MANIFEST_PIN,'outputDigest':s.digest(out),'atoms':marks,'complete':not pending,'pendingRequired':['unresolved'] if pending else []}
    return out,review
RESULT={}
class Checks(unittest.TestCase):
    def run_control(self,name,**kw):
        o,r=fixture(**kw);v=verify(o,r,(P/'manifest.json').read_bytes());RESULT[name]=v;return v
    def test_complete_retained_qualifier(self):self.assertEqual(self.run_control('complete')['protocol'],'developer_control_pass')
    def test_retention_one_does_not_permit_resolution(self):
        v=self.run_control('invented',resolution='observer_a_confirmed')
        self.assertEqual(v['scorer']['metrics']['conflictRetention'],s.ratio(1,1));self.assertEqual(v['protocol'],'fail');self.assertIn('invented_resolution',v['violations'])
    def test_retention_one_with_confirmed_omission(self):
        v=self.run_control('omitted',include=False)
        self.assertEqual(v['scorer']['metrics']['conflictRetention'],s.ratio(1,1));self.assertEqual(v['protocol'],'fail');self.assertIn('confirmed_missing_unresolved_qualifier',v['violations'])
    def test_pending_is_not_confirmed_omission(self):
        v=self.run_control('pending',include=False,pending=True)
        self.assertEqual(v['protocol'],'pending_human_decision');self.assertEqual(v['violations'],[]);self.assertIsNone(v['scorer']['metrics']['mandatoryRecall']);self.assertEqual(v['scorer']['pendingMandatory'],['unresolved'])
    def test_manifest_change_rejected(self):
        o,r=fixture();m=deepcopy(M);m['required'].remove('unresolved')
        with self.assertRaisesRegex(ValueError,'frozen control'):verify(o,r,json.dumps(m).encode())
    def test_stale_review_and_output_policy_rejected(self):
        o,r=fixture();o['resolution']='confirmed'
        with self.assertRaisesRegex(ValueError,'review binding'):verify(o,r,(P/'manifest.json').read_bytes())
        o,r=fixture();o['policy']={};r['outputDigest']=s.digest(o)
        with self.assertRaisesRegex(ValueError,'output shape'):verify(o,r,(P/'manifest.json').read_bytes())
    def test_no_input_mutation(self):
        o,r=fixture();before=deepcopy((o,r));verify(o,r,(P/'manifest.json').read_bytes());self.assertEqual((o,r),before)
if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks));print(json.dumps({'tests':r.testsRun,'passed':r.wasSuccessful(),'controls':RESULT},indent=2));sys.exit(0 if r.wasSuccessful() else 1)
