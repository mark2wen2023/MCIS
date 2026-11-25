import json, os, socket, subprocess, time
from pathlib import Path
from urllib.request import urlopen

WT=Path('/workspace/mcis-w19-9c878b1')
SERVICE_PY='/workspace/mcis-w17-871db66/service/.venv/bin/python'
SHOT=Path('/workspace/mcis-w19-report/screenshots')
SHOT.mkdir(exist_ok=True)

def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0)); return s.getsockname()[1]
def ready(url):
    for _ in range(100):
        try:
            urlopen(url, timeout=1); return
        except Exception:
            time.sleep(.1)
    raise SystemExit('not ready '+url)

webport,apiport=port(),port()
web,api=f'http://127.0.0.1:{webport}',f'http://127.0.0.1:{apiport}'
env={k:v for k,v in os.environ.items() if k in ('HOME','PATH','LD_LIBRARY_PATH','LANG','LC_ALL','TMPDIR')}
root=Path('/tmp/mcis-w19-probe'); root.mkdir(exist_ok=True)
(root/'data').mkdir(exist_ok=True)
api_log=open(root/'api.log','w')
web_log=open(root/'web.log','w')
ap=subprocess.Popen([SERVICE_PY,'-B','-m','mcis_service'],cwd=WT/'service',env={**env,'MCIS_SEED_DEMO':'0','MCIS_PORT':str(apiport),'MCIS_DATA_DIR':str(root/'data')},stdout=api_log,stderr=subprocess.STDOUT)
vp=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(webport),'--strictPort'],cwd=WT/'web',env={**env,'MCIS_API':api},stdout=web_log,stderr=subprocess.STDOUT)
try:
    ready(api+'/api/v1/knowledge/cards')
    ready(web+'/')
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/opt/google/chrome/google-chrome',headless=True,chromium_sandbox=True,args=['--no-proxy-server'])
        context=browser.new_context(service_workers='block')
        page=context.new_page(); page.set_default_timeout(12000)
        page.goto(web+'/#/knowledge')
        page.locator('select.role-select').select_option('LeadInvestigator')
        page.get_by_text('人工创建候选（不会自动公开）',exact=True).wait_for()
        page.screenshot(path=str(SHOT/'probe-01-after-role.png'),full_page=True)
        info={}
        info['details_open_before']=page.locator('details.w19-create').evaluate('e=>e.open')
        page.get_by_text('人工创建候选（不会自动公开）',exact=True).click()
        info['details_open_after_click']=page.locator('details.w19-create').evaluate('e=>e.open')
        page.screenshot(path=str(SHOT/'probe-02-after-summary-click.png'),full_page=True)
        btn=page.get_by_role('button',name='在表单中填入合成示例（不保存）')
        info['sample_btn_visible']=btn.is_visible()
        info['sample_btn_enabled']=btn.is_enabled()
        btn.click()
        info['details_open_after_sample']=page.locator('details.w19-create').evaluate('e=>e.open')
        page.screenshot(path=str(SHOT/'probe-03-after-sample.png'),full_page=True)
        labels=page.evaluate('''() => [...document.querySelectorAll('label')].map(l=>({
          text:(l.childNodes[0]&&l.childNodes[0].textContent||'').trim(),
          disabled:!!(l.closest('fieldset')&&l.closest('fieldset').disabled)
        }))''')
        info['labels']=labels
        info['title_count']=page.get_by_label('标题',exact=True).count()
        fs=page.locator('details.w19-create fieldset')
        info['fieldset_disabled_js']=fs.evaluate('e=>e.disabled') if fs.count() else None
        print(json.dumps(info,ensure_ascii=False,indent=2))
        browser.close()
finally:
    for p in (vp,ap):
        p.terminate()
        try: p.wait(timeout=5)
        except Exception:
            p.kill(); p.wait()
