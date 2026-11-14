"""Generate an offline review page with explicit v1 worksheet JSON download."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys

from export_review import template, write_new
from render_review import CSP, MAX_OUTPUT_BYTES, esc, render
from evaluate import load


def render_browser(corpus, corpus_sha, predictions, prediction_sha):
    worksheet = template(corpus, corpus_sha, predictions, prediction_sha)
    base = render(corpus, corpus_sha, predictions).decode('utf-8')
    script = Path(__file__).with_name('browser_review.js').read_text(encoding='utf-8')
    digest = base64.b64encode(hashlib.sha256(script.encode('utf-8')).digest()).decode('ascii')
    policy = CSP + "; script-src 'sha256-" + digest + "'; object-src 'none'"
    base = base.replace(esc(CSP), esc(policy), 1)
    # No untrusted text can terminate the inert JSON script element.
    data = json.dumps(worksheet, ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    panel = ('<section aria-label="本地导出"><h2>显式下载研究备注</h2>'
             '<p>勾选仅表示待核实；未勾选不表示核实通过、同意或无问题。标记项必须填写原因。备注最多 4000 个 Unicode 字符。</p>'
             '<p>点击下载兼容 export_review.py 的 JSON，再用 CLI 生成含原文、模型标签、完整解释及来源的 HTML 快照。'
             'JSON 仅含备注和双摘要绑定，不含原报告；请保留原语料和模型输出文件。无作者认证，不是案件事实。摘要不是签名。</p>'
             '<p>模型输出文件 SHA256：<code>' + esc(prediction_sha) + '</code></p>'
             '<button id="download-notes" type="button">下载当前研究备注 JSON</button>'
             '<p id="download-status" role="status" aria-live="polite">尚未导出。仅点击按钮才请求本地下载；无自动保存或上传。</p>'
             '<noscript>浏览器未启用脚本，无法下载备注。请使用原有 CLI 备注模板流程。</noscript></section>')
    base = base.replace('<body>', '<body>' + panel, 1)
    output = base.replace('</body>', '<script id="worksheet-template" type="application/json">' + data + '</script><script>' + script + '</script></body>').encode('utf-8')
    if len(output) > MAX_OUTPUT_BYTES:
        raise ValueError('budget')
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--corpus', required=True)
    parser.add_argument('--predictions', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    corpus, corpus_sha = load(args.corpus)
    predictions, prediction_sha = load(args.predictions)
    write_new(args.output, render_browser(corpus, corpus_sha, predictions, prediction_sha))
    print(json.dumps({'ok': True, 'modelCalled': False, 'factActivated': False, 'reviewerAuthenticated': False}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('{"ok":false,"errorCode":"BROWSER_REVIEW_REJECTED"}', file=sys.stderr)
        sys.exit(2)
