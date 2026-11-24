"""Synthetic SQLite acceptance only: no production route, schema, or migration."""
from copy import deepcopy
from hashlib import sha1,sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import UUID
import sys
ROOT=Path(__file__).resolve().parent
for line in (ROOT/'SOURCES').read_text().splitlines():
    blob,ref,path=line.split()
    b=(ROOT/'source'/path).read_bytes()
    assert sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==blob,path
sys.path.insert(0,str(ROOT/'source'/'service'))

from fastapi import HTTPException
from sqlalchemy import event, select, text
from sqlalchemy.exc import IntegrityError
from mcis_service.audit.models import AuditEventRow
from mcis_service.cases.models import CaseRow
from mcis_service.db import Base,Database,get_doc,put_doc
from mcis_service.ecfc_drafts import router as ec
from mcis_service.ecfc_drafts.models import EcfcAuditRow,EcfcRequestRow,EcfcWorksheetRow
from mcis_service.evidence.models import EvidenceRow
from mcis_service.recommendations import router as w7
from mcis_service.recommendations.models import RecommendationRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.reports.access import begin

CASE='SYN-W7-A'; OTHER='SYN-W7-B'; REC='SR-2026-71'; LEGACY='SR-2026-72'; NODE='Node01'; EID='EV-001'
dig=lambda obj:sha256(ec.canonical(obj)).hexdigest()
def mark(n):print(f'PASS {n}',flush=True)
def req(s,sql,**args):return s.execute(text(sql),args)
def rec(s,case,key):
    d=w7._load(s,case,key)
    if d.get('caseId')!=case or d.get('id')!=key or d.get('status')!='Draft':
        return None
    return d
def graph(s,c,case):
    # Reuse the exact W11 read validation and latest-audit checks without
    # calling get_draft(), which creates a second independent session.
    row=s.get(EcfcWorksheetRow,case)
    newest=s.scalars(select(EcfcAuditRow).where(EcfcAuditRow.case_id==case).order_by(EcfcAuditRow.revision.desc()).limit(1)).first()
    if row is None:
        if newest is not None or s.scalars(select(EcfcRequestRow).where(EcfcRequestRow.case_id==case).limit(1)).first() is not None:ec.integrity()
        return None
    d=ec.validate_document(row.doc,case)
    if newest is None or ec.validate_event(newest.doc,case,newest.revision)['after']!=d:ec.integrity()
    return d if ec.check_document_sources(s,c,case,d)=='unchanged' else None
def both(s,c,case):
    begin(s)  # Actual production SQLite reserved-writer gate, holds one read snapshot.
    w7.require_content(s,case,c.role)
    ec.snapshot(s,c,case,[])  # Actual W11 case and distinct authorization gate.
def binding(d,g,node):
    return (d['caseId'],d['id'],dig(d),g['revision'],g['digest'],node)
def values(key):return dict(zip(('case','rec','rec_sha','graph_rev','graph_sha','node'),key,strict=True))
def latest(s,case,key,node):
    return req(s,'SELECT * FROM synthetic_link_history WHERE case_id=:c AND rec_id=:r AND node=:n ORDER BY seq DESC LIMIT 1',c=case,r=key,n=node).mappings().first()
def write_event(c,case,requested,action):
    if len(requested)!=6 or requested[0]!=case:
        return None
    with c.db.session() as s:
        both(s,c,case)
        d=rec(s,case,requested[1])
        g=graph(s,c,case)
        if d is None or g is None or requested!=binding(d,g,requested[-1]):
            return None
        node=requested[-1]
        if node not in d.get('causeNodeIds',[]) or not any(n['id']==node for n in g['draft']['nodes']):
            return None
        prior=latest(s,case,d['id'],node)
        if action=='revoked' and not (prior and prior['action']=='linked' and event_key(prior)==requested):
            return None
        if action=='linked' and prior and prior['action']=='linked' and event_key(prior)==requested:
            return None
        return req(s,'INSERT INTO synthetic_link_history(case_id,rec_id,rec_digest,graph_revision,graph_digest,node,action) VALUES(:case,:rec,:rec_sha,:graph_rev,:graph_sha,:node,:action)',**values(requested),action=action).lastrowid
def event_key(row):return tuple(row[k] for k in ('case_id','rec_id','rec_digest','graph_revision','graph_digest','node'))
def read(c,case,key,node,requested_case=None):
    if requested_case is not None and requested_case!=case:return None
    try:
        with c.db.session() as s:
            both(s,c,case)  # before lookup, including misses
            d=rec(s,case,key)
            g=graph(s,c,case)
            if d is None or g is None or node not in d.get('causeNodeIds',[]):
                return None
            row=latest(s,case,key,node)
            if row is None or row['action']!='linked' or event_key(row)!=binding(d,g,node):
                return None
            found=next((n for n in g['draft']['nodes'] if n['id']==node),None)
            return None if found is None else dict(nodeId=node,status='Draft',strength='ToBeVerified',seekAvailable=False)
    except (HTTPException,ec.PreviewError):
        return None  # same body/no disclosure for all unauthorized/unavailable cases
def history(c,case,key,node):
    try:
        with c.db.session() as s:
            both(s,c,case)
            # explicit history, after both gates, read metadata only: no old node content
            return [(r['action'],r['graph_revision'],r['graph_digest'],r['rec_digest']) for r in 
                req(s,'SELECT * FROM synthetic_link_history WHERE case_id=:c AND rec_id=:r AND node=:n ORDER BY seq',c=case,r=key,n=node).mappings()]
    except (HTTPException,ec.PreviewError):return None
def fixture_graph(db,c,case,revision,content):
    # A narrow, transparent fixture replaces .NET generation only. The exact W11
    # append helper, storage rows, audit validation and validation of doc run.
    n=dict(id=NODE,kind='Condition',text=content,timeSeconds=None,lane=0,isPrimaryIncident=False,evidenceIds=[EID])
    with db.session() as s:
        begin(s)
        sources,_,_=ec.snapshot(s,c,case,[EID],write=True)
        draft=dict(scope='Synthetic investigation',nodes=[n],edges=[])
        validation=dict(coreVersion='mcis-ecfc-draft/1',nodes=[dict(n,isPresumptive=True)],edges=[],issues=[])
        d=dict(caseId=case,revision=revision,draft=draft,sources=sources,validation=validation)
        d['digest']=dig(d)
        d.update(status='Draft',strength='ToBeVerified',origin='Investigator',savedBy=c.operator,savedRole=c.role,savedUtc='2026-11-24T00:00:00Z')
        ec.validate_document(d,case)
        row=s.get(EcfcWorksheetRow,case)
        before=row.doc if row else None
        if row: row.doc=d
        else:s.add(EcfcWorksheetRow(case_id=case,doc=d))
        s.flush()
        ec.append_revision(s,case,before,d,c,str(UUID(int=revision)))
    got=ec.get_draft(case,c)
    assert got.status_code==200 and b'"sourceStatus":"unchanged"' in got.body
    return d
def track(db):
    sql=[]
    event.listen(db.engine,'before_cursor_execute',lambda conn,cursor,statement,parameters,context,executemany:sql.append(statement))
    return sql
def ctx(db,role='LeadInvestigator'):return SimpleNamespace(db=db,role=role,operator='Synthetic reviewer')
def seed(db):
    tables=[x.__table__ for x in (CaseRow,RecommendationRow,AuditEventRow,AccessPolicyRow,EvidenceRow,EcfcWorksheetRow,EcfcAuditRow,EcfcRequestRow)]
    Base.metadata.create_all(db.engine,tables=tables)
    with db.engine.begin() as con:
        con.exec_driver_sql("""CREATE TABLE synthetic_link_history(seq INTEGER PRIMARY KEY, case_id TEXT NOT NULL,
        rec_id TEXT NOT NULL, rec_digest TEXT NOT NULL, graph_revision INTEGER NOT NULL, graph_digest TEXT NOT NULL,
        node TEXT NOT NULL, action TEXT NOT NULL CHECK(action IN ('linked','revoked')))""")
        for op in ('UPDATE','DELETE'):
            con.exec_driver_sql(f"CREATE TRIGGER history_{op} BEFORE {op} ON synthetic_link_history BEGIN SELECT RAISE(ABORT,'append-only'); END")
    with db.session() as s:
        for case in (CASE,OTHER):
            put_doc(s,CaseRow,case,case,dict(caseId=case))
            put_doc(s,EvidenceRow,case,EID,dict(caseId=case,evidenceId=EID,title='Synthetic source only',sha256='a'*64,confidentiality='Normal'))
def create(c,case,key):
    w7.create_rec(case,w7.RecIn(id=key,title='Synthetic recommendation',body='Synthetic suggestion',addressee='Synthetic owner',causeNodeIds=[NODE],dueUtc='2099-01-01T00:00:00Z',isInterim=False),c)
    w7.get_rec(case,key,c)
    with c.db.session() as s:return rec(s,case,key)
def reopen(db,url):db.engine.dispose();return Database(url)

def main():
    with TemporaryDirectory(prefix='w7-ecfc-synthetic-') as temp:
        url=f'sqlite:///{temp}/isolated.db'
        db=Database(url);seed(db);c=ctx(db)
        a=create(c,CASE,REC);b=create(c,OTHER,REC);create(c,CASE,LEGACY)
        a1=fixture_graph(db,c,CASE,1,'initial synthetic condition A')
        b1=fixture_graph(db,c,OTHER,1,'unrelated same-ID synthetic condition B')
        pa1=binding(a,a1,NODE);pb1=binding(b,b1,NODE)
        assert read(c,CASE,REC,NODE) is None and read(c,CASE,LEGACY,NODE) is None
        mark('real W7 creation and W11 GET; raw IDs alone remain unbound')
        assert write_event(c,CASE,pa1,'linked') is not None
        assert write_event(c,OTHER,pb1,'linked') is not None
        assert write_event(c,CASE,pb1,'linked') is None
        assert read(c,CASE,REC,NODE,requested_case=OTHER) is None
        mark('cross-case same IDs do not select a different case binding')
        assert read(c,CASE,REC,NODE)==dict(nodeId=NODE,status='Draft',strength='ToBeVerified',seekAvailable=False)
        db=reopen(db,url);c=ctx(db)
        assert read(c,CASE,REC,NODE)['nodeId']==NODE and read(c,CASE,LEGACY,NODE) is None
        mark('binding persists across SQLite disposal/reopen; returns draft metadata only')
        sql=track(db)
        for role in ('Public','Investigator','ExternalExpert','AgentService'):
            denied=ctx(db,role);assert read(denied,CASE,REC,NODE) is None and history(denied,CASE,REC,NODE) is None
        assert not any('synthetic_link_history' in q or 'FROM ecfc_drafts' in q or 'FROM recommendations' in q for q in sql)
        mark('actual unauthorized gates before any recommendation, graph, or association read')
        a2=fixture_graph(db,c,CASE,2,'new meaning on same node id')
        pa2=binding(a,a2,NODE)
        assert read(c,CASE,REC,NODE) is None and read(c,OTHER,REC,NODE)['nodeId']==NODE
        assert history(c,CASE,REC,NODE)==[('linked',1,a1['digest'],dig(a))]
        assert write_event(c,CASE,pa1,'linked') is None
        mark('same-case graph revision replacement refuses reused ID; old pin remains in history')
        assert write_event(c,CASE,pa2,'linked') is not None
        assert read(c,CASE,REC,NODE)['nodeId']==NODE
        w7.patch_rec(CASE,REC,w7.RecPatch(title='Amended synthetic recommendation'),c)
        with c.db.session() as s:a_changed=rec(s,CASE,REC)
        assert dig(a_changed)!=dig(a) and read(c,CASE,REC,NODE) is None
        pa_new=binding(a_changed,a2,NODE)
        mark('real W7 PATCH invalidates prior recommendation digest, without silently rebinding')
        assert write_event(c,CASE,pa_new,'linked') is not None
        with db.session() as s:
            ev=get_doc(s,EvidenceRow,CASE,EID)
            put_doc(s,EvidenceRow,CASE,EID,dict(ev,sha256='b'*64))
        assert read(c,CASE,REC,NODE) is None
        assert b'"sourceStatus":"changed"' in ec.get_draft(CASE,c).body
        mark('real W11 source status invalidates the binding after evidence metadata changes')
        with db.session() as s:
            put_doc(s,EvidenceRow,CASE,EID,ev)
        assert read(c,CASE,REC,NODE)['nodeId']==NODE
        policy=default_policy();changed=deepcopy(policy);changed['matrix']['LeadInvestigator']['medical']='Deny'
        with db.session() as s: put_doc(s,AccessPolicyRow,CASE,'policy',changed)
        sql.clear()
        assert read(c,CASE,REC,NODE) is None and history(c,CASE,REC,NODE) is None
        assert not any('synthetic_link_history' in q or 'FROM ecfc_drafts' in q or 'FROM recommendations' in q for q in sql)
        with db.session() as s: put_doc(s,AccessPolicyRow,CASE,'policy',policy)
        mark('actual access-policy revocation also hides previously linked node and history before reads')
        assert write_event(c,CASE,pa_new,'revoked') is not None
        db=reopen(db,url);c=ctx(db)
        assert read(c,CASE,REC,NODE) is None
        h=history(c,CASE,REC,NODE)
        assert h==[('linked',1,a1['digest'],dig(a)),('linked',2,a2['digest'],dig(a)),('linked',2,a2['digest'],dig(a_changed)),('revoked',2,a2['digest'],dig(a_changed))]
        mark('explicit revocation survives reopening; all four history records and exact prior digests preserved')
        for statement in ('UPDATE synthetic_link_history SET action=action','DELETE FROM synthetic_link_history'):
            try:
                with db.session() as s:req(s,statement)
            except IntegrityError:pass
            else:raise AssertionError('append-only mutation unexpectedly worked')
        assert history(c,CASE,REC,NODE)==h
        assert read(c,CASE,LEGACY,NODE) is None
        mark('append-only history rejects UPDATE/DELETE; legacy and revoked candidates do not auto-bind')
        db.engine.dispose()
if __name__=='__main__': main()
