"""Independent offline comparison checks; no expert labels or real model use."""
import copy,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).parent
spec=importlib.util.spec_from_file_location('independent_semantic_eval',ROOT/'evaluate.py');e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)

def sample():
 source='😀甲船约12吨。\n乙船未记录。甲船约12吨。'
 corpus={'schemaVersion':1,'corpusId':'independent','provenance':'assistant_constructed_provisional_not_expert_certified','items':[{'id':'one','sourceText':source,'sourceSha256':hashlib.sha256(source.encode()).hexdigest(),'sourceLocator':{'url':'https://example.test/a.pdf','pdfSha256':'0'*64,'pdfPage':3,'printedPage':1,'section':'公开原文声明，未核验PDF'},'claim':'乙船确实泄漏精确12吨，故导致事故','citation':{'start':1,'length':6,'quote':'甲船约12吨'},'suggestedLabel':'conflicted','rationale':'AI构造建议，不是专家标签'}]}
 preds={'schemaVersion':1,'corpusSha256':'a'*64,'origin':'scripted_fixture','predictions':[{'itemId':'one','label':'supported','rationale':'脚本候选，不是真实模型'}]}
 return corpus,preds


def test_independent_exact_quote_never_verifies_semantics_or_locator():
 c,p=sample();before=copy.deepcopy((c,p));out=e.evaluate(c,'a'*64,p);item=out['items'][0]
 assert item['citation']['status']=='exact' and item['suggestedLabel']=='conflicted' and item['prediction']['label']=='supported'
 assert not out['semanticSupportVerified'] and not out['factActivated'] and not item['sourceLocatorVerified']
 assert item['prediction']['origin']=='scripted_fixture' and not item['prediction']['modelIdentityVerified'] and not item['prediction']['provenanceVerified']
 assert (c,p)==before
 assert not any(k in json.dumps(out).lower() for k in ('accuracy','gold_standard','correctness_rate'))


def test_independent_codepoints_repeated_quote_and_no_normalization():
 c,p=sample();s=c['items'][0]['sourceText'];citation=c['items'][0]['citation']
 citation['start']=s.rindex('甲');assert e.evaluate(c,'a'*64,p)['items'][0]['citation']['location']
 citation.update(start=0,length=1,quote='😀');assert e.evaluate(c,'a'*64,p)['items'][0]['citation']['coordinates']=='unicode_code_points'
 citation.update(start=0,length=2,quote='😀');assert e.evaluate(c,'a'*64,p)['items'][0]['citation']['status']=='not_exact'
 citation.update(start=len(s),length=1,quote='x');out=e.evaluate(c,'a'*64,p);assert out['items'][0]['citation']['status']=='out_of_bounds' and out['items'][0]['prediction']['label']=='supported'


def test_independent_two_aliases_conflict_retained_without_expert_certification():
 c,p=sample();reviews={'schemaVersion':1,'corpusSha256':'a'*64,'reviewers':[{'reviewerId':name,'displayName':'同一自述姓名','qualificationStatement':'自称专家，未认证','origin':origin} for name,origin in [('alias_one','user_submission_unverified'),('alias_two','scripted_test')]],'opinions':[{'itemId':'one','reviewerId':name,'label':label,'rationale':reason} for name,label,reason in [('alias_one','supported','意见一'),('alias_two','conflicted','相反意见')]]}
 original=copy.deepcopy(reviews);out=e.evaluate(c,'a'*64,p,reviews);item=out['items'][0]
 assert item['disagreementRecorded'] and item['distinctReviewerRecords']==2 and item['verifiedHumanReviewers']==0
 assert [o['rationale'] for o in item['opinions']]==['意见一','相反意见'] and not any(o['humanReviewVerified'] for o in item['opinions'])
 assert all(not r['identityVerified'] and not r['qualificationVerified'] and not r['independenceVerified'] for r in out['reviewers'])
 assert reviews==original and not out['expertCertificationVerified']
 reviews['opinions'][1]['label']='supported';out=e.evaluate(c,'a'*64,p,reviews);assert not out['items'][0]['disagreementRecorded'] and not out['semanticSupportVerified']

@pytest.mark.parametrize('damage',['wrong_source','bool_start','bool_version','extra_field','long_source','bad_origin','wrong_corpus','missing_prediction','duplicate_prediction','extra_prediction','bad_label'])
def test_independent_strict_bounded_shapes(damage):
 c,p=sample()
 if damage=='wrong_source':c['items'][0]['sourceSha256']='b'*64
 elif damage=='bool_start':c['items'][0]['citation']['start']=True
 elif damage=='bool_version':c['schemaVersion']=True
 elif damage=='extra_field':c['items'][0]['verified']=True
 elif damage=='long_source':c['items'][0]['sourceText']='x'*24001
 elif damage=='bad_origin':p['origin']='real_model_verified'
 elif damage=='wrong_corpus':p['corpusSha256']='b'*64
 elif damage=='missing_prediction':p['predictions']=[]
 elif damage=='duplicate_prediction':p['predictions']*=2
 elif damage=='extra_prediction':p['predictions'].append({**p['predictions'][0],'itemId':'other'})
 else:p['predictions'][0]['label']='true_fact'
 with pytest.raises(ValueError):e.evaluate(c,'a'*64,p)

@pytest.mark.parametrize('raw',['{"a":{"x":1,"\\u0078":2}}','{"a":1e999}','{"a":NaN}','{"a":-Infinity}','['*12+'0'+']'*12])
def test_independent_raw_json_rejects_duplicates_nonfinite_depth(tmp_path,raw):
 path=tmp_path/'input.json';path.write_text(raw)
 with pytest.raises(ValueError):e.load(path)


def test_independent_loader_byte_budget(tmp_path):
 path=tmp_path/'large.json';path.write_bytes(b' '*(e.MAX_BYTES+1))
 with pytest.raises(ValueError):e.load(path)


def test_independent_public_corpus_cli_is_offline_fixture_not_accuracy():
 command="import socket,runpy,sys;socket.socket=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('network forbidden'));entry=sys.argv[4];sys.argv=['evaluate.py','--corpus',sys.argv[1],'--predictions',sys.argv[2],'--reviews',sys.argv[3]];runpy.run_path(entry,run_name='__main__')"
 paths=[ROOT/'yangze22-provisional.json',ROOT/'fixture-predictions.json',ROOT/'empty-review-template.json'];before=[p.read_bytes() for p in paths]
 run=subprocess.run([sys.executable,'-c',command,*map(str,paths),str(ROOT/'evaluate.py')],text=True,capture_output=True,timeout=15)
 assert run.returncode==0 and run.stderr=='';out=json.loads(run.stdout)
 assert len(out['items'])==11 and not out['realModelCalled'] and not out['semanticSupportVerified'] and out['reviewers']==[]
 assert sum(i['suggestedComparison']=='not_labeled' for i in out['items'])==2
 assert all(i['prediction']['origin']=='scripted_fixture' and not i['sourceLocatorVerified'] for i in out['items'])
 assert before==[p.read_bytes() for p in paths]


def test_independent_cli_error_does_not_echo_source(tmp_path):
 bad=tmp_path/'bad.json';bad.write_text('{"private":"SENTINEL_DO_NOT_ECHO","private":0}')
 run=subprocess.run([sys.executable,str(ROOT/'evaluate.py'),'--corpus',str(bad),'--predictions',str(bad)],text=True,capture_output=True,timeout=15)
 assert run.returncode==2 and run.stdout=='' and 'SENTINEL' not in run.stderr
 assert json.loads(run.stderr)['errorCode']=='PROVISIONAL_EVALUATION_REJECTED'

@pytest.mark.parametrize('damage',['third_reviewer','unknown_reviewer','duplicate_opinion','verified_flag','origin_claim','corpus_mismatch'])
def test_independent_review_authority_and_identity_shapes(damage):
 c,p=sample();r={'schemaVersion':1,'corpusSha256':'a'*64,'reviewers':[{'reviewerId':'one','displayName':'自述专家','qualificationStatement':'未核验','origin':'user_submission_unverified'}],'opinions':[{'itemId':'one','reviewerId':'one','label':'insufficient','rationale':'待讨论'}]}
 if damage=='third_reviewer':r['reviewers'] += [{**r['reviewers'][0],'reviewerId':x} for x in ('two','three')]
 elif damage=='unknown_reviewer':r['opinions'][0]['reviewerId']='unknown'
 elif damage=='duplicate_opinion':r['opinions']*=2
 elif damage=='verified_flag':r['reviewers'][0]['identityVerified']=True
 elif damage=='origin_claim':r['reviewers'][0]['origin']='verified_expert'
 else:r['corpusSha256']='b'*64
 with pytest.raises(ValueError):e.evaluate(c,'a'*64,p,r)
