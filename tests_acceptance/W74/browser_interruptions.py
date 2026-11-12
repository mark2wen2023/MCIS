"""Component-level browser doubles for interruptions. Real HTTP integration is separate."""
import os,signal,subprocess,time,urllib.request,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];html=ROOT/'web/tests/.tmp-w74-acceptance.html'
html.write_text('''<div id="root"></div><script type="module">
import React from 'react';
import {createRoot} from 'react-dom/client';
import {RecommendationReview} from '/src/recommendationReview/RecommendationReview.tsx';
import {setIdentity} from '/src/api.ts';
setIdentity('LeadInvestigator','Synthetic Operator');const root=createRoot(document.getElementById('root'));
window.mount=(caseId='A',recId='SR-2026-01')=>root.render(React.createElement(RecommendationReview,{caseId,recId}));window.mount();
</script>''')
s=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15876','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15876',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox']);p=b.new_page(viewport={'width':390,'height':844});p.set_default_timeout(6000)
  held=[];calls=[];mode={'hold':False,'audit_error':False,'invalid':False,'empty':False}
  def body(case,rec,label='CURRENT_BODY'):
   return dict(caseId=case,id=rec,title='Synthetic',addressee='Synthetic recipient',body=label,status='Draft',causeNodeIds=['N1'],createdUtc='2026-11-01T00:00:00Z',dueUtc='2026-12-01T00:00:00Z',responses=[])
  def event(case,rec):return dict(caseId=case,entityId=rec,entityType='recommendation',category='SafetyRec',seq=1,utc='2026-11-01T00:00:00Z',operator='synthetic',action='safetyrec.update',command='AUDIT_SUMMARY',before='',after='safe',line='NEVER_RAW_LINE',snapshotRef='NEVER_SNAPSHOT')
  def route(r):
   u=r.request.url;calls.append((r.request.method,u));case=u.split('/cases/')[1].split('/')[0];rec=u.split('/recommendations/')[1].split('/')[0]
   if mode['hold']:held.append((r,case,rec));return
   if u.endswith('/history'):
    if mode['audit_error']:r.fulfill(status=403,json={'message':'NEVER_ERROR_ORIGINAL'});return
    r.fulfill(json=[event(case,rec)]);return
   d=body(case,rec)
   if mode['invalid']:d['responses']=[{'party':'p','text':'FIRST_NOT_PARTIAL','utc':'2026-11-01T00:00:00Z'},None]
   if mode['empty']:d['body']='';d['responses']=[]
   r.fulfill(json=d)
  p.route('**/api/v1/**',route);p.goto('http://127.0.0.1:15876/tests/.tmp-w74-acceptance.html')
  panel=p.get_by_role('region',name='安全建议只读核查');panel.wait_for()
  def open():panel.get_by_role('button',name='读取正文与登记回复',exact=True).click()
  def waitheld():
   for _ in range(60):
    p.wait_for_timeout(20)
    if held:return
   raise AssertionError('no held request')
  def late(label='STALE_BODY'):
   r,c,i=held.pop(0)
   try:r.fulfill(json=[event(c,i)] if r.request.url.endswith('/history') else body(c,i,label))
   except Exception:pass
   p.wait_for_timeout(80);assert label not in panel.inner_text()
  assert calls==[]
  # Keyboard open, separate audit success then403: keep body, clear previous audit.
  panel.get_by_role('button',name='读取正文与登记回复',exact=True).focus();p.keyboard.press('Enter');panel.get_by_text('CURRENT_BODY',exact=True).wait_for()
  panel.get_by_role('button',name='读取审计摘要',exact=True).click();panel.get_by_text('#1 · AUDIT_SUMMARY',exact=True).wait_for();assert 'NEVER_' not in panel.inner_text()
  mode['audit_error']=True;panel.get_by_role('button',name='重新读取审计摘要',exact=True).click();panel.get_by_text('审计：后端拒绝',exact=False).wait_for();assert 'AUDIT_SUMMARY' not in panel.inner_text() and 'CURRENT_BODY' in panel.inner_text() and 'NEVER_' not in panel.inner_text()
  mode['audit_error']=False;mode['hold']=True;panel.get_by_role('button',name='重新读取完整内容').click();waitheld();assert 'CURRENT_BODY' not in panel.inner_text();assert '审计：后端拒绝' not in panel.inner_text()
  panel.get_by_role('button',name='关闭核查',exact=True).click();late()
  # Close/open a new request before releasing the old request must retain only newest.
  open();waitheld();panel.get_by_role('button',name='关闭核查',exact=True).click();mode['hold']=False;open();panel.get_by_text('CURRENT_BODY',exact=True).wait_for();late();assert 'CURRENT_BODY' in panel.inner_text()
  for action in ["window.mount('A','SR-2026-02')","window.mount('B','SR-2026-02')","location.hash='#different'","(await import('/src/api.ts')).setIdentity('LeadInvestigator','Different Synthetic Operator')"]:
   mode['hold']=True;panel.get_by_role('button',name='重新读取完整内容').click();waitheld()
   p.evaluate('async()=>{'+action+'}');panel.get_by_role('button',name='读取正文与登记回复',exact=True).wait_for();late()
   mode['hold']=False;open();panel.get_by_text('CURRENT_BODY',exact=True).wait_for()
  # Invalid reply anywhere rejects the complete batch; empty legal content gets explicit placeholders.
  mode['invalid']=True;panel.get_by_role('button',name='重新读取完整内容').click();panel.get_by_text('响应格式或连接异常',exact=False).wait_for();assert 'FIRST_NOT_PARTIAL' not in panel.inner_text() and 'CURRENT_BODY' not in panel.inner_text()
  mode['invalid']=False;mode['empty']=True;panel.get_by_role('button',name='重新读取完整内容').click();panel.get_by_text('未记录正文，不能据此认定建议内容完整。',exact=True).wait_for();panel.get_by_text('尚无已登记回复。',exact=True).wait_for()
  assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
  mode['hold']=True;panel.get_by_role('button',name='读取审计摘要',exact=True).click();waitheld();panel.get_by_role('button',name='关闭核查',exact=True).click();late('AUDIT_SUMMARY')
  before=len(calls);p.evaluate("async()=>{(await import('/src/api.ts')).setIdentity('Public')}");panel.get_by_text('本核查入口仅向调查组开放',exact=False).wait_for();p.wait_for_timeout(80);assert len(calls)==before
  assert all(m=='GET' for m,u in calls);p.unroute_all(behavior='ignoreErrors');b.close()
 print('W74 independent component browser: keyboard, audit403 isolation, refresh/close/reopen/rec/case/navigation/operator late-result discard, malformed whole batch, empty placeholders,mobile,Public no reader calls,GET-only passed')
finally:os.killpg(s.pid,signal.SIGTERM);s.wait();html.unlink(missing_ok=True)
