"""Opt-in real Chromium test. Only intercepted local assets; no server or backend."""
import argparse, hashlib, json
from pathlib import Path
from urllib.parse import urlparse, unquote

predicates=(Path(__file__).with_name('predicates.js')).read_text()
p=argparse.ArgumentParser()
p.add_argument('--chromium',required=True, type=Path)
p.add_argument('--dist',required=True,type=Path)
p.add_argument('--output',required=True,type=Path)
a=p.parse_args()
if not a.chromium.is_file() or not (a.dist/'index.html').is_file():p.error('existing Chromium and built fixture required')
if a.output.exists():p.error('output must be a new directory')
from playwright.sync_api import sync_playwright

a.output.mkdir(parents=True)
receipt={'schema':'mcis-evidence-page-browser-1','passed':False,'fixtureSha256':{},'checks':[],'externalRequests':0}
for f in sorted(a.dist.rglob('*')):
 if f.is_file():receipt['fixtureSha256'][str(f.relative_to(a.dist))]=hashlib.sha256(f.read_bytes()).hexdigest()
try:
 with sync_playwright() as pw:
  # Playwright default disables sandbox: explicitly enable it. No custom launch flags.
  browser=pw.chromium.launch(executable_path=str(a.chromium.resolve()),headless=True,chromium_sandbox=True)
  receipt['browserVersion']=browser.version
  for width in (1440,390):
   context=browser.new_context(viewport={'width':width,'height':900},service_workers='block')
   external=[]; errors=[]
   def route(r):
    u=urlparse(r.request.url)
    path=(a.dist/unquote(u.path).lstrip('/')).resolve()
    if u.scheme!='https' or u.netloc!='mcis-synthetic.invalid' or not path.is_relative_to(a.dist.resolve()) or not path.is_file():
     external.append('blocked');receipt['externalRequests']+=1;r.abort();return
    r.fulfill(path=str(path))
   context.route('**/*',route)
   page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
   def req(baseline,case_id,operator):
    handle=page.wait_for_function('(a)=>{'+predicates+'; return window.gate && matchingRequest(gate.requests(),a[0],a[1],a[2]);}',arg=[baseline,case_id,operator])
    result=handle.json_value();handle.dispose();return result
   def action(name,case_id,operator='SYNTHETIC-ONE'):
    baseline=page.evaluate('gate.latestId()')
    page.get_by_role('button',name=name,exact=True).click()
    return req(baseline,case_id,operator)
   def settle(i,kind,title=''):
    page.evaluate('(v)=>gate.settle(...v)',[i,kind,title])
   def metrics(value):
    page.wait_for_function('(v)=>{'+predicates+'; return fourMetrics(Array.from(document.querySelectorAll(".w4-metrics .val")).slice(0,4).map(x=>x.textContent),v);}',arg=value)
   for late in ('data','deny'):
    page.goto('https://mcis-synthetic.invalid/index.html')
    old=req(0,'SYN-A','SYNTHETIC-ONE');metrics('待载入');settle(old,'data','OLD-A')
    page.get_by_role('button',name='OLD-A',exact=True).wait_for()
    b=action('Case B','SYN-B')
    assert 'OLD-A' not in page.locator('.w4-page').inner_text()
    stale=action('Case A','SYN-A')
    current=action('Case B','SYN-B')
    settle(current,'data','CURRENT-B');page.get_by_role('button',name='CURRENT-B',exact=True).wait_for()
    settle(stale,late,'LATE-A');settle(b,late,'LATE-B')
    # Allow promise, effects and rendering opportunities before checking absence.
    page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
    text=page.locator('.w4-page').inner_text()
    assert 'CURRENT-B' in text and 'LATE-' not in text and 'OLD-A' not in text and 'CURRENT-DENIAL' not in text
    # A pending request issued under old identity must not overwrite current denial.
    identity_old=action('Case A','SYN-A')
    identity_new=action('Synthetic identity change','SYN-A','SYNTHETIC-TWO')
    assert identity_old!=identity_new
    settle(identity_new,'deny','CURRENT-DENIAL');metrics('不可用')
    settle(identity_old,late,'LATE-IDENTITY')
    page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
    metrics('不可用')
    assert 'LATE-IDENTITY' not in page.locator('.w4-page').inner_text()
    assert 'CURRENT-DENIAL' in page.locator('.w4-page').inner_text()
    assert '暂无证据' not in page.locator('.w4-page').inner_text()
    settle(action('Case B','SYN-B','SYNTHETIC-TWO'),'empty')
    page.get_by_text('暂无证据，请添加调查证据。',exact=True).wait_for()
    assert page.locator('.w4-metrics .val').all_text_contents()[:4]==['0条','0/ 0','0条','0条']
    assert not page.evaluate('gate.unexpected()')
    receipt['checks'].append({'width':width,'touch':False,'late':late,'passed':True})
   assert not external and not errors, 'unexpected network or page error'
   page.screenshot(path=str(a.output/f'empty-{width}.png'),full_page=True)
   context.close()
  browser.close()
 receipt['passed']=True
finally:
 (a.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('PASS EvidencePage synthetic Chromium lifecycle; no real authorization/backend')
