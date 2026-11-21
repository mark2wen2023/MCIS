"""Synthetic server scopes / atomic memory store, not real authorization or ORM."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import unittest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
MODULES = ROOT/'service/mcis_service/reports'

def functions(path, names, env):
    tree = ast.parse((ROOT/path).read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, 'exec'), env)
    return env

load = functions('tests_acceptance/audio-reference-range/check.py', ['load'], dict(ast=ast, MODULES=MODULES))['load']
p = load('media_reference.py')
r = load('media_reference_reader.py', p)
a = load('audio_reference_range.py', r)
g = load('generation_snapshot.py')
b = load('sentence_binding.py', dict(generation_sentence=g['generation_sentence'], read_exact_audio_range=a['read_exact_audio_range']))
fixture = functions('tests_acceptance/media-report-reference/check.py', ['fixture'], dict(A='a'*64,B='b'*64,C='c'*64,D='d'*64))['fixture']
reports = functions('tests_acceptance/report-generation-snapshot/check.py', ['report','inputs'], dict(deepcopy=deepcopy))
validator = Draft202012Validator(json.loads((ROOT/'contracts/schemas/report.schema.json').read_text()))
prepare, decide = b['prepare_audio_binding'], b['decide_binding']

class MemoryStore(b['BindingStore']):
    def __init__(self): self.rows = {}
    def get(self, key): return self.rows.get(key)
    def insert_if_absent(self, key, payload): return self.rows.setdefault(key, payload)

class Scope(b['BindingReadScope']):
    """Entirely handmade; no assertion that these methods authenticate a user."""
    def __init__(self, unknown=False):
        self.calls=[]; self.denied=None; self.data=fixture('audio')
        initial, human = [r['doc'] for r in self.data['saved_rows']]
        initial['audio']=dict(format='PCM_WAV',channels=1,sampleWidthBytes=2,sampleRateHz=8000,frames=96000)
        initial['machineDraft']['version']=3
        initial['machineDraft']['source'].update(durationMs=12000,frameCount=96000,sampleRateHz=8000)
        human.update(reason='synthetic',operator='synthetic',role='Investigator',utc='2026-01-01T00:00:00Z',speaker={'status':'unknown','id':None},startMs=None if unknown else 1000,endMs=None if unknown else 2500,timeStatus='unknown' if unknown else 'operator_declared')
        self.report=reports['report']('RPT-'+'1'*20,1,'Synthetic frozen sentence')
        self.report.update(caseId='CASE-SYN',reportHref='#/report?case=CASE-SYN')
        self.generation=reports['inputs'](self.report,1)
        self.key=('CASE-SYN',self.generation['snapshot']['snapshotId'],'section-synthetic','sentence-synthetic')
        digest=r['read_exact_media_reference'](reader=self.reader(),media='audio',case_id='CASE-SYN',evidence_id='EV-A',evidence_role='audio',run_id='RUN-SYN',revision=1)['referenceSha256']
        self.pin=dict(zip(('caseId','generationSnapshotId','sectionId','sentenceId'),self.key),auditSeq=1,reportId=self.report['reportId'],familyId=self.report['familyId'],version=1,media='audio',evidenceId='EV-A',runId='RUN-SYN',revision=1,segmentId='SEG-SYN',referenceSha256=digest)
        self.calls.clear()
    def require_generation_access(self,key):
        self.calls.append('report_gate')
        if self.denied=='report': raise PermissionError('synthetic denied')
    def read_generation(self,key): self.calls.append('generation'); return deepcopy(self.generation)
    def validate_contract(self,name,value):
        assert name=='report'; validator.validate(value)
    def read_pin(self,key): self.calls.append('pin'); return deepcopy(self.pin)
    def require_media_access(self,key,pin):
        self.calls.append('media_gate')
        if self.denied=='media': raise PermissionError('synthetic denied')
    def media_reader(self,key,pin): self.calls.append('reader'); return self.reader()
    def reader(self):
        parent=self
        class Reader:
            case_id='CASE-SYN'
            def read_revision(self,media,run,revision):
                parent.calls.append(('revision',media,run,revision))
                return deepcopy([x for x in parent.data['saved_rows'] if x['case_id']==self.case_id and x['run_id']==run and x['revision']==revision])
            def read_evidence(self,eid):
                parent.calls.append(('evidence',eid))
                return deepcopy(next(x for x in parent.data['evidence_items'] if x['evidenceId']==eid))
        return Reader()

class Tests(unittest.TestCase):
    def test_exact_read_order_and_atomic_idempotence(self):
        s=Scope(); raw=prepare(scope=s,key=s.key); store=MemoryStore()
        self.assertEqual(s.calls,['report_gate','generation','pin','media_gate','reader',('revision','audio','RUN-SYN',0),('revision','audio','RUN-SYN',1),('evidence','EV-A')])
        self.assertEqual(decide(key=s.key,proposed=raw,existing=store.get(s.key)),'insert_required')
        self.assertEqual(decide(key=s.key,proposed=raw,existing=store.insert_if_absent(s.key,raw)),'identical')
        self.assertEqual(decide(key=s.key,proposed=prepare(scope=s,key=s.key),existing=store.get(s.key)),'identical')
        self.assertEqual(set(json.loads(raw)),{'contract','key','pin','sentenceSha256'})
        self.assertEqual(json.loads(raw)['pin']['referenceSha256'],s.pin['referenceSha256'])
    def test_every_immutable_payload_change_conflicts(self):
        s=Scope(); raw=prepare(scope=s,key=s.key); doc=json.loads(raw)
        for field in s.pin:
            altered=deepcopy(doc); old=altered['pin'][field]
            altered['pin'][field]=('f'*64 if field=='referenceSha256' else old+1 if type(old) is int else old+'changed')
            changed=b['_bytes'](altered); store=MemoryStore();store.insert_if_absent(s.key,raw)
            with self.assertRaises(b['BindingConflict']): decide(key=s.key,proposed=changed,existing=store.insert_if_absent(s.key,changed))
            self.assertEqual(store.get(s.key),raw)
        altered=deepcopy(doc);altered['sentenceSha256']='f'*64
        with self.assertRaises(b['BindingConflict']): decide(key=s.key,proposed=b['_bytes'](altered),existing=raw)
    def test_no_context_and_denial_before_reads(self):
        s=Scope()
        for scope in (None,{},True):
            with self.assertRaises(b['BindingUnavailable']): prepare(scope=scope,key=s.key)
        s.require_generation_access=lambda key:False
        with self.assertRaises(b['BindingUnavailable']): prepare(scope=s,key=s.key)
        self.assertEqual(s.calls,[])
        s=Scope();s.media_reader=lambda key,pin:None
        with self.assertRaises(b['BindingUnavailable']): prepare(scope=s,key=s.key)
        for phase, calls in [('report',['report_gate']),('media',['report_gate','generation','pin','media_gate'])]:
            s=Scope();s.denied=phase
            with self.assertRaises(PermissionError): prepare(scope=s,key=s.key)
            self.assertEqual(s.calls,calls)
    def test_non_generation_missing_duplicate_sentence(self):
        for mutation in ('action','missing','duplicate','snapshot'):
            s=Scope(); snap=s.generation['snapshot']; sentences=snap['afterValue']['sections'][0]['sentences']
            if mutation=='action': s.generation['audit_event']['action']='report.review'
            if mutation=='missing': sentences[0]['sentenceId']='different'
            if mutation=='duplicate': sentences.append(deepcopy(sentences[0]))
            if mutation=='snapshot': snap['snapshotId']='RA-'+'f'*32
            with self.assertRaises(ValueError): prepare(scope=s,key=s.key)
            self.assertNotIn('pin',s.calls)
    def test_cross_case_wrong_pin_sha_missing_revision(self):
        for field,value in [('caseId','OTHER'),('auditSeq',2),('reportId','RPT-'+'2'*20),('generationSnapshotId','RA-'+'2'*32),('referenceSha256','f'*64),('referenceSha256',None),('segmentId','OTHER'),('revision',9)]:
            s=Scope();s.pin[field]=value
            with self.assertRaises(ValueError): prepare(scope=s,key=s.key)
        s=Scope();s.pin.pop('version')
        with self.assertRaises(ValueError): prepare(scope=s,key=s.key)
        s=Scope();s.data['saved_rows'][1]['doc']['text']='changed saved body'
        with self.assertRaises(ValueError): prepare(scope=s,key=s.key)
        s=Scope();s.data['saved_rows'][1]['case_id']='OTHER'
        with self.assertRaises(ValueError): prepare(scope=s,key=s.key)
    def test_absent_not_corrupt_unknown_not_zero(self):
        s=Scope(True); raw=prepare(scope=s,key=s.key)
        result=a['read_exact_audio_range'](reader=s.reader(),case_id=s.key[0],evidence_id='EV-A',run_id='RUN-SYN',revision=1,segment_id='SEG-SYN',expected_reference_sha256=s.pin['referenceSha256'])
        self.assertIsNone(result['startMs']);self.assertIsNone(result['endMs'])
        self.assertNotIn('audio',json.loads(raw))
        s.pin=None;self.assertIsNone(prepare(scope=s,key=s.key))
        self.assertEqual(decide(key=s.key,proposed=None,existing=None),'no_historical_reference')
        for stored in (b'{}',b'invalid',b'null',b'',False):
            with self.assertRaises(b['BindingCorrupt']): decide(key=s.key,proposed=raw,existing=stored)
        with self.assertRaises(b['BindingConflict']): decide(key=s.key,proposed=None,existing=raw)
        s.pin={}
        with self.assertRaises(b['BindingUnavailable']): prepare(scope=s,key=s.key)
    def test_later_revision_and_generation_never_replace_old(self):
        s=Scope();old=prepare(scope=s,key=s.key);oldkey=s.key;oldgen=deepcopy(s.generation);oldpin=deepcopy(s.pin)
        later=deepcopy(s.data['saved_rows'][1]);later['revision']=2;later['doc'].update(revision=2,expectedRevision=1,startMs=4000,endMs=5500);s.data['saved_rows'].append(later)
        s.report['sections'][0]['sentences'][0]['textZh']='Current row edit'
        self.assertEqual(prepare(scope=s,key=s.key),old)
        parent=oldgen['snapshot']['afterValue'];new=reports['report']('RPT-'+'2'*20,2,'New sentence',parent['reportId']);new.update(caseId='CASE-SYN',reportHref='#/report?case=CASE-SYN')
        s.generation=reports['inputs'](new,2,parent);s.key=(oldkey[0],s.generation['snapshot']['snapshotId'],*oldkey[2:])
        digest=r['read_exact_media_reference'](reader=s.reader(),media='audio',case_id='CASE-SYN',evidence_id='EV-A',evidence_role='audio',run_id='RUN-SYN',revision=2)['referenceSha256']
        s.pin.update(generationSnapshotId=s.key[1],reportId=new['reportId'],auditSeq=2,version=2,revision=2,referenceSha256=digest)
        fresh=prepare(scope=s,key=s.key);store=MemoryStore();store.insert_if_absent(oldkey,old);store.insert_if_absent(s.key,fresh)
        self.assertEqual(len(store.rows),2);self.assertEqual(json.loads(fresh)['pin']['revision'],2)
        s.key=oldkey;s.generation=oldgen;s.pin=oldpin
        self.assertEqual(prepare(scope=s,key=oldkey),old);self.assertEqual(store.get(oldkey),old)

    def test_no_prose_and_changed_frozen_sentence_conflicts(self):
        s=Scope();phrase='SYNTHETIC_PRIVATE_SENTENCE_7Q9'
        sentence=s.generation['snapshot']['afterValue']['sections'][0]['sentences'][0]
        sentence['textZh']=phrase
        sentence['generatedText']['textZh']=phrase+'_generated'
        raw=prepare(scope=s,key=s.key)
        self.assertNotIn(phrase.encode(),raw)
        self.assertEqual(b['_sentence_digest'](sentence),b['_sentence_digest'](dict(reversed(list(sentence.items())))))
        for field in (b'textZh',b'citations',b'generatedText',b'operator',b'startMs',b'endMs'):
            self.assertNotIn(field,raw)
        sentence['textZh']=phrase+'_changed'
        changed=prepare(scope=s,key=s.key)
        self.assertNotEqual(json.loads(raw)['sentenceSha256'],json.loads(changed)['sentenceSha256'])
        self.assertEqual(json.loads(raw)['pin'],json.loads(changed)['pin'])
        with self.assertRaises(b['BindingConflict']): decide(key=s.key,proposed=changed,existing=raw)

    def test_bounded_corrupt_bytes_both_operands(self):
        s=Scope();raw=prepare(scope=s,key=s.key)
        bad=[json.dumps(raw.decode()).encode(),b'['*10000+b'0'+b']'*10000,
             b'['*9+b'0'+b']'*9,b' '* (b['MAX_RECORD_BYTES']+1),
             b'{"x":NaN}',b'{"x":1,"x":2}',b'\xff',b'{}',b'null',
             raw.replace(b'"pin":',b'"pin":null,"discard":')]
        for corrupt in bad:
            for kwargs in (dict(proposed=raw,existing=corrupt),dict(proposed=corrupt,existing=raw)):
                with self.assertRaises(b['BindingCorrupt']): decide(key=s.key,**kwargs)
        # JSON escaping/brackets in a permitted identifier are not nesting.
        doc=json.loads(raw);doc['pin']['evidenceId']='EV-[]{}"\\'
        escaped=b['_bytes'](doc)
        self.assertEqual(decide(key=s.key,proposed=escaped,existing=escaped),'identical')
        # Old content-bearing v1 envelopes explicitly fail, no silent migration.
        old=b['_bytes'](dict(contract='frozen-sentence-audio-binding/1',key=list(s.key),pin=s.pin,generation={},audio={}))
        with self.assertRaises(b['BindingCorrupt']): decide(key=s.key,proposed=raw,existing=old)

    def test_sentence_hash_limits_and_range_revalidation(self):
        for value in ('x'*(b['MAX_SENTENCE_BYTES']+1), [[[[None]]]]):
            if type(value) is list:
                for _ in range(34):value=[value]
            with self.assertRaises(b['BindingUnavailable']): b['_sentence_digest'](value)
        for unknown in (False,True):
            s=Scope(unknown);raw=prepare(scope=s,key=s.key)
            self.assertEqual(decide(key=s.key,proposed=prepare(scope=s,key=s.key),existing=raw),'identical')
            s.data['saved_rows'][0]['doc']['audio']['frames']=1
            with self.assertRaises(ValueError): prepare(scope=s,key=s.key)

if __name__=='__main__': unittest.main()
