"""Parent-controlled hard deadline for the fixed one-request provider worker."""
import asyncio
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from research.expert_meeting.machine import canonical, strict
from research.expert_remote.transport import TransportError, MAX_BYTES, validate_meta
from research.expert_group.engine import _assistant
from research.expert_executor.ownership import require_support, observe, exit_code, cleanup

ROOT=Path(__file__).resolve().parents[2]


def _command(mocked):
    return [sys.executable,'-m','research.expert_remote.worker']+(['--mock'] if mocked else [])


async def request(messages,tools,*,key,deadline,cancel=None,mocked=False,managed_binding=None):
    proc=None;sent=0;data=b'';result=None;error=None;observed=None;reaped=False
    try:
        if type(mocked) is not bool:raise TransportError('worker_mode')
        if (cancel and cancel()) or time.monotonic()>=deadline:raise TransportError('cancelled')
        config={'messages':messages,'tools':tools,'key':key,'deadline':deadline}
        worker_env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'}
        if managed_binding is not None:
            if mocked or key is not None:raise TransportError('managed_mode_invalid')
            from research.expert_remote.managed import resolve
            material=resolve(managed_binding)
            worker_env.update(material.environment)
            config['managedBinding']=managed_binding
        payload=canonical(config)
        if len(payload)>MAX_BYTES+16384:raise TransportError('request_limit')
        require_support()
        proc=subprocess.Popen(_command(mocked),cwd=ROOT,env=worker_env,
             stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True,bufsize=0)
        os.set_blocking(proc.stdin.fileno(),False);os.set_blocking(proc.stdout.fileno(),False)
        while True:
            if (cancel and cancel()) or time.monotonic()>=deadline:raise TransportError('cancelled_or_deadline',True)
            if sent<len(payload):
                try:sent+=os.write(proc.stdin.fileno(),payload[sent:sent+65536])
                except BlockingIOError:pass
                if sent==len(payload):proc.stdin.close()
            try:chunk=os.read(proc.stdout.fileno(),65536)
            except BlockingIOError:chunk=b''
            data+=chunk
            if len(data)>MAX_BYTES:raise TransportError('worker_output_limit',True)
            status=observe(proc)
            if status is not None:
                observed=exit_code(status)
                if observed!=0:raise TransportError('worker_exit',True)
                # Kill any owned descendants before draining, preserving PID ownership.
                observed=cleanup(proc);reaped=True
                while True:
                    try:tail=os.read(proc.stdout.fileno(),65536)
                    except BlockingIOError:break
                    if not tail:break
                    data+=tail
                    if len(data)>MAX_BYTES:raise TransportError('worker_output_limit',True)
                output=strict(data)
                if output.get('ok') is not True:raise TransportError('provider_worker_rejected',True)
                if set(output)!={'ok','result','transportMocked'} or output['transportMocked'] is not mocked:raise TransportError('worker_mode_mismatch',True)
                result=output['result']
                if type(result) is not dict or set(result)!={'assistant','responseMeta','identityVerified'} or result['identityVerified'] is not False:
                    raise TransportError('worker_result_invalid',True)
                validate_meta(result['responseMeta'])
                normalized,_=_assistant(result['assistant'])
                if canonical(normalized)!=canonical(result['assistant']):raise TransportError('worker_result_invalid',True)
                break
            await asyncio.sleep(.01)
    except BaseException as exc:
        error=TransportError(exc.code,exc.dispatched or proc is not None) if isinstance(exc,TransportError) else TransportError('worker_interrupted',proc is not None)
    finally:
        if proc is not None:
            try:
                if not reaped:
                    observed=cleanup(proc);reaped=True
            except Exception:
                error=TransportError('worker_cleanup_unknown',True)
            finally:
                try:
                    if not proc.stdin.closed:proc.stdin.close()
                    proc.stdout.close()
                except Exception:error=TransportError('worker_cleanup_unknown',True)
    worker={'processStarted':proc is not None,'leaderReaped':reaped,'exitObserved':observed,'transportMocked':mocked}
    if error is not None:
        error.worker=worker
        raise error from None
    result['worker']=worker
    return result
