"""Run shipped browser checker, adding independent live DOM/capture assertions."""
import importlib.util,json,sys
from pathlib import Path
from playwright.sync_api import Page
ROOT=Path(__file__).resolve().parents[2]
PHRASE='无W10时1.2.0工作记录扩展；含W10时须1.3.0'
seen=[];original_goto=Page.goto;original_shot=Page.screenshot
output=Path(sys.argv[sys.argv.index('--output')+1])
def goto(self,url,*args,**kwargs):
 result=original_goto(self,url,*args,**kwargs)
 if '/#/lobby?' in url:
  self.get_by_text(PHRASE,exact=False).first.wait_for()
  self.wait_for_function('(s)=>document.body.innerText.split(s).length-1>=2',arg=PHRASE)
  assert self.locator('body').inner_text().count(PHRASE)>=2
  seen.append('lobby package/preflight+export exact copy visible')
  original_shot(self,path=str(output/('independent-lobby-'+str(len(seen))+'.png')),full_page=True)
 return result
def screenshot(self,*args,**kwargs):
 if '/#/report?' in self.url or '/#/interview?' in self.url:
  assert PHRASE in self.locator('body').inner_text()
  seen.append('report/interview exact version copy visible')
 return original_shot(self,*args,**kwargs)
Page.goto=goto;Page.screenshot=screenshot
spec=importlib.util.spec_from_file_location('stage_browser',ROOT/'tools/stage-demo/browser_check.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.main()
assert len(seen)==6,seen
(output/'independent-dom.json').write_text(json.dumps({'status':'passed','checks':seen},ensure_ascii=False,indent=2))
