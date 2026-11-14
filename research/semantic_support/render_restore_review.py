"""Opt-in local worksheet restore on top of the unchanged browser export page."""
import argparse
import base64
import hashlib
from pathlib import Path
import sys
from evaluate import load
from export_review import write_new
from render_review import esc, MAX_OUTPUT_BYTES
from render_browser_review import render_browser


def render_restore(corpus, corpus_sha, predictions, prediction_sha):
    base = render_browser(corpus, corpus_sha, predictions, prediction_sha).decode('utf-8')
    script = Path(__file__).with_name('browser_import.js').read_text(encoding='utf-8')
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    base = base.replace('; object-src', " " + esc("'sha256-" + digest + "'") + '; object-src', 1)
    panel = ('<section aria-label="本地恢复"><h2>显式导入本地备注</h2>'
             '<p>仅恢复与本页语料、模型输出文件双摘要完全一致的备注 JSON。选择文件不会立即覆盖编辑；校验后需确认替换。'
             '文件内容和作者仍未认证，摘要不是真实性证明。无自动上传或事实确认。</p>'
             '<label>选择备注 JSON（最多 4 MiB）<input id="import-file" type="file" accept=".json,application/json"></label>'
             '<button id="apply-import" type="button" disabled>确认替换全部当前备注</button> '
             '<button id="cancel-import" type="button">取消导入或清空</button> '
             '<button id="clear-notes" type="button">清空本页备注…</button> '
             '<button id="confirm-clear" type="button" hidden>确认清空全部备注和标记</button>'
             '<p id="import-status" role="status" aria-live="polite">尚未选择文件。当前编辑不会自动保存。</p></section>')
    output = base.replace('<body>', '<body>' + panel, 1).replace('</body>', '<script>' + script + '</script></body>').encode()
    if len(output) > MAX_OUTPUT_BYTES:
        raise ValueError('budget')
    return output


def main():
    parser = argparse.ArgumentParser()
    for name in ('corpus', 'predictions', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    c, cs = load(args.corpus); p, ps = load(args.predictions)
    write_new(args.output, render_restore(c, cs, p, ps))
    print('{"ok":true,"modelCalled":false,"factActivated":false}')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('{"ok":false,"errorCode":"RESTORE_REVIEW_REJECTED"}', file=sys.stderr)
        sys.exit(2)
