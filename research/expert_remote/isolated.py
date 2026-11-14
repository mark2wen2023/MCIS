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

ROOT=Path(__file__).resolve().parents[2]


def _command(mocked):
    return [sys.executable,'-m','research.expert_remote.worker']+(['--mock'] if mocked else [])


async def request(messages,tools,*,key,deadline,cancel=None,mocked=False):
    proc=None;sent=0;data=b'';result=None;error=None;observed=None;reaped=False
    try:
        if type(mocked) is not bool:raise TransportError('worker_mode')
        if (cancel and cancel()) or time.monotonic()>=deadline:raise TransportError('cancelled')
        payload=canonical({'messages':messages,'tools':tools,'key':key,'deadline':deadline})
        if len(payload)>MAX_BYTES+16384:raise TransportError('request_limit')
        proc=subprocess.Popen(_command(mocked),cwd=ROOT,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},
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
            status=os.waitid(os.P_PID,proc.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
            if status is not None:
                observed=status.si_status if status.si_code==os.CLD_EXITED else -status.si_status
                if observed!=0:raise TransportError('worker_exit',True)
                # Kill any owned descendants before draining, preserving PID ownership.
                try:os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                proc.wait(timeout=5);reaped=True
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
                    try:os.killpg(proc.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    observed=proc.wait(timeout=5);reaped=True
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
