"""Deterministic real SQLite second-connection interleavings on synthetic cases."""
import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from tests.test_evidence_intake_w42 import local,prepared,save,counts,URL,CASE
from mcis_service.evidence_intake import router as intake
from mcis_service.db import put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy


def provision(app):
 with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',default_policy())
 return app.state.settings.resolved_db_url.removeprefix('sqlite:///')


def revoke(database,timeout=0.05,started=None):
 policy=default_policy();policy['matrix']['Investigator']['evidence_meta']='Deny'
 with sqlite3.connect(database,timeout=timeout) as conn:
  if started:started.set()
  try:
   conn.execute('UPDATE access_policies SET doc=? WHERE case_id=? AND key=?',
                (json.dumps(policy),CASE,'policy'))
   conn.commit();return 'committed'
  except sqlite3.OperationalError as exc:
   if 'locked' not in str(exc):raise
   return 'locked'


@pytest.mark.parametrize('replay',[False,True])
def test_revoke_after_final_authorization_cannot_commit_inside_intake(local,monkeypatch,replay):
 client,app=local;database=provision(app)
 request=save(client)[0] if replay else prepared(client)
 initial=counts(app);real=intake.authorize;calls=[];outcomes=[]
 def checked(ctx,s,case_id,*,write=False):
  result=real(ctx,s,case_id,write=write)
  if write:
   calls.append(True)
   if len(calls)==2:
    with ThreadPoolExecutor(1) as pool:outcomes.append(pool.submit(revoke,database).result(timeout=2))
  return result
 monkeypatch.setattr(intake,'authorize',checked)
 response=client.post(URL+':commit',json=request)
 assert response.status_code==200,response.text
 assert outcomes==['locked'],('other connection revoked before successful write',outcomes,response.status_code)
 assert counts(app)==initial if replay else counts(app)==tuple(n+1 for n in initial)
 assert revoke(database)=='committed'
 before=counts(app)
 assert client.post(URL+':commit',json=request).status_code==403
 assert counts(app)==before


@pytest.mark.parametrize('replay',[False,True])
def test_revoke_before_final_transaction_refuses_without_new_writes(local,monkeypatch,replay):
 client,app=local;database=provision(app)
 request=save(client)[0] if replay else prepared(client)
 before=counts(app);read=intake.body_bounded
 async def revoked(request):
  body=await read(request)
  assert revoke(database)=='committed'
  return body
 monkeypatch.setattr(intake,'body_bounded',revoked)
 assert client.post(URL+':commit',json=request).status_code==403
 assert counts(app)==before
 if not replay:assert not list(app.state.settings.blob_dir.rglob('source.bin'))


@pytest.mark.parametrize('fail_write',[False,True])
def test_waiting_revocation_proceeds_only_after_commit_or_rollback(local,monkeypatch,fail_write):
 client,app=local;database=provision(app);request=prepared(client)
 before=counts(app);real=intake.authorize;calls=[];futures=[];attempted=threading.Event()
 with ThreadPoolExecutor(1) as pool:
  def checked(ctx,s,case_id,*,write=False):
   result=real(ctx,s,case_id,write=write)
   if write:
    calls.append(True)
    if len(calls)==2:
     future=pool.submit(revoke,database,2,attempted);futures.append(future)
     assert attempted.wait(1)
     # Synchronize with a bounded real writer attempt, not a fake policy callback.
     try:outcome=future.result(timeout=0.05)
     except TimeoutError:pass
     else:pytest.fail('revocation completed before intake boundary: '+outcome)
   return result
  monkeypatch.setattr(intake,'authorize',checked)
  if fail_write:
   original=intake.exclusive_write
   def failed(path,raw,created):
    original(path,raw,created)
    raise OSError('synthetic write fault')
   monkeypatch.setattr(intake,'exclusive_write',failed)
  response=client.post(URL+':commit',json=request)
  assert response.status_code==(500 if fail_write else 200),response.text
  assert futures[0].result(timeout=3)=='committed'
 assert counts(app)==before if fail_write else counts(app)==tuple(n+1 for n in before)
 if fail_write:assert not list(app.state.settings.blob_dir.rglob('source.bin'))
 assert client.post(URL+':commit',json=request).status_code==403
