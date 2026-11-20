"""Pure protocol + fake Docker only. No subprocess/app/container execution."""
import copy
import json
from pathlib import Path
import runpy
import subprocess
from types import SimpleNamespace as NS
import unittest
ROOT=Path(__file__).resolve().parents[2]
P=runpy.run_path(str(ROOT/'tools/pilot_image_acceptance/receipt.py'))
R=runpy.run_path(str(ROOT/'tools/pilot_image_acceptance/container_runner.py'))
IMAGE='sha256:'+'a'*64;CID='b'*64

def success():
    r=P['Receipt'](IMAGE)
    for stage in P['STAGES'][:-1]:r.mark(stage)
    r.cleaned();return r.finish(True)

class Checks(unittest.TestCase):
    def test_strict_single_record(self):
        good=success();self.assertEqual(P['parse'](good,IMAGE)['exitCode'],0)
        bads=[b'',good+good,b'x'*2049,b'log\n'+good,good+b' ',good.replace(b'"exitCode":0',b'"exitCode":true')]
        for changes in ({'secret':'fabricated'}, {'build':'other'}, {'image':'sha256:'+'c'*64}, {'cleanup':'unknown'}):
            d=json.loads(good);d.update(changes);bads.append(P['encode'](d))
        d=json.loads(good);d['stages']['first_import']='pending';bads.append(P['encode'](d))
        for raw in bads:
            with self.assertRaises((ValueError,TypeError)):P['parse'](raw,IMAGE)

    def test_failed_stage_contains_no_payload(self):
        r=P['Receipt'](IMAGE);r.mark('preflight');r.cleaned()
        d=P['parse'](r.finish(False),IMAGE)
        self.assertEqual(d['stages']['https_ready'],'failed');self.assertEqual(d['exitCode'],2)
        self.assertNotIn('caseId',d);self.assertEqual(d['cleanup'],'confirmed')
        with self.assertRaises(ValueError):P['Receipt'](IMAGE).mark('first_import')

    def test_outer_success_requires_all_three_confirmations(self):
        for mode in ('ok','invalid','oversize','multiple','missing','timeout','exit-unknown','exit-mismatch','cleanup-fail','cleanup-unknown','unapproved','bad-network','create-timeout','inner-failure'):
            calls=[];attached=[False];nonce=[None]
            def execute(argv,**kwargs):
                args=argv[1:];calls.append(args)
                if args[:2]==['image','inspect']:
                    d=[{'Id':IMAGE,'Config':{'User':'65532:65532','Env':['PATH=/opt/pilot/bin:/usr/bin:/bin','LANG=C.UTF-8']}}]
                elif args[0]=='create':
                    nonce[0]=args[args.index('--label')+1].split('=',1)[1]
                    if mode=='create-timeout':raise subprocess.TimeoutExpired('fabricated',20)
                    return NS(stdout=CID+'\n')
                elif args[0]=='inspect' and attached[0]:
                    d=[{'State':{'Running':mode=='exit-unknown','ExitCode':1 if mode=='exit-mismatch' else 2 if mode=='inner-failure' else 0}}]
                elif args[0]=='inspect':
                    d=[{'Image':IMAGE,'State':{'Running':False},'HostConfig':{
                        'NetworkMode':'bridge' if mode=='bad-network' else 'none','ReadonlyRootfs':True,'Privileged':False,
                        'IpcMode':'private','CapDrop':['ALL'],'SecurityOpt':['no-new-privileges'],'LogConfig':{'Type':'none'},
                        'Tmpfs':{'/run/pilot':'rw,nosuid,nodev,size=512m,mode=0700,uid=65532,gid=65532','/tmp':'rw,nosuid,nodev,size=128m,mode=1777'}},
                        'Config':{'User':'65532:65532','Labels':{'mcis.pilot.owner':nonce[0]},
                         'Cmd':[*R['COMMAND'],'--subject','SYN-PILOT-reviewer','--role','LeadInvestigator','--image',IMAGE]}}]
                elif args[0]=='rm':
                    if mode=='cleanup-fail':raise RuntimeError('fabricated sensitive body must never escape')
                    return NS(stdout='' if mode=='cleanup-unknown' else args[-1]+'\n')
                else:raise AssertionError('unexpected command')
                return NS(stdout=json.dumps(d))
            def collect(args,timeout):
                self.assertEqual(args,['start','--attach',CID]);self.assertEqual(timeout,240);attached[0]=True
                if mode=='timeout':raise subprocess.TimeoutExpired('fabricated',240)
                if mode=='inner-failure':
                    r=P['Receipt'](IMAGE);r.mark('preflight');r.cleaned();return r.finish(False),2
                raw={'invalid':b'secret-invalid','oversize':b'x'*2049,'multiple':success()*2,'missing':b''}.get(mode,success())
                return raw,0
            globals_=R['run_container'].__globals__
            globals_['APPROVED_IMAGES']=frozenset() if mode=='unapproved' else frozenset({IMAGE})
            d=R['run_container'](IMAGE,'SYN-PILOT-reviewer','LeadInvestigator',execute=execute,collect=collect)
            self.assertEqual(d['result'],'passed' if mode=='ok' else 'not_passed')
            self.assertEqual(d['exitCode'],0 if mode=='ok' else 2)
            self.assertLessEqual(len(P['encode'](d)),P['LIMIT'])
            self.assertNotIn(b'secret',P['encode'](d))
            if mode=='unapproved':self.assertEqual(calls,[])
            else:self.assertEqual(calls[-1],['rm','--force','mcis-pilot-'+nonce[0] if mode=='create-timeout' else CID])
            if mode.startswith('cleanup-'):self.assertEqual(d['containerCleanup'],'unknown')
        globals_['APPROVED_IMAGES']=frozenset()

    def test_bounded_stream_reader_with_fake_process(self):
        for mode in ('ok','oversize','timeout'):
            payload=success() if mode=='ok' else b'x'*3000
            data=bytearray(payload);events=[];done=[False]
            class Process:
                stdout=NS(fileno=lambda:7)
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def wait(self,**kwargs):events.append('wait');return 0
                def poll(self):return 0 if done[0] else None
                def kill(self):events.append('kill');done[0]=True
            class Selector:
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def register(self,*args):pass
                def select(self,timeout):return [] if mode=='timeout' else [object()]
            def read(fd,n):
                chunk=bytes(data[:n]);del data[:n]
                if not chunk:done[0]=True
                return chunk
            def popen(args,**kw):
                self.assertEqual(kw['stderr'],'discard');return Process()
            g=R['collect_receipt'].__globals__;old={k:g[k] for k in ('subprocess','selectors','time','os')}
            g.update(subprocess=NS(Popen=popen,PIPE='pipe',DEVNULL='discard'),
                     selectors=NS(DefaultSelector=Selector,EVENT_READ=1),time=NS(monotonic=lambda:0),os=NS(read=read))
            try:
                if mode=='ok':self.assertEqual(R['collect_receipt'](['start','--attach',CID]),(payload,0))
                else:
                    with self.assertRaises((ValueError,TimeoutError)):R['collect_receipt'](['start','--attach',CID])
                    self.assertIn('kill',events)
                if mode=='oversize':self.assertEqual(len(payload)-len(data),P['LIMIT']+1)
            finally:g.update(old)

    def test_build_identifier_matches_fixed_source_materials(self):
        import hashlib,re
        record=json.loads((ROOT/'logs/pilot-stage-receipt-build.json').read_text())
        hashes={}
        for name in record['files']:
            raw=(ROOT/'tools/pilot_image_acceptance'/name).read_bytes()
            if name=='receipt.py':raw=re.sub(rb"(?m)^BUILD='[^']*'$",b"BUILD=''",raw)
            hashes[name]=hashlib.sha256(raw).hexdigest()
        self.assertEqual(hashes,record['files'])
        value='sha256:'+hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.assertEqual(value,P['BUILD']);self.assertEqual(value,record['build'])

    def test_stage_markers_and_private_channel_static(self):
        import ast
        files=['prepare.py','browser_steps.py','runtime_host.py','container_entry.py','container_runner.py']
        source={f:(ROOT/'tools/pilot_image_acceptance'/f).read_text() for f in files}
        for raw in source.values():ast.parse(raw)
        self.assertIn("host.mark('cases_zero_runs')",source['prepare.py'])
        self.assertIn("host.mark('four_receipts')",source['prepare.py'])
        for stage in ('first_import','save_reopen','authorized_switch'):self.assertIn("mark('"+stage+"')",source['browser_steps.py'])
        self.assertIn('os.set_inheritable(channel,False)',source['container_entry.py'])
        self.assertLess(source['container_entry.py'].index('os.dup2'),source['container_entry.py'].index('from tools.pilot_image_acceptance.runtime_host'))
        self.assertIn('stderr=subprocess.DEVNULL',source['container_runner.py'])
        self.assertIn("'--log-driver=none'",source['container_runner.py'])
        self.assertNotIn("['logs'",source['container_runner.py'])

if __name__=='__main__':unittest.main()
