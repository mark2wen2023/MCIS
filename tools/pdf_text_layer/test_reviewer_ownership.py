import subprocess,sys,time
import derive as module

def test_group_signal_must_precede_reaping(monkeypatch):
    spawned=[];observed=[]
    original=module.subprocess.Popen
    def spawn(*a,**kw):
        proc=original(*a,**kw);spawned.append(proc);return proc
    def signal_owned_group(pid,sig):
        # Do not signal any process. Record actual Popen-reaped state only.
        observed.append(spawned[0].returncode)
    monkeypatch.setattr(module.subprocess,'Popen',spawn)
    monkeypatch.setattr(module.os,'killpg',signal_owned_group)
    module.run_bounded([sys.executable,'-c','print("done")'],deadline=time.monotonic()+5,limit=1024)
    assert observed==[None], 'leader already reaped before process-group signal: '+repr(observed)
