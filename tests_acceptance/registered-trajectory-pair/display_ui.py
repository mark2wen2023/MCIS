"""Real A registration -> fixed B consumer -> allowlisted display -> existing UI.
No HTTP, browser, report, model, original-text delivery or saved output.
"""
import importlib.util
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FIXED='e0cbccc83b13598c7ff118798ec7c56e472d413b'

def load(name):
    path=HERE/'seat_receiver'/(name+'.py')
    spec=importlib.util.spec_from_file_location('_seat_ui_'+name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module

if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use existing Python -I -B')
    # B and A boundary files stay byte-identical; no weakened pin/shape validation.
    for rel in ['seat_handoff.py']+['seat_receiver/'+n for n in ('run.py','check.py','receiver.py','fixed_objects.py','README.md')]:
        expected=subprocess.check_output(['git','show',FIXED+':tests_acceptance/registered-trajectory-pair/'+rel],cwd=ROOT)
        if (HERE/rel).read_bytes()!=expected:raise RuntimeError('Fixed handoff dependency differs: '+rel)
    objects=load('fixed_objects');dependencies=objects.fixed_dependencies(ROOT);receiver=load('receiver')
    count=[]
    with tempfile.TemporaryDirectory(prefix='seat-ui-') as folder:
        page=Path(folder)/'shell.html'
        runpy.run_path(str(ROOT/'tools/replay_evidence_workbench/registered_build.py'))['build'](page, display_only=True)
        def consume(record):
            note=receiver.consumer(record,dependencies=dependencies)
            assert note['saved'] is False and note['factActivated'] is False
            assert all(s['timeReview']=='pending' for s in note['summaries'])
            projection=runpy.run_path(str(HERE/'display_projection.py'))['project']
            safe=projection(record,validate_host_record=lambda r: receiver.consumer(r,dependencies=dependencies))
            wire=json.dumps(safe)
            for key in ('original','pins','evidenceId','requestDigest','sourceSha256'):
                assert key not in wire
            for v in record['frames'][0]['vessels']:
                for key in ('evidenceId','requestDigest','sourceSha256'):
                    assert v['original'][key] not in wire
            from copy import deepcopy
            bad=deepcopy(record);bad['frames'][0]['vessels'][0]['original']['sourceSha256']='0'*64
            try:
                projection(bad,validate_host_record=lambda r: receiver.consumer(r,dependencies=dependencies))
            except receiver.ReviewError:
                pass
            else:
                raise AssertionError('Invalid host source must not produce display output')
            subprocess.run(['node',str(HERE/'display_ui.cjs'),str(page)],input=wire,text=True,check=True)
            count.append(1)
        ok=runpy.run_path(str(HERE/'seat_handoff.py'))['run_handoff'](consume)
    assert len(count)==1,'Expected one successful actual receiver/UI callback'
    print('Actual host validation -> pin-free display callback completed once; temporary output removed')
    raise SystemExit(0 if ok else 1)
