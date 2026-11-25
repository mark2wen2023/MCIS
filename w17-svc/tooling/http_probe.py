"""Receipt A hands-on probe: real uvicorn (e2e_server.py on the a80226d worktree), real HTTP on 127.0.0.1, SQLite read-only."""
import json,sqlite3,sys,urllib.request,urllib.error
ready=json.load(open(sys.argv[1]));o=ready['origin'];reg=ready['registered']
def get(path,role='LeadInvestigator'):
 req=urllib.request.Request(o+path,headers={'X-MCIS-Role':role,'X-MCIS-Operator':'synthetic-reader'})
 try:
  with urllib.request.urlopen(req,timeout=20) as r:b=r.read();return r.status,dict(r.headers),b
 except urllib.error.HTTPError as e:return e.code,dict(e.headers),e.read()
def db():
 c=sqlite3.connect(f"file:{ready['db']}?mode=ro",uri=True)
 r=dict(custody=c.execute("select case_id,evidence_id,kind from custody_events order by id").fetchall(),audit=c.execute("select count(*) from audit_events").fetchone()[0],evidence=c.execute("select case_id,key from evidence_items order by case_id").fetchall())
 c.close();return r
res={'dbAfterSeed':db(),'checks':[]}
def chk(name,ok,**kw):res['checks'].append(dict(name=name,passed=bool(ok),**kw))
for c in ('SYN-A','SYN-B'):
 s,h,b=get(f'/api/v1/cases/{c}/evidence');L=json.loads(b)
 chk(f'{c} list 200, exactly one EV-001 titled SOURCE-{c}',s==200 and [(x['evidenceId'],x['title']) for x in L]==[('EV-001','SOURCE-'+c)],status=s)
 chk(f'{c} list does not leak other case',('SOURCE-'+('SYN-B' if c=='SYN-A' else 'SYN-A')).encode() not in b)
 s,h,b=get(f'/api/v1/cases/{c}/evidence/EV-001/custody');ev=json.loads(b)
 chk(f'{c} custody 200, only own Register',s==200 and [e['kind'] for e in ev]==['Register'] and all(e.get('caseId',c)==c for e in ev),status=s)
 s,h,b=get(f'/api/v1/cases/{c}/evidence/EV-001/intake');d=json.loads(b)
 chk(f'{c} intake receipt matches registered digest/sha/fileName, no contentBase64, replayed',s==200 and d['requestDigest']==reg[c]['requestDigest'] and d['sourceSha256']==reg[c]['sourceSha256'] and d['fileName']==c+'.txt' and 'contentBase64' not in d and d.get('replayed') is True,status=s,cacheControl=h.get('cache-control'))
s,h,b=get('/api/v1/cases/SYN-B/evidence-intakes/'+reg['SYN-A']['requestDigest']);chk('SYN-A digest under SYN-B -> 404, no sourceSha256',s==404 and b'sourceSha256' not in b,status=s)
s,h,b=get('/api/v1/cases/SYN-B/evidence/EV-999/intake');chk('EV-999 -> 404',s==404 and b'sourceSha256' not in b,status=s)
# Public: matrix Deny -> 403 everywhere. External roles: matrix ReadOnly but FR-05 'Remove' for Restricted evidence
# ("Restricted 证据仅调查组可见，不对外部角色列出"); the fixture evidence is Restricted, so it must not be exposed anywhere.
for p in ('/evidence','/evidence/EV-001','/evidence/EV-001/intake','/evidence/EV-001/custody'):
 s,h,b=get('/api/v1/cases/SYN-B'+p,'Public');chk(f'Public {p} -> 403, no metadata',s==403 and b'SOURCE-SYN-B' not in b,status=s)
for role in ('ExternalExpert','InterestedState','AgentService'):
 for p in ('/evidence','/evidence/EV-001','/evidence/EV-001/intake','/evidence/EV-001/custody'):
  s,h,b=get('/api/v1/cases/SYN-B'+p,role);leak=[x for x in (b'SOURCE-SYN-B',b'SYN-B.txt',b'Restricted') if x in b]
  chk(f'{role} {p}: Restricted EV-001 not exposed (FR-05)',not leak,status=s,leaked=[x.decode() for x in leak],bodyHead=b[:160].decode('utf8','replace'))
for role in ('Investigator',):
 s,h,b=get('/api/v1/cases/SYN-B/evidence/EV-001/intake',role);chk(f'{role} intake read',s==200,status=s,note='recorded only')
before=db()
urllib.request.urlopen(o+'/__w17ctl/denyB').read()
s,h,b=get('/api/v1/cases/SYN-B/evidence/EV-001/intake');chk('after denyB policy: LeadInvestigator intake -> 403, no receipt',s==403 and b'sourceSha256' not in b,status=s)
s,h,b=get('/api/v1/cases/SYN-A/evidence/EV-001/intake');chk('SYN-A unaffected by SYN-B deny',s==200,status=s)
after=db()
chk('SQLite: exactly 2 custody rows, both Register (one per case), no Access/Verify after all reads',[k for _,_,k in after['custody']]==['Register','Register'] and sorted(c for c,_,_ in after['custody'])==['SYN-A','SYN-B'],custody=after['custody'])
chk('SQLite: GET reads add no audit rows',after['audit']==res['dbAfterSeed']['audit'],auditSeed=res['dbAfterSeed']['audit'],auditEnd=after['audit'])
res['dbEnd']=after;res['passed']=all(c['passed'] for c in res['checks'])
print(json.dumps(res,ensure_ascii=False,indent=1));sys.exit(0 if res['passed'] else 1)
