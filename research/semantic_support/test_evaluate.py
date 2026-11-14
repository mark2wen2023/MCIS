import copy,hashlib,importlib.util,json
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('semantic_evaluate',Path(__file__).with_name('evaluate.py'));e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)

def inputs():
 s='船甲约12吨\n船乙未报告。😀'
 c={'schemaVersion':1,'corpusId':'trial','provenance':'assistant_constructed_provisional_not_expert_certified','items':[{'id':'one','sourceText':s,'sourceSha256':hashlib.sha256(s.encode()).hexdigest(),'sourceLocator':{'url':'https://example.org/report.pdf','pdfSha256':'a'*64,'pdfPage':1,'printedPage':1,'section':'test'},'claim':'船乙精确12吨','citation':{'start':0,'length':6,'quote':'船甲约12吨'},'suggestedLabel':'conflicted','rationale':'人工构造待专家判断'}]}
 p={'schemaVersion':1,'corpusSha256':'b'*64,'origin':'scripted_fixture','predictions':[{'itemId':'one','label':'supported','rationale':'外部模型未复核输出'}]}
 return c,p

def test_axes_separate():
 c,p=inputs();r=e.evaluate(c,'b'*64,p);i=r['items'][0]
 assert i['citation']['location'] is True and i['prediction']['label']=='supported' and i['suggestedLabel']=='conflicted'
 assert r['semanticSupportVerified'] is False and not r['factActivated']
 assert 'accuracy' not in json.dumps(r)
 c['items'][0]['suggestedLabel']=None
 assert e.evaluate(c,'b'*64,p)['items'][0]['suggestedComparison']=='not_labeled'

def test_quote_mismatch_not_entire_rejection():
 c,p=inputs();c['items'][0]['citation']['quote']='船乙约12吨'
 assert e.evaluate(c,'b'*64,p)['items'][0]['citation']['status']=='not_exact'

def test_unicode_span():
 c,p=inputs();s=c['items'][0]['sourceText'];c['items'][0]['citation']={'start':s.index('😀'),'length':1,'quote':'😀'}
 assert e.evaluate(c,'b'*64,p)['items'][0]['citation']['location']

def test_opinions_preserved_no_verified_humans():
 c,p=inputs();rev={'schemaVersion':1,'corpusSha256':'b'*64,'reviewers':[{'reviewerId':'expert_a','displayName':'甲','qualificationStatement':'自述','origin':'user_submission_unverified'},{'reviewerId':'expert_b','displayName':'乙','qualificationStatement':'脚本','origin':'scripted_test'}],'opinions':[{'itemId':'one','reviewerId':'expert_a','label':'supported','rationale':'自述'},{'itemId':'one','reviewerId':'expert_b','label':'conflicted','rationale':'脚本'}]}
 i=e.evaluate(c,'b'*64,p,rev)['items'][0];assert i['disagreementRecorded'] and i['verifiedHumanReviewers']==0 and i['unverifiedHumanSubmissionRecords']==1
 rev['reviewers'][1]['reviewerId']='expert_a'
 with pytest.raises(ValueError):e.evaluate(c,'b'*64,p,rev)

@pytest.mark.parametrize('raw',['{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}','['*12+'0'+']'*12])
def test_loader_rejects(tmp_path,raw):
 f=tmp_path/'bad.json';f.write_text(raw)
 with pytest.raises(ValueError):e.load(f)

@pytest.mark.parametrize('mutation',[lambda c:c.update(extra=True),lambda c:c.update(schemaVersion=True),lambda c:c['items'][0].update(sourceSha256='0'*64),lambda c:c['items'].append(copy.deepcopy(c['items'][0])),lambda c:c['items'][0]['citation'].update(start=True)])
def test_schema_rejects(mutation):
 c,p=inputs();mutation(c)
 with pytest.raises(ValueError):e.evaluate(c,'b'*64,p)

def test_origins_and_empty_review():
 c,p=inputs();r=e.evaluate(c,'b'*64,p,{'schemaVersion':1,'corpusSha256':'b'*64,'reviewers':[],'opinions':[]})
 assert r['items'][0]['prediction']['origin']=='scripted_fixture' and not r['items'][0]['prediction']['modelIdentityVerified']
 p['origin']='model_output_unverified';assert e.evaluate(c,'b'*64,p)['items'][0]['prediction']['origin']==p['origin']
 p['origin']='verified_model'
 with pytest.raises(ValueError):e.evaluate(c,'b'*64,p)

def test_file_budget(tmp_path):
 path=tmp_path/'oversize.json';path.write_bytes(b' '*(e.MAX_BYTES+1))
 with pytest.raises(ValueError):e.load(path)

def test_cli_error_is_generic(tmp_path):
 import subprocess,sys
 c=tmp_path/'bad.json';c.write_text('{"SECRET_DO_NOT_ECHO":NaN}')
 result=subprocess.run([sys.executable,str(Path(__file__).with_name('evaluate.py')),'--corpus',str(c),'--predictions',str(c)],capture_output=True,text=True)
 assert result.returncode==2 and not result.stdout and 'SECRET' not in result.stderr
 assert json.loads(result.stderr)['errorCode']=='PROVISIONAL_EVALUATION_REJECTED'
