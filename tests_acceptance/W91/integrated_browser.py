"""W9/W5 cross-navigation smoke on combined main; real API and browser."""
import asyncio,json,pathlib,sys
from playwright.async_api import async_playwright,expect
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'W82'))
from harness import servers,request,payload
OUT=pathlib.Path(__file__).parent/'artifacts'
async def run():
 with servers(web=True) as (api,web):
  cid='W91-W5-INTEGRATED';assert request(api,'/cases',payload(cid))[0]==201
  vessel={'caseId':cid,'vesselId':'one','name':'Synthetic integrated vessel'}
  assert request(api,f'/cases/{cid}/vessels',vessel)[0]==201
  async with async_playwright() as pw:
   browser=await pw.chromium.launch(executable_path='/tmp/w8-headless/chrome-headless-shell-linux64/chrome-headless-shell',headless=True,args=['--no-sandbox'])
   page=await browser.new_page(viewport={'width':1440,'height':1000})
   await page.goto(web+'/#/ships?case='+cid)
   await expect(page.locator('.w9-vessel')).to_contain_text(vessel['name'])
   await page.locator('a.nav-item[href*="/interview"]').click()
   assert 'case='+cid in page.url
   await expect(page.locator('[data-testid="ic-roster"]')).to_contain_text('当前案件暂无询问笔录')
   await expect(page.locator('.case-chip')).to_contain_text(cid)
   await expect(page.locator('.main')).not_to_contain_text('Lily')
   await page.locator('a.nav-item[href*="/ships"]').click()
   assert 'case='+cid in page.url
   await expect(page.locator('.w9-vessel')).to_contain_text(vessel['name'])
   await page.go_back();await expect(page.locator('[data-testid="ic-roster"]')).to_contain_text('当前案件暂无询问笔录')
   await page.go_forward();await expect(page.locator('.w9-vessel')).to_contain_text(vessel['name'])
   await page.locator('.role-select').select_option('Public')
   await expect(page.get_by_role('button',name='＋ 新增船舶')).to_have_count(0)
   await expect(page.locator('.w9-vessel')).to_contain_text(vessel['name'])
   await browser.close()
 OUT.joinpath('integrated-cross-navigation.json').write_text(json.dumps({'status':'PASS','case':cid,'flow':'Ships → Interview empty → Ships → Back → Forward → Public readonly'},ensure_ascii=False,indent=2))
 print('Integrated ships/interview real-HTTP browser roundtrip PASS')
asyncio.run(run())
