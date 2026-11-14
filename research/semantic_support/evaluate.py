"""Offline comparison, never an accuracy metric or factual decision."""
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

LABELS={'supported','conflicted','insufficient'}
MAX_BYTES=4*1024*1024

def exact(value,keys):
    if type(value) is not dict or set(value)!=set(keys.split()):raise ValueError('shape')

def text(value,limit=2000):
    if type(value) is not str or not value.strip() or len(value)>limit:raise ValueError('text')
    value.encode('utf-8')
    return value

def ident(value):
    if type(value) is not str or not re.fullmatch('[a-z][a-z0-9_-]{0,63}',value):raise ValueError('id')
    return value

def sha(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):raise ValueError('hash')
    return value

def integer(value,lo,hi):
    if type(value) is not int or not lo<=value<=hi:raise ValueError('integer')

def array(value,lo,hi):
    if type(value) is not list or not lo<=len(value)<=hi:raise ValueError('list')
    return value

def label(value):
    if type(value) is not str or value not in LABELS:raise ValueError('label')
    return value

def _pairs(pairs):
    out={}
    for k,v in pairs:
        if k in out:raise ValueError('duplicate key')
        out[k]=v
    return out

def _bounded(value,depth=0):
    if depth>10:raise ValueError('depth')
    if type(value) is float and not math.isfinite(value):raise ValueError('finite')
    if type(value) is dict:
        for v in value.values():_bounded(v,depth+1)
    elif type(value) is list:
        for v in value:_bounded(v,depth+1)

def load(path):
    with Path(path).open('rb') as f:raw=f.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise ValueError('bytes')
    value=json.loads(raw.decode('utf-8'),object_pairs_hook=_pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('constant')))
    _bounded(value)
    return value,hashlib.sha256(raw).hexdigest()

def version(obj):integer(obj['schemaVersion'],1,1)

def evaluate(corpus,corpus_sha,predictions,reviews=None):
    sha(corpus_sha)
    exact(corpus,'schemaVersion corpusId provenance items');version(corpus);ident(corpus['corpusId'])
    if corpus['provenance']!='assistant_constructed_provisional_not_expert_certified':raise ValueError('provenance')
    items={}
    for item in array(corpus['items'],1,100):
        exact(item,'id sourceText sourceSha256 sourceLocator claim citation suggestedLabel rationale')
        key=ident(item['id'])
        if key in items:raise ValueError('duplicate item')
        source=text(item['sourceText'],24000)
        if sha(item['sourceSha256'])!=hashlib.sha256(source.encode('utf-8')).hexdigest():raise ValueError('source hash')
        text(item['claim']);text(item['rationale'])
        if item['suggestedLabel'] is not None:label(item['suggestedLabel'])
        loc=item['sourceLocator'];exact(loc,'url pdfSha256 pdfPage printedPage section')
        text(loc['url'],2000);sha(loc['pdfSha256']);integer(loc['pdfPage'],1,100000);integer(loc['printedPage'],1,100000);text(loc['section'],500)
        if not loc['url'].startswith('https://'):raise ValueError('source URL')
        c=item['citation'];exact(c,'start length quote');integer(c['start'],0,1000000);integer(c['length'],1,24000);text(c['quote'],24000)
        status='out_of_bounds' if c['start']+c['length']>len(source) else ('exact' if source[c['start']:c['start']+c['length']]==c['quote'] else 'not_exact')
        items[key]={'itemId':key,'claim':item['claim'],'sourceLocator':dict(loc),'sourceLocatorVerified':False,'citation':{'status':status,'location':status=='exact','coordinates':'unicode_code_points','sourceSha256':item['sourceSha256'],'start':c['start'],'length':c['length'],'quote':c['quote'],'meaning':'exact_text_location_only_not_semantic_support'},'suggestedLabel':item['suggestedLabel'],'suggestionRationale':item['rationale'],'suggestionStatus':'provisional_not_expert_certified','opinions':[]}
    exact(predictions,'schemaVersion corpusSha256 origin predictions');version(predictions)
    if predictions['origin'] not in ('scripted_fixture','model_output_unverified'):raise ValueError('prediction origin')
    if sha(predictions['corpusSha256'])!=corpus_sha:raise ValueError('binding')
    seen=set()
    for p in array(predictions['predictions'],1,100):
        exact(p,'itemId label rationale');key=ident(p['itemId'])
        if key not in items or key in seen:raise ValueError('prediction id')
        seen.add(key);label(p['label']);text(p['rationale'])
        items[key]['suggestedComparison']='not_labeled' if items[key]['suggestedLabel'] is None else ('same_provisional_label' if items[key]['suggestedLabel']==p['label'] else 'different_provisional_label')
        items[key]['prediction']={'label':p['label'],'rationale':p['rationale'],'status':'external_proposed_unreviewed','origin':predictions['origin'],'modelIdentityVerified':False,'provenanceVerified':False}
    if seen!=set(items):raise ValueError('coverage')
    reviewers={}
    if reviews is not None:
        exact(reviews,'schemaVersion corpusSha256 reviewers opinions');version(reviews)
        if sha(reviews['corpusSha256'])!=corpus_sha:raise ValueError('review binding')
        for r in array(reviews['reviewers'],0,2):
            exact(r,'reviewerId displayName qualificationStatement origin');key=ident(r['reviewerId'])
            if key in reviewers:raise ValueError('duplicate reviewer')
            text(r['displayName'],200);text(r['qualificationStatement'],2000)
            if r['origin'] not in ('user_submission_unverified','scripted_test'):raise ValueError('origin')
            reviewers[key]=dict(r,identityVerified=False,qualificationVerified=False,independenceVerified=False)
        seen=set()
        for opinion in array(reviews['opinions'],0,200):
            exact(opinion,'itemId reviewerId label rationale');key=ident(opinion['itemId']);rid=ident(opinion['reviewerId'])
            if key not in items or rid not in reviewers or (key,rid) in seen:raise ValueError('opinion id')
            seen.add((key,rid));label(opinion['label']);text(opinion['rationale'])
            items[key]['opinions'].append(dict(opinion,origin=reviewers[rid]['origin'],humanReviewVerified=False))
    for item in items.values():
        opinions=item['opinions'];item['disagreementRecorded']=len({o['label'] for o in opinions})>1
        item['distinctReviewerRecords']=len(opinions)
        item['unverifiedHumanSubmissionRecords']=sum(o['origin']=='user_submission_unverified' for o in opinions)
        item['verifiedHumanReviewers']=0
    return {'schemaVersion':1,'corpusId':corpus['corpusId'],'corpusSha256':corpus_sha,'status':'provisional_comparison_only','realModelCalled':False,'factActivated':False,'semanticSupportVerified':False,'expertCertificationVerified':False,'reviewers':list(reviewers.values()),'items':list(items.values())}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--corpus',required=True);parser.add_argument('--predictions',required=True);parser.add_argument('--reviews');args=parser.parse_args()
    c,d=load(args.corpus);p,_=load(args.predictions);r=load(args.reviews)[0] if args.reviews else None
    print(json.dumps(evaluate(c,d,p,r),ensure_ascii=False,allow_nan=False))

if __name__=='__main__':
    try:main()
    except Exception:
        print('{"ok":false,"errorCode":"PROVISIONAL_EVALUATION_REJECTED"}',file=sys.stderr);sys.exit(2)
