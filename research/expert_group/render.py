"""Inert side-by-side research output: differences are not consensus or facts."""
import html
import json


def esc(value):
    return html.escape(str(value), quote=True)


def render(packet, result):
    if result.get('factActivated') is not False or result.get('consensusComputed') is not False:
        raise ValueError('result boundary')
    roles = result['roles']
    if len(roles) != 2 or [r['roleId'] for r in roles] != ['source_attribution', 'uncertainty_boundary']:
        raise ValueError('roles')
    chunks = ['<!doctype html><html lang="zh"><meta charset="utf-8">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; connect-src \'none\'; form-action \'none\'; base-uri \'none\'; frame-src \'none\'">',
        '<meta name="referrer" content="no-referrer"><title>公开报告双角色审读</title>',
        '<style>body{font:16px sans-serif;max-width:1100px;margin:2em auto;padding:1em}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{width:100%;table-layout:fixed;border-collapse:collapse}td,th{border:1px solid #aaa;padding:1em;vertical-align:top;overflow-wrap:anywhere}.notice{padding:1em;background:#fff0ce}</style>',
        '<h1>公开报告双角色审读 · 未核实研究记录</h1>',
        '<p class="notice">两种模型分析视角，不是真人专家或独立专家共识。引用匹配不等于语义或事实核定；不会写入案件。</p>',
        '<p class="notice">' + ('脚本模拟提供方 · 未进行真实模型能力验收' if result['transportMocked'] else '真实提供方模式声明 · 底层模型身份及意见正确性未认证') + '</p>',
        '<p>运行状态：' + esc(result['status']) + '；运行ID：' + esc(result['runId']) + '</p>',
        '<p class="notice">本页仅为运行内容。导出是否完整须使用 --verify-dir 核对 completion.json 与三个文件摘要；单独页面不能证明导出成功。</p>',
        '<p>来源包SHA256：' + esc(result['packetSha256']) + '</p>']
    for item in packet['items']:
        chunks += ['<section><h2>' + esc(item['itemId']) + ' · 待审主张</h2><p>' + esc(item['claim']) + '</p>',
                   '<details><summary>受控公开原文（不自动访问原PDF）</summary><pre>' + esc(item['sourceText']) + '</pre></details>',
                   '<p>来源声明：' + esc(json.dumps(item['sourceLocator'], ensure_ascii=False)) + '</p>',
                   '<p>原文SHA256：' + esc(item['sourceSha256']) + '</p><table><thead><tr><th>来源与对象归属视角</th><th>限定词与推断边界视角</th></tr></thead><tbody><tr>']
        found = []
        for role in roles:
            rows = [r for r in role.get('reviews', []) if r['itemId'] == item['itemId']]
            row = rows[0] if len(rows) == 1 and role['status'] == 'completed_unverified' else None
            found.append(row)
            chunks += ['<td><p>子任务：' + esc(role.get('runId', 'not_started')) + ' · ' + esc(role['status']) + '</p>']
            if row:
                chunks += ['<p>建议标签：' + esc(row['label']) + '</p><p>解释：' + esc(row['rationale']) + '</p>',
                           '<p>不确定性：' + esc(row['uncertainty']) + '</p><pre>引用：' + esc(row['quote']) + '</pre>']
            else: chunks += ['<p>本角色没有已接受的完整意见，不补造答案。</p>']
            chunks += ['</td>']
        if all(found):
            same = found[0]['label'] == found[1]['label']
            note = '标签相同；不是共识或事实确认，仍须逐项审读解释与不确定性。' if same else '建议标签不同；并列保留分歧，不投票或自动裁决。'
        else: note = '意见不完整，不能判定一致或分歧。'
        chunks += ['</tr></tbody></table><p>' + note + '</p></section>']
    chunks += ['<p>本地回执仅记录执行轨迹及摘要，不认证作者、来源PDF或模型身份。</p></html>']
    raw = ''.join(chunks).encode('utf-8')
    if len(raw) > 8 * 1024 * 1024: raise ValueError('output budget')
    return raw
