"""Server-controlled pilot page shaping, never a URL capability or authentication."""
from .._review_page import _review_page
from .workbench_skin import CSS, image_shell


def workbench_page(html, *, images):
    if type(images) is not bool or html.count('const imagePageAvailable=false;') != 1:
        raise ValueError('pilot workbench capability marker mismatch')
    if html.count('/* pilot-workbench-skin */') != 1:
        raise ValueError('pilot skin marker mismatch')
    html = html.replace('/* pilot-workbench-skin */', CSS)
    return html.replace('const imagePageAvailable=false;', 'const imagePageAvailable=true;') if images else html


def image_page(html):
    html = _review_page(html, task_routes=False)
    markers = {
        '<p id="loaded-context"': '<button id="pilot-return" type="button" hidden>返回取证工作台（提示回选本案）</button><p id="loaded-context"',
        'function renderLoadedContext(){': 'function renderLoadedContext(){updatePilotReturn();',
        'reopenFromUrl(typeof location===': """function pilotReturnCase(){
 return state&&context===el('case').value&&state.caseId===context&&state.runId===el('run').value&&/^SYN-[A-Za-z0-9_.-]{1,123}$/.test(context)?context:null;
}
function updatePilotReturn(){el('pilot-return').hidden=!pilotReturnCase();}
el('pilot-return').onclick=()=>{
 const c=pilotReturnCase();
 if(!c||busy||!reset())return;
 // Keep dirty/beforeunload protection intact; never write or claim cancellation.
 try{location.assign('/pilot?case='+encodeURIComponent(c));}
 catch(e){el('status').textContent='未能返回工作台；当前草稿仍在，请先复制保留。';}
};
reopenFromUrl(typeof location===""",
        'const originalRoutesAvailable=true;': 'const originalRoutesAvailable=false;',
        'const pilotSession=false;': 'const pilotSession=true;',
        '<section class="image-pane"': '<section hidden inert class="image-pane"',
        '<h1>图片文字核对 · 隔离候选</h1>': '<h1>合成试用 · 图片文字核对</h1><style>.review-grid{display:block}</style><p role="status">仅支持已有合法登记回执的人工结果导入与文字修订；不提供原图载入、定位、下载、模型任务或登记。文字核对不等于看过原件或确认真实性。<a href="/pilot">返回选案工作台</a>（离页会提示未保存草稿）</p>',
        '配置本地执行器后可显式发起公开第6页识别。': '此入口不提供模型任务。',
        '请求沿用现有本地身份机制，不代表生产身份认证。': '请求使用本试用工厂的服务器会话与逐案授权，仍未完成运行验收，不代表生产身份认证。',
        '任务来源记录仍须通过服务端原有绑定核验。': '任务来源记录在本试用入口明确拒绝。',
    }
    for marker, replacement in markers.items():
        if html.count(marker) != 1:
            raise ValueError('pilot image capability marker mismatch')
        html = html.replace(marker, replacement)
    return image_shell(html)


def _mount_pilot_image_pages(app):
    from pathlib import Path
    from fastapi.responses import HTMLResponse, Response
    root = Path(__file__).parents[1] / 'image_review'
    html = image_page((root / 'review.html').read_text(encoding='utf-8'))
    script = (root / 'preview.js').read_text(encoding='utf-8')
    headers = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
               'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY'}

    @app.get('/pilot/image-review', response_class=HTMLResponse)
    def page():
        return HTMLResponse(html, headers=headers)

    @app.get('/image-review-lab/preview.js')
    def preview_script():
        return Response(script, media_type='text/javascript', headers=headers)
