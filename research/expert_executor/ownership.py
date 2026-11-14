"""Owned child groups require an exclusive reaper and stable SIGCHLD=SIG_DFL.

This module cannot enforce that another host thread never reaps our child. Such
hosts are unsupported; checks detect loss but are not an atomic PID capability.
"""
import os
import signal
import time


class OwnershipError(RuntimeError):
    pass


def require_support(*, probe=True):
    if os.name != 'posix' or not callable(getattr(os,'waitid',None)) or any(not hasattr(os,n) for n in ('P_PID','WEXITED','WNOHANG','WNOWAIT','CLD_EXITED')):
        raise OwnershipError('waitid_ownership_required')
    if not hasattr(signal,'SIGCHLD') or signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
        raise OwnershipError('default_sigchld_required')
    if probe:
        # A process cannot be its own child. ECHILD proves this precise waitid
        # option combination is implemented without spawning or reaping anything.
        try: os.waitid(os.P_PID,os.getpid(),os.WEXITED|os.WNOHANG|os.WNOWAIT)
        except ChildProcessError: pass
        except Exception: raise OwnershipError('waitid_probe_failed') from None
        else: raise OwnershipError('waitid_probe_failed')


def _lost(proc):
    proc._mcis_ownership_lost = True
    raise OwnershipError('child_ownership_lost') from None


def observe(proc):
    if getattr(proc,'_mcis_ownership_lost',False) or proc.returncode is not None: _lost(proc)
    try: require_support(probe=False)
    except OwnershipError: _lost(proc)
    try: status=os.waitid(os.P_PID,proc.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
    except ChildProcessError: _lost(proc)
    if status is not None and status.si_pid != proc.pid: _lost(proc)
    return status


def exit_code(status):
    return status.si_status if status.si_code == os.CLD_EXITED else -status.si_status


def cleanup(proc):
    # Recheck immediately before signalling. Exclusive-reaper contract is required
    # across this check/kill interval; no poll()/wait() or SIGCHLD mutation elsewhere.
    observe(proc)
    try: os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError: pass
    deadline=time.monotonic()+5
    while True:
        try: status=os.waitid(os.P_PID,proc.pid,os.WEXITED|os.WNOHANG)
        except ChildProcessError: _lost(proc)
        if status is not None:
            if status.si_pid != proc.pid: _lost(proc)
            code=exit_code(status)
            proc.returncode=code  # Already reaped by our waitid, never Popen.wait's ECHILD fallback.
            return code
        if time.monotonic()>=deadline:raise OwnershipError('child_reap_timeout')
        time.sleep(.01)
