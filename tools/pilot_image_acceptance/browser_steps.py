"""NOT EXECUTED. Approved host supplies an already authenticated same-origin page.
No browser launch, cookies, credentials, network client or permission probes here.
"""
import re
from urllib.parse import urlsplit, parse_qs
from .fixtures import CASE_IDS
from .prepare import checked


async def review_in_same_origin_page(page, prepared):
    """Future browser adapter continuation, kept within the host cleanup scope.

    Use only after explicit browser/HTTP/ORM approval. A timeout stops; no action
    retry, no permission override. The selected control is switching authorized
    cases, NOT an unapproved permission-denial probe.
    """
    checked(prepared.get('caseId')==CASE_IDS[0] and type(prepared.get('imageRuns')) is int
            and prepared['imageRuns']==0 and set(prepared['bindings'])=={'pdf','image','raw','candidate'},
            'Preparation result incomplete')
    parsed=urlsplit(page.url)
    checked(parsed.scheme=='https' and parsed.hostname=='127.0.0.1'
            and not parsed.username and not parsed.password,'Trusted HTTPS loopback page required')
    origin=parsed.scheme+'://'+parsed.netloc
    await page.goto(origin+'/pilot')
    await page.locator('#refresh').click()
    await page.get_by_role('button',name=re.compile('^'+re.escape(CASE_IDS[0])+' ·')).click()
    link=page.locator('#image-entry a')
    await link.wait_for(state='visible',timeout=10000)
    checked(await link.get_attribute('href')=='/pilot/image-review?case='+CASE_IDS[0],'Wrong case link')
    await link.click()
    checked(await page.locator('#case').input_value()==CASE_IDS[0],'Case prefill mismatch')
    checked(await page.locator('#run').input_value()=='','Expected no run before first import')
    # Expand the existing import panel before filling its hidden inputs.
    await page.get_by_text('导入已登记结果',exact=True).click()
    for kind,digest in prepared['bindings'].items():
        checked(isinstance(digest,str) and re.fullmatch('[0-9a-f]{64}',digest) is not None,'Invalid confirmed receipt')
        await page.locator('#'+kind).fill(digest)
    await page.locator('#ack').check()
    await page.locator('#create').click()
    await page.locator('#lines article').first.wait_for(state='visible',timeout=10000)
    query=parse_qs(urlsplit(page.url).query)
    checked(query.get('case')==[CASE_IDS[0]] and len(query.get('run',[]))==1
            and re.fullmatch('OCR-[a-f0-9]{32}',query['run'][0]) is not None,'Accepted run address not confirmed')
    run=query['run'][0]
    line=page.locator('#lines article').first
    revised='SYNTHETIC LINE — manually revised for acceptance'
    await line.locator('textarea').fill(revised)
    await line.get_by_label('核对理由',exact=True).fill('Synthetic exercise; no original authenticity claim')
    await line.get_by_role('button',name='追加本行核对记录',exact=True).click()
    await page.wait_for_function("document.querySelector('#lines article [role=status]')?.textContent.includes('上次确认保存修订 1')",timeout=10000)
    await page.reload()
    await page.locator('#lines article').first.wait_for(state='visible',timeout=10000)
    checked(parse_qs(urlsplit(page.url).query).get('run')==[run],'Reload changed run')
    checked(await page.locator('#lines article').first.locator('textarea').input_value()==revised,'Saved text not reread')
    # Switch on workbench: B must be B, never A's metadata/link. No media data is
    # copied into the workspace; this is not a delayed-response browser test.
    await page.goto(origin+'/pilot')
    await page.locator('#refresh').click()
    for cid in CASE_IDS:
        await page.get_by_role('button',name=re.compile('^'+re.escape(cid)+' ·')).click()
        await page.wait_for_function("expected => document.querySelector('#context')?.textContent === '当前案号：'+expected",arg=cid,timeout=10000)
        checked(await page.locator('#image-entry a').get_attribute('href')=='/pilot/image-review?case='+cid,'Workspace case/link mismatch')
    return {'caseId':CASE_IDS[0],'runId':run,'revision':1,'sourceVerified':False,
            'checked':'first import, one revision, reload, authorized workspace case switch'}
