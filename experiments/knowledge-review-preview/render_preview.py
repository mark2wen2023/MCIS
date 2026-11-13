"""Offline read-only review view. Input always passes the provenance gate."""
from html import escape
from gate import gate


def render(raw, sources, known=()):
    preview = gate(raw, sources, known)
    esc = lambda value: escape(str(value), quote=True)
    cards = []
    for number, candidate in enumerate(preview['candidates'], 1):
        citations = []
        for citation in candidate['citations']:
            citations.append(
                '<li><dl><dt>来源 / 版本</dt><dd>' + esc(citation['sourceId']) + ' / ' +
                esc(citation['version']) + '</dd><dt>位置（原文字符，左闭右开）</dt><dd>' +
                esc(citation['start']) + '–' + esc(citation['end']) + '</dd><dt>材料位置</dt><dd>' +
                esc(citation['locator']) + '</dd><dt>文本 SHA-256</dt><dd class="hash">' +
                esc(citation['textSha256']) + '</dd></dl><blockquote>' + esc(citation['quote']) +
                '</blockquote></li>')
        cards.append('<article aria-labelledby="candidate-' + str(number) + '"><h2 id="candidate-' +
                     str(number) + '">' + esc(candidate['title']) + '</h2><p class="badge">' +
                     ('含虚构材料 · ' if candidate['synthetic'] else '公开材料 · ') +
                     '未核实 · 待人工审核</p><p>类别：' + esc(candidate['kind']) + '</p><p class="claim">' +
                     esc(candidate['claim']) + '</p><h3>引用原文（并非事实认定）</h3><ol>' +
                     ''.join(citations) + '</ol><p class="hash">候选指纹：' +
                     esc(candidate['fingerprint']) + '</p></article>')
    duplicate_rows = ''.join('<li>输入序号 ' + str(d['index'] + 1) + '：<code>' +
                             esc(d['fingerprint']) + '</code></li>' for d in preview['duplicates'])
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>MCIS 知识候选 · 离线审阅</title><style>
body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#142b3b;background:#f4f7f9;line-height:1.7}
article{background:white;border:1px solid #bccbd3;border-radius:12px;padding:1.5rem;margin:1.5rem 0}
h1,h2,h3{line-height:1.3}.notice,.badge{background:#fff0bd;padding:.75rem;color:#493600}
.hash,code,dd{overflow-wrap:anywhere}blockquote{border-left:4px solid #647f90;margin:1rem 0;padding-left:1rem;white-space:pre-wrap}.claim{white-space:pre-wrap}dt{font-weight:bold}dd{margin-left:0}
@media print{body{background:white}article{break-inside:avoid}}
</style></head><body><main><h1>知识候选 · 离线人工审阅</h1>
<p class="notice">研究原型，只读预览。未保存、未发布、未调用模型。引用匹配不代表主张成立；来源、使用权和结论均须人工审核。</p>''' + (
        ''.join(cards) if cards else '<p>没有新增候选。</p>') + '<section><h2>完全重复条目</h2><p>' + str(
        len(preview['duplicates'])) + ' 条被跳过；这不是语义去重。</p><ul>' + duplicate_rows + \
        '</ul></section></main></body></html>'
