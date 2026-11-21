"""Reuse fixed node adapter and real synthetic registration; new edge is fixture-only."""
from copy import deepcopy
from pathlib import Path
import json
import os
import runpy
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
FIXED='2a1af988df07ebde97336829fe361188b05c9146'
for rel in ('research/ecfc_associated_position/check.py','research/ecfc_associated_position/display.py'):
    if (ROOT/rel).read_bytes()!=subprocess.check_output(['git','show',FIXED+':'+rel],cwd=ROOT):
        raise RuntimeError('Fixed node adapter differs')
base=runpy.run_path(str(ROOT/'research/ecfc_associated_position/check.py'))
ui=runpy.run_path(str(Path(__file__).with_name('selection.py')))

class Checks(base['Associated']):
    def graph(self):
        env,association=self.fixture()
        doc=env['document'];node=dict(doc['draft']['nodes'][0],id='event2',text='Synthetic second hypothesis',timeSeconds=None,evidenceIds=[])
        edge=dict(id='edge1',**{'from':'event1','to':'event2'})
        doc['draft']['nodes'].append(node);doc['draft']['edges']=[edge]
        doc['validation']['nodes'].append(dict(node,isPresumptive=True))
        doc['validation']['edges']=[dict(edge,kind='Sequence',bold=True)]
        result=subprocess.run(['node','-e',"const m=require(process.argv[1]);let s='';process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>{const e=JSON.parse(s);m.parseEnvelope(e,e.caseId)})",str(MODEL)],input=json.dumps(env),text=True,capture_output=True,check=True)
        return env,association

    def mapping(self,env):
        # Separate, artificial fragment; NOT registered original or an authorized read.
        fragment=dict(origin='synthetic_fixture',caseId=self.cid,version='fixture-r1',
                      sourceUtc='2026-02-01T12:00:37.000Z',locator={'jsonPointer':'/fragments/0'})
        association=dict(origin='synthetic_fixture',graphKey=ui['edge_key'](env,'edge1'),
                         fragmentVersion='fixture-r1',locator=deepcopy(fragment['locator']))
        return association,fragment

    def test_node_and_edge_keep_distinct_sources_and_no_event_seek(self):
        env,node_assoc=self.graph();before=deepcopy(env)
        node=ui['node_display'](self.render(env,node_assoc,self.query()))
        a,f=self.mapping(env);edge=ui['edge_display'](env,'edge1',a,f)
        self.assertEqual(node['locator'],{'jsonPointer':'/points/7'})
        self.assertEqual(node['sourceUtc'],base['UTC']);self.assertEqual(node['manualTimeSeconds'],17)
        self.assertEqual(edge['locator'],{'jsonPointer':'/fragments/0'})
        self.assertEqual(edge['sourceUtc'],'2026-02-01T12:00:37.000Z');self.assertIsNone(edge['replayUtc'])
        for result in (node,edge):
            self.assertFalse(result['seekAvailable']);self.assertFalse(result['eventVerified'])
            self.assertIsNone(result['uncertaintySeconds']);self.assertEqual(result['status'],'待审')
            for key in ('evidenceId','requestDigest','sourceSha256','original'):self.assertNotIn(key,json.dumps(result))
        self.assertEqual(edge['evidenceDirection'],'未判定');self.assertEqual(env,before)
        self.assertEqual(self.counts(),(2,4,4)) # one actual pair read; edge adds zero Access

    def test_new_graph_version_invalidates_old_edge_and_late_completion(self):
        env,_=self.graph();a,f=self.mapping(env);view=ui['Selection']()
        old=view.select(env,'edge1');result=ui['edge_display'](env,'edge1',a,f)
        self.assertTrue(view.finish(old,result));self.assertIsNotNone(view.visible)
        new=deepcopy(env);new['document']['revision']=2;new['document']['digest']='b'*64
        current=view.select(new,'edge1');self.assertIsNone(view.visible)
        self.assertFalse(view.finish(old,result));self.assertFalse(view.finish(old,None));self.assertIsNone(view.visible)
        self.assertIsNone(ui['edge_display'](new,'edge1',a,f))
        a2,f2=self.mapping(new);self.assertTrue(view.finish(current,ui['edge_display'](new,'edge1',a2,f2)))
        self.assertEqual(view.visible['status'],'待审');self.assertEqual(self.counts(),(2,2,2))

    def test_deleted_edge_changed_endpoint_and_fragment_do_not_borrow(self):
        env,_=self.graph();a,f=self.mapping(env);view=ui['Selection']();old=view.select(env,'edge1')
        result=ui['edge_display'](env,'edge1',a,f);view.finish(old,result)
        removed=deepcopy(env);removed['document']['draft']['edges']=[]
        view.select(removed,'edge1');self.assertIsNone(view.visible);self.assertFalse(view.finish(old,result))
        self.assertIsNone(ui['edge_display'](removed,'edge1',a,f))
        changed=deepcopy(env);changed['document']['draft']['edges'][0].update({'from':'event2','to':'event1'})
        self.assertIsNone(ui['edge_display'](changed,'edge1',a,f))
        for field,value in [('caseId','SYN-OTHER'),('version','fixture-r2'),('locator',{'jsonPointer':'/points/7'})]:
            self.assertIsNone(ui['edge_display'](env,'edge1',a,{**f,field:value}))
        self.assertEqual(self.counts(),(2,2,2))

if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use existing Python -I -B')
    esbuild=os.environ.get('MCIS_ESBUILD')
    if not esbuild or not Path(esbuild).is_file():raise SystemExit('Existing MCIS_ESBUILD required')
    with tempfile.TemporaryDirectory(prefix='ecfc-edge-display-') as folder:
        root=Path(folder);ts=root/'model.ts';MODEL=root/'model.cjs'
        ts.write_bytes(subprocess.check_output(['git','show',base['ECFC']+':web/src/ecfcDrafts/model.ts'],cwd=ROOT))
        subprocess.run([esbuild,str(ts),'--platform=node','--format=cjs','--outfile='+str(MODEL)],check=True)
        base['Associated'].fixture.__globals__['MODEL']=MODEL
        pilot=base['pilot'];source=pilot['base']['materialize'](root/'source',ref=pilot['REF'],paths=pilot['BASE'])
        ok=pilot['base']['run'](source,extra_cases=(Checks,),allowed_paths=pilot['BASE'])
    raise SystemExit(0 if ok else 1)
