"""UNEXECUTED offline container controller. No image is approved in this revision."""
import argparse
import json
import re
import subprocess
import sys
import secrets
import selectors
import time
import os
from pathlib import Path
import runpy
_protocol=runpy.run_path(str(Path(__file__).with_name('receipt.py')))
Receipt=_protocol['Receipt'];parse_receipt=_protocol['parse'];encode_receipt=_protocol['encode'];LIMIT=_protocol['LIMIT']


def collect_receipt(args,timeout=240):
    # Bounded streaming, no communicate()/capture_output of browser text, no log file.
    with subprocess.Popen(['docker',*args],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL) as process:
        raw=bytearray();deadline=time.monotonic()+timeout
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout,selectors.EVENT_READ)
                while True:
                    remaining=deadline-time.monotonic()
                    if remaining<=0 or not selector.select(remaining):raise TimeoutError('receipt deadline')
                    chunk=os.read(process.stdout.fileno(),min(256,LIMIT+1-len(raw)))
                    if not chunk:break
                    raw.extend(chunk)
                    if len(raw)>LIMIT:raise ValueError('receipt budget')
            return bytes(raw),process.wait(timeout=max(.01,deadline-time.monotonic()))
        finally:
            if process.poll() is None:process.kill()
            process.wait()


def run_container(image,subject,role,*,execute=subprocess.run,collect=collect_receipt):
    report=Receipt(image).value
    report['containerCleanup']='confirmed'  # no container exists before create
    try:_run_container(image,subject,role,report=report,execute=execute,collect=collect)
    except BaseException:report['exitCode']=2
    passed=(report['exitCode']==0 and report['containerExitCode']==0
            and report['containerCleanup']=='confirmed' and report['cleanup']=='confirmed'
            and all(v=='passed' for v in report['stages'].values()))
    report['result']='passed' if passed else 'not_passed'
    if not passed:report['exitCode']=2
    return report

# Reviewed OFFLINE image IDs only; approval requires source/dependency/browser
# closure and absence of business data, seeds, credentials and model assets.
# A user-provided SHA or image label is NOT evidence of that review.
APPROVED_IMAGES = frozenset()
COMMAND = ('/opt/pilot/bin/python', '-I', '/opt/pilot/entry.py')


def _run_container(image, subject, role, *, report, execute, collect):
    if image not in APPROVED_IMAGES or not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
        raise RuntimeError('No reviewed offline image; blocked before container creation')
    if (not isinstance(subject,str) or not re.fullmatch(r'SYN-PILOT-[A-Za-z0-9_.-]{1,64}',subject)
            or role not in ('Investigator','LeadInvestigator')):
        raise RuntimeError('Explicit synthetic server identity required')
    def call(args, timeout=20):
        return execute(['docker',*args],check=True,capture_output=True,text=True,timeout=timeout).stdout
    info=json.loads(call(['image','inspect',image]))[0]
    config=info['Config']
    if (info['Id']!=image or config.get('Volumes') or config.get('ExposedPorts')
            or config.get('User')!='65532:65532' or config.get('Entrypoint') not in (None,[])
            or config.get('Env')!=['PATH=/opt/pilot/bin:/usr/bin:/bin','LANG=C.UTF-8']):
        raise RuntimeError('Offline image configuration changed')
    nonce=secrets.token_hex(16)
    name="mcis-pilot-"+nonce
    cid=None;creation_attempted=False
    try:
        creation_attempted=True
        report['containerCleanup']='unknown'
        cid=call(['create','--name',name,'--label','mcis.pilot.owner='+nonce,'--pull=never','--network=none','--read-only','--cap-drop=ALL',
                  '--security-opt=no-new-privileges','--user=65532:65532','--pids-limit=256',
                  '--memory=2g','--cpus=2','--log-driver=none',
                  '--tmpfs=/run/pilot:rw,nosuid,nodev,size=512m,mode=0700,uid=65532,gid=65532',
                  '--tmpfs=/tmp:rw,nosuid,nodev,size=128m,mode=1777',
                  '--shm-size=256m',image,*COMMAND,'--subject',subject,'--role',role,'--image',image]).strip()
        if not re.fullmatch('[0-9a-f]{64}',cid):
            raise RuntimeError('Container creation identity unconfirmed')
        state=json.loads(call(['inspect',cid]))[0];hc=state['HostConfig']
        if (state['Image']!=image or state['State']['Running'] or hc['NetworkMode']!='none'
                or not hc['ReadonlyRootfs'] or hc['Privileged'] or hc.get('Binds')
                or hc.get('PortBindings') or hc.get('Devices') or hc.get('CapAdd')
                or hc.get('PidMode') or hc.get('IpcMode') not in ('private','')
                or hc.get('CapDrop')!=['ALL'] or hc.get('SecurityOpt')!=['no-new-privileges']
                or hc.get('LogConfig',{}).get('Type')!='none'
                or hc.get('Tmpfs')!={'/run/pilot':'rw,nosuid,nodev,size=512m,mode=0700,uid=65532,gid=65532',
                                       '/tmp':'rw,nosuid,nodev,size=128m,mode=1777'}
                or any(m.get('Type')!='tmpfs' or m.get('Destination') not in ('/run/pilot','/tmp') for m in state.get('Mounts',[]))
                or state['Config'].get('Labels',{}).get('mcis.pilot.owner')!=nonce
                or state['Config']['User']!='65532:65532'
                or tuple(state['Config']['Cmd'])!=(*COMMAND,'--subject',subject,'--role',role,'--image',image)):
            raise RuntimeError('Container isolation configuration unconfirmed')
        report['stages']={s:'unknown' for s in report['stages']}
        raw,attached_exit=collect(['start','--attach',cid],timeout=240)
        inner=parse_receipt(raw,image)
        report.update(inner)
        state=json.loads(call(['inspect',cid]))[0]['State']
        code=state.get('ExitCode')
        if state.get('Running') is not False or type(code) is not int or not 0<=code<=255:
            raise RuntimeError('Container exit unknown')
        report['containerExitCode']=code
        if type(attached_exit) is not int or attached_exit!=code or code!=inner['exitCode']:
            raise RuntimeError('Exit/receipt disagreement')
    finally:
        # Remove only the ID returned by this create. Stop/kill on timeout/failure,
        # no host path deletion; Docker removes its private tmpfs/processes.
        if cid and re.fullmatch('[0-9a-f]{64}',cid):
            if call(['rm','--force',cid]).strip()!=cid:raise RuntimeError('Cleanup not confirmed')
            report['containerCleanup']='confirmed'
        elif creation_attempted:
            # CLI timeout can leave a daemon-side create in progress. Inspect the
            # unique owned name, never retry creation. Failure/absence here is
            # uncertain cleanup, not success; an operator must reconcile it.
            try:
                pending=json.loads(call(['inspect',name]))[0]
                if pending['Config'].get('Labels',{}).get('mcis.pilot.owner')!=nonce:
                    raise RuntimeError('Unconfirmed container ownership')
                if call(['rm','--force',name]).strip()!=name:raise RuntimeError('Cleanup not confirmed')
                report['containerCleanup']='confirmed'
            except Exception:
                raise RuntimeError('Container creation/cleanup outcome unconfirmed') from None


def main():
    class Parser(argparse.ArgumentParser):
        def error(self,message):raise ValueError('Invalid arguments')
    parser=Parser(add_help=False,description='Approval-required offline synthetic image acceptance')
    parser.add_argument('--image',required=True);parser.add_argument('--subject',required=True)
    parser.add_argument('--role',required=True,choices=('Investigator','LeadInvestigator'))
    try:
        args=parser.parse_args()
        result=run_container(args.image,args.subject,args.role)
    except Exception:result=Receipt(None).value
    sys.stdout.buffer.write(encode_receipt(result))
    return result['exitCode']

if __name__=='__main__':raise SystemExit(main())
