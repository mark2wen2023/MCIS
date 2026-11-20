"""UNEXECUTED offline container controller. No image is approved in this revision."""
import argparse
import json
import re
import subprocess
import sys
import secrets

# Reviewed OFFLINE image IDs only; approval requires source/dependency/browser
# closure and absence of business data, seeds, credentials and model assets.
# A user-provided SHA or image label is NOT evidence of that review.
APPROVED_IMAGES = frozenset()
COMMAND = ('/opt/pilot/bin/python', '-I', '/opt/pilot/entry.py')


def run_container(image, subject, role, *, execute=subprocess.run):
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
        cid=call(['create','--name',name,'--label','mcis.pilot.owner='+nonce,'--pull=never','--network=none','--read-only','--cap-drop=ALL',
                  '--security-opt=no-new-privileges','--user=65532:65532','--pids-limit=256',
                  '--memory=2g','--cpus=2','--log-driver=none',
                  '--tmpfs=/run/pilot:rw,nosuid,nodev,size=512m,mode=0700,uid=65532,gid=65532',
                  '--tmpfs=/tmp:rw,nosuid,nodev,size=128m,mode=1777',
                  '--shm-size=256m',image,*COMMAND,'--subject',subject,'--role',role]).strip()
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
                or tuple(state['Config']['Cmd'])!=(*COMMAND,'--subject',subject,'--role',role)):
            raise RuntimeError('Container isolation configuration unconfirmed')
        call(['start',cid])
        result=call(['wait',cid],timeout=240).strip()
        if result!='0':raise RuntimeError('Synthetic acceptance failed; no success claimed')
        return {'status':'passed','scope':'synthetic image workflow only','image':image}
    finally:
        # Remove only the ID returned by this create. Stop/kill on timeout/failure,
        # no host path deletion; Docker removes its private tmpfs/processes.
        if cid and re.fullmatch('[0-9a-f]{64}',cid):
            call(['rm','--force',cid])
        elif creation_attempted:
            # CLI timeout can leave a daemon-side create in progress. Inspect the
            # unique owned name, never retry creation. Failure/absence here is
            # uncertain cleanup, not success; an operator must reconcile it.
            try:
                pending=json.loads(call(['inspect',name]))[0]
                if pending['Config'].get('Labels',{}).get('mcis.pilot.owner')!=nonce:
                    raise RuntimeError('Unconfirmed container ownership')
                call(['rm','--force',name])
            except Exception:
                print('CLEANUP UNCONFIRMED: reconcile owned container '+name,file=sys.stderr)
                raise RuntimeError('Container creation/cleanup outcome unconfirmed') from None


def main():
    parser=argparse.ArgumentParser(description='Approval-required offline synthetic image acceptance')
    parser.add_argument('--image',required=True);parser.add_argument('--subject',required=True)
    parser.add_argument('--role',required=True,choices=('Investigator','LeadInvestigator'))
    args=parser.parse_args()
    try:result=run_container(args.image,args.subject,args.role)
    except Exception:
        print('BLOCKED/FAILED: no acceptance result; inspect approved configuration and owned-resource cleanup',file=sys.stderr)
        return 2
    print(json.dumps(result));return 0

if __name__=='__main__':raise SystemExit(main())
