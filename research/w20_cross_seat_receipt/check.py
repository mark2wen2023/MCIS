"""New cross-seat/version acceptance; no model, chair lifecycle or database."""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parent
def load(name,path,blob=None):
    raw=path.read_bytes()
    if blob:assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
    p=argparse.ArgumentParser();p.add_argument('--ecfc-package',type=Path,required=True);p.add_argument('--packet',type=Path,required=True);p.add_argument('--locator',type=Path,required=True);args=p.parse_args()
    fixture=load('fixture',ROOT/'receiver_fixture.py')
    packet=load('actual_packet',args.packet,'ff2018dad2d58e9fe158f503ecd71a004c20e226')
    locator=load('actual_locator',args.locator,'44fc5d82279db5fa3a3c748161f3122708e85668')
    # Exact 6996fa05 sample; verify package records against published frozen manifest.
    manifest=(args.ecfc_package/'FROZEN.sha256').read_bytes()
    assert hashlib.sha256(manifest).hexdigest()=='e91d31f34678ee2af880fb9931813677b93706332a03e96a0846943ef50235dd'
    for line in manifest.decode().splitlines():
        sha,name=line.split('  ');assert hashlib.sha256((args.ecfc_package/name).read_bytes()).hexdigest()==sha
    data=json.loads((args.ecfc_package/'sample.json').read_text());registry={}
    for source in data['sources']:
        locator.ROOT=args.ecfc_package/source['directory'];card=source['card']
        assert locator.locate(card)=='LOCATED'
        statement=json.loads(card['content']['source']['excerpt'])
        assert statement['caseId']==data['caseId'] and statement['vesselId']=='SYN-VESSEL-A'
        registry[card['sourceBinding']['recordId']]={'sha256':card['sourceBinding']['sha256'],
          'line':card['sourceBinding']['line'],'recordId':card['sourceBinding']['recordId'],
          'excerpt':card['content']['source']['excerpt'],'target':statement['target'],
          'sourceAssertedStance':statement['assertedStance']}
    draft={'caseId':data['caseId'],'version':'synthetic-draft-v1','event':data['eventClaim'],'candidateLink':data['linkClaim']}
    expected=fixture.digest(draft)
    def opinions(refs,label='insufficient'):
        return [{'role':role,'draftVersion':draft['version'],'draftDigest':expected,'citations':list(refs),
           'review':{'itemId':'draft','label':label,'quote':registry['OBS-1']['excerpt'],
              'rationale':'合成席位意见，仅验归属及出处，不是专业判定。','uncertainty':'因果及相反检查均待人工复核。'}} for role in fixture.ROLES]
    observation={'OBS-1':registry['OBS-1']}
    first=fixture.receive(draft,expected,opinions(['OBS-1']),observation,packet._validate)
    assert first['opinionCount']==4 and first['locatedOriginalCount']==1 and first['causalStatementOriginalCount']==0
    aliases=dict(observation,ALIAS=registry['OBS-1']);aliased=opinions(['OBS-1']);aliased[2]['citations']=['ALIAS']
    alias=fixture.receive(draft,expected,aliased,aliases,packet._validate)
    assert alias['opinionCount']==4 and alias['locatedOriginalCount']==1
    conflict=fixture.receive(draft,expected,opinions(list(registry),'conflicted'),registry,packet._validate)
    assert conflict['locatedOriginalCount']==3 and conflict['observationOriginalCount']==1 and conflict['causalStatementOriginalCount']==2
    assert conflict['reviewStatus']=='opposed_source_assertions_pending'
    # Four identical supported labels must not outvote the actual opposing source statements.
    voted=fixture.receive(draft,expected,opinions(list(registry),'supported'),registry,packet._validate)
    assert voted['reviewStatus']=='opposed_source_assertions_pending' and not voted['factVerified']
    for out in (first,alias,conflict,voted):
        assert out['causalConclusion'] is None and out['jumpAnchor'] is None and not out['sourceCountIsWeight']
        assert out['humanConfirmation']=='PENDING'
    negatives=0
    for kind in ('draft','opinion_version','opinion_digest','unknown_source','quote_mismatch'):
        d=deepcopy(draft);ops=opinions(['OBS-1'])
        if kind=='draft':d['candidateLink']='已确定原因'
        elif kind=='opinion_version':ops[0]['draftVersion']='v2'
        elif kind=='opinion_digest':ops[0]['draftDigest']='0'*64
        elif kind=='unknown_source':ops[0]['citations']=['absent']
        else:ops[0]['review']['quote']='原件不存在的引文'
        try:fixture.receive(d,expected,ops,observation,packet._validate)
        except (ValueError,packet.GroupError):negatives+=1
        else:raise AssertionError(kind)
    assert negatives==5
    # Positive: quote from one explicitly cited located excerpt, including a later citation.
    single=opinions(['STA-1'])
    for op in single:op['review']['quote']=registry['STA-1']['excerpt']
    assert fixture.receive(draft,expected,single,registry,packet._validate)['locatedOriginalCount']==1
    multiple=opinions(['OBS-1','STB-1'])
    for op in multiple:op['review']['quote']=registry['STB-1']['excerpt']
    assert fixture.receive(draft,expected,multiple,registry,packet._validate)['locatedOriginalCount']==2
    quote_rejections=0
    uncited=opinions(['OBS-1']);uncited[0]['review']['quote']=registry['STA-1']['excerpt']
    joined=opinions(['OBS-1','STA-1'])
    boundary=registry['OBS-1']['excerpt'][-24:]+'\n'+registry['STA-1']['excerpt'][:24]
    assert boundary in '\n'.join(x['excerpt'] for x in registry.values())
    assert all(boundary not in x['excerpt'] for x in registry.values())
    joined[0]['review']['quote']=boundary
    for kind,ops in [('uncited_excerpt',uncited),('cross_excerpt_join',joined)]:
        try:fixture.receive(draft,expected,ops,registry,packet._validate)
        except (ValueError,packet.GroupError):quote_rejections+=1
        else:raise AssertionError('quote correspondence accepted: '+kind)
    assert quote_rejections==2
    print(json.dumps({'scope':'receiver fixture, NOT actual chair meeting','draft':draft,'draftDigest':expected,
      'actual_functions':['packet._validate','source_traceability.locate'],'observation_only':first,
      'alias_unique_count':alias['locatedOriginalCount'],'conflict':conflict,
      'unanimous_labels_still_pending':True,'negative_cases':negatives,'quote_positive_cases':2,'quote_rejections':quote_rejections},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
