"""Manual opt-in, actual sandboxed Chromium. Never calls legacy W42 runners."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from build import build, COMPONENT_SHA

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', type=Path, required=True, help='existing supported Chromium executable')
    parser.add_argument('--output-dir', type=Path, required=True, help='new disposable artifact directory')
    args = parser.parse_args()
    if not args.browser.is_absolute() or not args.browser.is_file():
        parser.error('browser must be an existing absolute executable path')
    args.output_dir.mkdir(exist_ok=False)
    receipt = {'schema':'mcis-selection-keyboard-v1', 'baseline':'ceea6e2a990720a5b57c3afc354c7dee6ee4a03b',
               'componentSha256':COMPONENT_SHA,
               'harnessSha256':{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ('browser.py','build.py','fixture.tsx')}, 'fixture':None, 'browserVersion':None,
               'viewports':[], 'status':'failed', 'errorClass':None, 'exitCode':1}
    try:
        html = args.output_dir / 'fixture.html'
        receipt['fixture'] = build(html)
        from playwright.sync_api import sync_playwright, expect
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=str(args.browser), headless=True, chromium_sandbox=True)
            try:
                receipt['browserVersion'] = browser.version
                for width in (1440,390):
                    context = browser.new_context(viewport={'width':width,'height':900}, has_touch=False, service_workers='block')
                    try:
                        page = context.new_page(); external=[]; errors=[]
                        page.on('pageerror', lambda error: errors.append(type(error).__name__))
                        def block(route):
                            external.append('blocked'); route.abort()
                        context.route('http://**/*', block); context.route('https://**/*', block)
                        page.goto(html.resolve().as_uri())
                        a=page.get_by_role('button',name='查看证据 SYN-E-A：同名合成记录',exact=True)
                        b=page.get_by_role('button',name='查看证据 SYN-E-B：同名合成记录',exact=True)
                        expect(a).to_have_attribute('aria-pressed','true'); expect(b).to_have_attribute('aria-pressed','false')
                        page.keyboard.press('Tab'); expect(page.get_by_role('button',name='开始定位',exact=True)).to_be_focused()
                        page.keyboard.press('Tab'); expect(a).to_be_focused()
                        page.keyboard.press('Tab'); expect(b).to_be_focused()
                        expect(page.get_by_test_id('calls')).to_have_text('0')
                        page.keyboard.press('Enter')
                        expect(b).to_have_attribute('aria-pressed','true'); expect(a).to_have_attribute('aria-pressed','false')
                        expect(page.get_by_test_id('calls')).to_have_text('1')
                        page.keyboard.press('Shift+Tab'); expect(a).to_be_focused()
                        page.keyboard.press('Space')
                        expect(a).to_have_attribute('aria-pressed','true'); expect(b).to_have_attribute('aria-pressed','false')
                        expect(page.get_by_test_id('calls')).to_have_text('2')
                        expect(page.get_by_test_id('bubbled')).to_have_text('0')
                        page.keyboard.press('Tab'); page.keyboard.press('Tab')
                        expect(page.get_by_role('button',name='结束定位',exact=True)).to_be_focused()
                        assert not external and not errors, 'external request or page error'
                        screenshot=args.output_dir / f'{width}.png'; page.screenshot(path=str(screenshot),full_page=True)
                        receipt['viewports'].append({'width':width,'height':900,'touch':False,'status':'passed',
                            'checks':['accessible-names','tab-order','enter-once','space-once','pressed-state','no-bubbling','no-http-requests','no-page-errors'],
                            'screenshotSha256':hashlib.sha256(screenshot.read_bytes()).hexdigest()})
                    finally:
                        context.close()
            finally:
                browser.close()
        receipt.update(status='passed',exitCode=0)
    except Exception as error:
        receipt['errorClass']=type(error).__name__
    finally:
        (args.output_dir/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False))
    return receipt['exitCode']

if __name__ == '__main__':
    sys.exit(main())
