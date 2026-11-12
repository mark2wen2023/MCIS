import hashlib,json,re,datetime
from ..common.context import problem
MAX=8*1024*1024
ZERO='0'*64
PROFILE='MCIS-KNOWLEDGE-ARCHIVE-1'

def fail(status=422,code='KNOWLEDGE_ARCHIVE_INVALID'):
    raise problem(status,code,'知识归档不符合完整保全要求')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encode(obj):
    try:return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    except (ValueError,TypeError,UnicodeError,RecursionError):fail()
def exact(obj,keys):
    if not isinstance(obj,dict)or set(obj)!=set(keys.split()):fail()
def integer(n,lo=1):
    if type(n)is not int or n<lo:fail()
def token(s,pattern):
    if not isinstance(s,str)or not re.fullmatch(pattern,s):fail()
def string(s,cap,empty=False):
    from ..knowledge.router import strings
    if not isinstance(s,str)or len(s)>cap or(not empty and not s.strip()):fail()
    if s:
        try:strings(s)
        except Exception:fail()
def utc(s):
    token(s,r'(19\d\d|20\d\d|2100)-\d\d-\d\dT\d\d:\d\d:\d\dZ')
    try:datetime.datetime.strptime(s,'%Y-%m-%dT%H:%M:%SZ')
    except ValueError:fail()
def strict(raw,*,budget=True):
    if budget and len(raw)>MAX:fail(413,'KNOWLEDGE_ARCHIVE_BUDGET')
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError()
            d[k]=v
        return d
    def bad(_):raise ValueError()
    try:d=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=bad)
    except (UnicodeError,ValueError,RecursionError):fail()
    def walk(x,depth):
        if depth>32:fail(413,'KNOWLEDGE_ARCHIVE_BUDGET')
        if isinstance(x,dict):
            for k,v in x.items():k.encode('utf-8');walk(v,depth+1)
        elif isinstance(x,list):
            for v in x:walk(v,depth+1)
        elif isinstance(x,str):x.encode('utf-8')
    try:walk(d,1)
    except UnicodeError:fail()
    return d

def doc(d):
    from ..knowledge.router import validate_content,digest
    base='cardId status content contentDigest createdUtc createdBy'
    if not isinstance(d,dict):fail()
    reviewed=d.get('status')!='Candidate'
    exact(d,base+(' reviewedUtc reviewedBy reviewNote approvals'if reviewed else''))
    token(d['cardId'],r'KC-[a-f0-9]{32}')
    if d['status']not in ('Candidate','Published','Rejected','Withdrawn'):fail()
    try:tags=validate_content(d['content'])
    except Exception:fail()
    if digest(d['content'])!=d['contentDigest']:fail()
    utc(d['createdUtc']);string(d['createdBy'],160)
    if reviewed:
        utc(d['reviewedUtc']);string(d['reviewedBy'],160);string(d['reviewNote'],2000)
        exact(d['approvals'],'sourceVerified rightsVerified releaseApproved')
        if any(type(v)is not bool for v in d['approvals'].values()):fail()
        if d['status']=='Published'and not all(d['approvals'].values()):fail()
    return tags

def validate(raw,*,budget=True):
    d=strict(raw,budget=budget);exact(d,'format version exportedUtc cards audit auditSnapshots')
    if d['format']!='MCIS-KNOWLEDGE-ARCHIVE'or type(d['version'])is not int or d['version']!=1:fail()
    utc(d['exportedUtc'])
    for name,cap in [('cards',1024),('audit',4096)]:
        if not isinstance(d[name],list):fail()
        if budget and len(d[name])>cap:fail(413,'KNOWLEDGE_ARCHIVE_BUDGET')
    cards={}
    for i,row in enumerate(d['cards'],1):
        exact(row,'order cardId status kind searchText tagsText doc');integer(row['order'])
        if row['order']!=i:fail()
        x=row['doc'];tags=doc(x)
        if row['cardId']!=x['cardId']or row['status']!=x['status']or row['kind']!=x['content']['kind']or row['cardId']in cards:fail()
        if row['tagsText']!='|'+'|'.join(tags)+'|'or row['searchText']!='\n'.join([x['content'][k]for k in ('title','summary','body','applicability')]+tags).casefold():fail()
        cards[row['cardId']]=x
    states={};events={};head=ZERO
    for n,row in enumerate(d['audit'],1):
        exact(row,'seq line');integer(row['seq']);string(row['line'],32768)
        b=row['line'].encode()
        if len(b)>32768:fail()
        e=strict(b);exact(e,'seq utc operator role cardId action before after note prevHash');integer(e['seq'])
        for key in ('role','cardId','action','before','after','prevHash'):
            if not isinstance(e[key],str):fail()
        token(e['cardId'],r'KC-[a-f0-9]{32}');token(e['prevHash'],r'[a-f0-9]{64}')
        if row['seq']!=n or e['seq']!=n or e['prevHash']!=head or e['cardId']not in cards:fail()
        utc(e['utc']);string(e['operator'],160);string(e['note'],2000,True)
        x=cards[e['cardId']];previous=states.get(e['cardId'])
        if e['action']=='knowledge.create':
            if previous is not None or e['role']not in ('Investigator','LeadInvestigator')or e['before']!=''or e['after']!=x['contentDigest']or e['note']!=''or e['operator']!=x['createdBy']:fail()
            state='Candidate'
        else:
            transitions={'knowledge.published':('Candidate','Published'),'knowledge.rejected':('Candidate','Rejected'),'knowledge.withdrawn':('Published','Withdrawn')}
            if e['action']not in transitions or e['role']!='LeadInvestigator':fail()
            before,state=transitions[e['action']]
            if previous!=before or e['before']!=before or e['after']!=state:fail()
        states[e['cardId']]=state;events[n]=e;head=sha(b)
    if set(states)!=set(cards):fail()
    for cid,x in cards.items():
        if states[cid]!=x['status']:fail()
        last=next(e for e in reversed(list(events.values()))if e['cardId']==cid)
        if x['status']!='Candidate'and(x['reviewedBy']!=last['operator']or x['reviewNote']!=last['note']):fail()
    a=d['auditSnapshots'];exact(a,'coverage items');cov=a['coverage'];exact(cov,'mode firstSeq priorHeadSha256')
    if not isinstance(a['items'],list):fail()
    if budget and len(a['items'])>4096:fail(413,'KNOWLEDGE_ARCHIVE_BUDGET')
    if cov['mode']=='legacy-only':
        if cov['firstSeq']is not None or cov['priorHeadSha256']!=head or a['items']:fail()
    elif cov['mode']=='from-sequence':
        first=cov['firstSeq'];integer(first)
        if first>len(events)or cov['priorHeadSha256']!=(ZERO if first==1 else sha(d['audit'][first-2]['line'].encode()))or len(a['items'])!=len(events)-first+1:fail()
        captured={}
        for n,r in enumerate(a['items'],first):
            exact(r,'seq auditLineSha256 cardId beforeDoc afterDoc');integer(r['seq'])
            e=events[n];cid=e['cardId'];after=r['afterDoc'];before=r['beforeDoc'];doc(after)
            if r['seq']!=n or r['cardId']!=cid or after['cardId']!=cid or r['auditLineSha256']!=sha(d['audit'][n-1]['line'].encode()):fail()
            if e['action']=='knowledge.create':
                if before is not None or after['status']!='Candidate'or after['createdBy']!=e['operator']or after['contentDigest']!=e['after']:fail()
            else:
                doc(before)
                if before['cardId']!=cid or before['status']!=e['before']or after['status']!=e['after']or after['reviewedBy']!=e['operator']or after['reviewNote']!=e['note']:fail()
                for key in ('cardId','content','contentDigest','createdUtc','createdBy'):
                    if before[key]!=after[key]:fail()
                if cid in captured and before!=captured[cid]:fail()
            for key in ('cardId','content','contentDigest','createdUtc','createdBy'):
                if after[key]!=cards[cid][key]:fail()
            captured[cid]=after
        if any(x!=cards[cid]for cid,x in captured.items()):fail()
    else:fail()
    summary={'profile':PROFILE,'archiveSha256':sha(raw),'byteLength':len(raw),'cardCount':len(cards),'auditCount':len(events),'auditHeadSha256':head,'auditSnapshotCount':len(a['items']),'snapshotCoverage':cov,'scope':'current-online-library-snapshot','restoreMode':'isolated-read-only-history','identityMode':'unverified-self-reported'}
    return d,summary
