"""Independent W17@871db66 HTTP+SQLite probe. Real uvicorn, synthetic cases, 127.0.0.1."""
import json,sqlite3,sys,urllib.request,urllib.error
ready=json.load(open(sys.argv[1]));o=ready['origin'];reg=ready['registered']
ROLES_INV=('LeadInvestigator','Investigator')
ROLES_RESTRICTED=('Public','ExternalExpert','InterestedState','AgentService')
PATHS=('evidence','evidence/EV-001','evidence/EV-001/custody','evidence/EV-001/intake')

def get(path,role='LeadInvestigator'):
 req=urllib.request.Request(o+path,headers={'X-MCIS-Role':role,'X-MCIS-Operator':'synthetic-reader'})
 try:
  with urllib.request.urlopen(req,timeout=20) as r:b=r.read();return r.status,dict(r.headers),b
 except urllib.error.HTTPError as e:return e.code,dict(e.headers),e.read()

def db():
 c=sqlite3.connect(f"file:{ready['db']}?mode=ro",uri=True)
 r=dict(
  audit=c.execute('select count(*) from audit_events').fetchone()[0],
  custody=c.execute('select case_id,evidence_id,kind from custody_events order by id').fetchall(),
  custodyN=c.execute('select count(*) from custody_events').fetchone()[0],
 )
 c.close();return r

def leak(b):
 return [x.decode() for x in (b'SOURCE-SYN-A',b'SOURCE-SYN-B',b'SYN-A.txt',b'SYN-B.txt',b'Restricted') if x in b]

res={'sha':'871db66badc6566d82239ee701958c0ef8feb558','dbBeforeReads':None,'checks':[]}
def chk(name,ok,**kw):res['checks'].append(dict(name=name,passed=bool(ok),**kw))

seed=db();res['dbAfterSeed']=seed
# --- investigation team can read ---
for role in ROLES_INV:
 for c in ('SYN-A','SYN-B'):
  s,h,b=get(f'/api/v1/cases/{c}/evidence',role)
  ok=s==200
  try: L=json.loads(b); ok=ok and [(x['evidenceId'],x['title']) for x in L]==[('EV-001','SOURCE-'+c)]
  except Exception: ok=False
  chk(f'{role} {c} list 200 own EV-001 only',ok,status=s)
  s,h,b=get(f'/api/v1/cases/{c}/evidence/EV-001',role)
  chk(f'{role} {c} item 200, no other case',s==200 and ('SOURCE-'+c).encode() in b and ('SOURCE-'+(('SYN-B' if c=='SYN-A' else 'SYN-A'))).encode() not in b,status=s)
  s,h,b=get(f'/api/v1/cases/{c}/evidence/EV-001/custody',role)
  ev=json.loads(b) if s==200 else []
  chk(f'{role} {c} custody 200 Register only',s==200 and [e.get('kind') for e in ev]==['Register'] and leak(b).count('SOURCE-'+c)+leak(b).count(c+'.txt')>=1,status=s)
  s,h,b=get(f'/api/v1/cases/{c}/evidence/EV-001/intake',role)
  d=json.loads(b) if s==200 else {}
  chk(f'{role} {c} intake matches digest/sha, no contentBase64',s==200 and d.get('requestDigest')==reg[c]['requestDigest'] and d.get('sourceSha256')==reg[c]['sourceSha256'] and d.get('fileName')==c+'.txt' and 'contentBase64' not in d,status=s,cache=h.get('cache-control'))

# --- case isolation ---
s,h,b=get('/api/v1/cases/SYN-B/evidence-intakes/'+reg['SYN-A']['requestDigest'])
chk('SYN-A digest under SYN-B -> 404, no sourceSha256',s==404 and b'sourceSha256' not in b,status=s)
s,h,b=get('/api/v1/cases/SYN-B/evidence/EV-999/custody')
chk('EV-999 custody not found (or 403), no SOURCE',s in (404,403) and not leak(b),status=s)
s,h,b=get('/api/v1/cases/SYN-A/evidence')
chk('SYN-A list does not mention SYN-B',s==200 and b'SOURCE-SYN-B' not in b,status=s)

res['dbAfterInvReads']=db()

# --- restricted roles denied on list, item, custody, intake ---
for role in ROLES_RESTRICTED:
 for c in ('SYN-A','SYN-B'):
  for p in PATHS:
   s,h,b=get(f'/api/v1/cases/{c}/{p}',role)
   leaked=leak(b)
   # Allowed outcomes: 403; or 200 with empty list and no metadata leak (FR-05 Remove on the list).
   if p=='evidence' and s==200:
     try: empty=json.loads(b)==[]
     except Exception: empty=False
     ok=empty and not leaked
   else:
     ok=s==403 and not leaked
   chk(f'{role} {c}/{p} denied, no Restricted metadata',ok,status=s,leaked=leaked,cache=h.get('cache-control'))

res['dbAfterRestricted']=db()

# --- revocation: deny LeadInvestigator evidence_meta on SYN-B ---
urllib.request.urlopen(o+'/__w17ctl/denyB').read()
for p in PATHS:
 s,h,b=get(f'/api/v1/cases/SYN-B/{p}')
 chk(f'after denyB LeadInvestigator SYN-B/{p} denied',s==403 and not leak(b),status=s,leaked=leak(b))
s,h,b=get('/api/v1/cases/SYN-A/evidence/EV-001/intake')
chk('after denyB SYN-A still readable',s==200 and b'SYN-A.txt' in b,status=s)
s,h,b=get('/api/v1/cases/SYN-A/evidence/EV-001/custody')
chk('after denyB SYN-A custody still readable',s==200,status=s)

after=db();res['dbAfterRevokeAndAll']=after
chk('SQLite: custody still exactly 2 Register rows (no Access/Verify)',
    after['custodyN']==2 and [k for *_,k in after['custody']]==['Register','Register'] and sorted(c for c,_,_ in after['custody'])==['SYN-A','SYN-B'],
    before=seed,after=after)
chk('SQLite: neither reads nor denials added audit rows',
    after['audit']==seed['audit'],
    auditSeed=seed['audit'],auditAfterInv=res['dbAfterInvReads']['audit'],auditAfterRestricted=res['dbAfterRestricted']['audit'],auditEnd=after['audit'])

res['passed']=all(c['passed'] for c in res['checks'])
print(json.dumps(res,ensure_ascii=False,indent=1));sys.exit(0 if res['passed'] else 1)
