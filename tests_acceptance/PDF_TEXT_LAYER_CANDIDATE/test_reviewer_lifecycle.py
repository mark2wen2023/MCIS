import os,signal,sys,time
import pytest
import derive as module

@pytest.mark.parametrize('cap',['waitid','WNOWAIT','P_PID','CLD_EXITED'])
def test_missing_platform_capability_refuses_before_spawn(monkeypatch,cap):
 monkeypatch.delattr(module.os,cap)
 monkeypatch.setattr(module.subprocess,'Popen',lambda *a,**k:pytest.fail('unexpected spawn'))
 with pytest.raises(module.DerivationError,match='unsupported_process_lifecycle'):
  module.run_bounded(['unused'],deadline=time.monotonic()+1,limit=100)

def test_ignored_sigchld_refuses_before_spawn(monkeypatch):
 monkeypatch.setattr(module.signal,'getsignal',lambda sig:signal.SIG_IGN)
 monkeypatch.setattr(module.subprocess,'Popen',lambda *a,**k:pytest.fail('unexpected spawn'))
 with pytest.raises(module.DerivationError,match='unsupported_process_lifecycle'):
  module.run_bounded(['unused'],deadline=time.monotonic()+1,limit=100)

def test_actual_nonreaping_observation_then_signal_then_wait(monkeypatch):
 events=[];spawn=module.subprocess.Popen;observe=module.os.waitid;kill=module.os.killpg
 def child(*a,**kw):
  p=spawn(*a,**kw);wait=p.wait
  def reap(*args,**kwargs):events.append(('wait',p.returncode));return wait(*args,**kwargs)
  p.wait=reap;return p
 def seen(kind,pid,flags):
  assert flags & os.WNOWAIT
  r=observe(kind,pid,flags)
  if r is not None:events.append(('observed',r.si_status))
  return r
 def killing(pid,sig):events.append(('kill',sig));return kill(pid,sig)
 monkeypatch.setattr(module.subprocess,'Popen',child)
 monkeypatch.setattr(module.os,'waitid',seen)
 monkeypatch.setattr(module.os,'killpg',killing)
 assert module.run_bounded([sys.executable,'-c','print("ok")'],deadline=time.monotonic()+3,limit=100)[0]==b'ok\n'
 assert [x[0] for x in events]==['observed','kill','wait']
 assert events[-1][1] is None
