"""Isolated synthetic-only SQLite service. No production auth, LLM or network."""
import hashlib
import json
import sqlite3
from copy import deepcopy

ROLES = ('regulation', 'navigation', 'investigation', 'vessel')

def encode(v):
    return json.dumps(v, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)

def bounded(v, name, limit=2000):
    if not isinstance(v, str) or not v.strip() or len(v) > limit:
        raise ValueError(name)
    v.encode('utf-8', errors='strict')
    return v

class Store:
    """actor is supplied by a trusted test harness, NOT an authentication mechanism."""
    def __init__(self, path):
        self.path = path
        with self.db() as c:
            c.executescript('CREATE TABLE IF NOT EXISTS panels(id TEXT PRIMARY KEY, doc TEXT NOT NULL);'
                            'CREATE TABLE IF NOT EXISTS receipts(panel TEXT, request TEXT, digest TEXT, result TEXT, PRIMARY KEY(panel,request));')
    def db(self):
        return sqlite3.connect(self.path, timeout=5)
    def create(self, panel_id, actor, snapshot, budget=8):
        if actor != 'investigator': raise ValueError('human_start_required')
        bounded(panel_id,'id',100)
        if type(budget) is not int or not 1 <= budget <= 32: raise ValueError('budget')
        if not isinstance(snapshot,dict) or set(snapshot) != {'caseId','reportVersion','reportText','sources','synthetic'} or snapshot['synthetic'] is not True:
            raise ValueError('synthetic_snapshot_required')
        for key in ('caseId','reportVersion'): bounded(snapshot[key],key,100)
        bounded(snapshot['reportText'],'reportText',20000)
        if not isinstance(snapshot['sources'],dict) or len(snapshot['sources']) > 100: raise ValueError('sources')
        for key, value in snapshot['sources'].items():
            bounded(key,'sourceId',100)
            if not isinstance(value,dict) or set(value) != {'version','text'}: raise ValueError('source')
            bounded(value['version'],'sourceVersion',100);bounded(value['text'],'sourceText',20000)
        doc={'id':panel_id,'snapshot':deepcopy(snapshot),'snapshotDigest':hashlib.sha256(encode(snapshot).encode()).hexdigest(),
             'revision':0,'phase':'independent','mode':'synthetic-no-llm','host':'海青君','budget':budget,'reads':{r:[] for r in ROLES},'reviews':{},'turns':[]}
        with self.db() as c:c.execute('INSERT INTO panels VALUES (?,?)',(panel_id,encode(doc)))
        return deepcopy(doc)
    def _load(self,c,pid):
        row=c.execute('SELECT doc FROM panels WHERE id=?',(pid,)).fetchone()
        if row is None: raise ValueError('not_found')
        return json.loads(row[0])
    def context(self,pid,role):
        bounded(pid,'id',100)
        if role not in ROLES: raise ValueError('role')
        with self.db() as c:d=self._load(c,pid)
        if d['phase']=='cancelled': raise ValueError('cancelled')
        # Source content is only returned through audited read_source command.
        result={k:deepcopy(d[k]) for k in ('revision','phase','mode','host','snapshotDigest')}
        result['report']={k:d['snapshot'][k] for k in ('caseId','reportVersion','reportText')}
        result['sourceManifest']={k:v['version'] for k,v in d['snapshot']['sources'].items()}
        if d['phase']!='independent':
            result.update(reviews=deepcopy(d['reviews']),turns=deepcopy(d['turns']))
        return result
    def command(self,pid,actor,request,expected,op,payload):
        bounded(pid,'id',100)
        bounded(op,'operation',100)
        bounded(request,'request',100)
        if type(expected) is not int or expected<0: raise ValueError('revision')
        if actor not in (*ROLES,'investigator'): raise ValueError('actor')
        if not isinstance(payload,dict): raise ValueError('payload')
        digest=hashlib.sha256(encode([actor,expected,op,payload]).encode()).hexdigest()
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            d=self._load(c,pid)
            # Cancellation is a revocation barrier, including all historical receipt replay.
            if d['phase']=='cancelled': raise ValueError('cancelled')
            receipt=c.execute('SELECT digest,result FROM receipts WHERE panel=? AND request=?',(pid,request)).fetchone()
            if receipt:
                if receipt[0]!=digest: raise ValueError('request_reuse')
                return json.loads(receipt[1])
            if expected!=d['revision']: raise ValueError('revision_conflict')
            result={}
            if op=='cancel':
                if actor!='investigator' or payload: raise ValueError('human_cancel_required')
                d['phase']='cancelled'
            elif op=='read_source':
                if actor not in ROLES or set(payload)!={'sourceId','version'}: raise ValueError('read')
                sid=bounded(payload['sourceId'],'sourceId',100)
                bounded(payload['version'],'sourceVersion',100)
                source=d['snapshot']['sources'].get(sid)
                if source is None or source['version']!=payload['version']: raise ValueError('source_version')
                ref={'sourceId':sid,'version':source['version']}
                if ref not in d['reads'][actor]: d['reads'][actor].append(ref)
                result={'source':deepcopy(source),'snapshotDigest':d['snapshotDigest']}
            elif op in ('review','challenge'):
                required={'text','refs'} if op=='review' else {'text','refs','target'}
                if actor not in ROLES or set(payload)!=required: raise ValueError('speech')
                bounded(payload['text'],'text',4000)
                refs=payload['refs']
                if not isinstance(refs,list) or len(refs)>50: raise ValueError('refs')
                for ref in refs:
                    if not isinstance(ref,dict) or set(ref)!={'sourceId','version'} or ref not in d['reads'][actor]: raise ValueError('unread_reference')
                entry={'id':'review:'+actor if op=='review' else 'turn:'+str(len(d['turns'])+1),
                       'speaker':actor,'text':payload['text'],'refs':deepcopy(refs),'snapshotDigest':d['snapshotDigest']}
                if op=='review':
                    if d['phase']!='independent' or actor in d['reviews']: raise ValueError('phase')
                    d['reviews'][actor]=entry
                    if len(d['reviews'])==4:d['phase']='cross_examination'
                else:
                    bounded(payload['target'],'target',100)
                    if d['phase']!='cross_examination':raise ValueError('phase')
                    targets=list(d['reviews'].values())+d['turns']
                    target=next((v for v in targets if v['id']==payload['target']),None)
                    if target is None or target['speaker']==actor:raise ValueError('target')
                    entry['target']=target['id'];d['turns'].append(entry)
                    if len(d['turns'])>=d['budget']:d['phase']='budget_exhausted'
                result={'entry':entry}
            else:raise ValueError('operation')
            d['revision']+=1
            result.update(revision=d['revision'],phase=d['phase'],mode=d['mode'])
            c.execute('UPDATE panels SET doc=? WHERE id=?',(encode(d),pid))
            c.execute('INSERT INTO receipts VALUES (?,?,?,?)',(pid,request,digest,encode(result)))
            return deepcopy(result)
