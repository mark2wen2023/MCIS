"""Offline legacy path lifecycle checks; no model or authenticated import."""
import concurrent.futures
import json
import sys
import time
import pytest
import assemble as a

def test_legacy_real_concurrency_keeps_contract():
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  packets=list(pool.map(lambda _:a.assemble_bundle(a.MATERIAL),range(2)))
 for bundle in packets:
  assert bundle['linkage']['linkStatus']=='unknown_no_derivative'
  assert bundle['admissionAllowed'] is False
  assert bundle['packet']['locator']['pdfPage']==24
  assert bundle['packet']['locator']['printedPage']==22
  assert bundle['packet']['candidate']['status']=='Candidate'
 assert packets[0]['packet']['candidate']['content']==packets[1]['packet']['candidate']['content']

@pytest.mark.parametrize('kind',['timeout','nonzero','overflow','warning','version'])
def test_failed_legacy_does_not_write(kind,tmp_path,monkeypatch):
 original=a.run_bounded
 calls=[]
 def controlled(argv,*,deadline,limit):
  calls.append(argv)
  if kind=='timeout':return original([sys.executable,'-c','import time;time.sleep(5)'],deadline=time.monotonic()+.15,limit=limit)
  if kind=='nonzero':return original([sys.executable,'-c','raise SystemExit(7)'],deadline=deadline,limit=limit)
  if kind=='overflow':return original([sys.executable,'-c','print("x"*1000)'],deadline=deadline,limit=20)
  if kind=='warning':return b'not used',b'warning'
  if argv[-1]=='-v':raise a.DerivationError('parser_failed')
  return original(argv,deadline=deadline,limit=limit)
 monkeypatch.setattr(a,'run_bounded',controlled)
 out=tmp_path/'result.json';start=time.monotonic()
 assert a.main(['--material-id',a.MATERIAL,'--bundle','--output',str(out)])==2
 assert not out.exists() and not list(tmp_path.glob('.pending-*'))
 assert time.monotonic()-start<4
 assert calls

def test_shared_deadline_and_snapshot(tmp_path,monkeypatch):
 original=a.run_bounded;seen=[]
 def spy(argv,*,deadline,limit):
  seen.append((argv,deadline,limit))
  return original(argv,deadline=deadline,limit=limit)
 monkeypatch.setattr(a,'run_bounded',spy)
 a.assemble(a.MATERIAL)
 assert len(seen)==2 and seen[0][1]==seen[1][1]
 assert seen[0][2]==2*1024*1024 and seen[1][2]==16384
