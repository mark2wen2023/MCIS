import base64
import hashlib
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import render_restore_review as r
from test_browser_review import inputs
from test_render_review_independent import Parser
ROOT = Path(__file__).parent


def test_generated_restore_script_and_csp(tmp_path):
    args = inputs(); raw = r.render_restore(*args)
    page = tmp_path / 'restore.html'; page.write_bytes(raw)
    result = subprocess.run(['node', str(ROOT / 'browser-import.test.cjs'), str(page)], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    parser = Parser(); parser.feed(raw.decode())
    csp = next(a['content'] for t, a in parser.tags if t == 'meta' and a.get('http-equiv') == 'Content-Security-Policy')
    for name in ('browser_review.js', 'browser_import.js'):
        digest = base64.b64encode(hashlib.sha256((ROOT/name).read_bytes()).digest()).decode()
        assert "'sha256-"+digest+"'" in csp
    assert "connect-src 'none'" in csp and len([t for t,a in parser.tags if t=='script'])==3
    assert '确认替换' in raw.decode() and '未认证' in raw.decode()


def test_restore_cli_no_overwrite(tmp_path):
    out = tmp_path/'page.html'
    cmd = [sys.executable,str(ROOT/'render_restore_review.py'),'--corpus',str(ROOT/'jiangxin9-provisional.json'),'--predictions',str(ROOT/'jiangxin9-real-predictions.json'),'--output',str(out)]
    assert subprocess.run(cmd,capture_output=True).returncode==0
    original=out.read_bytes()
    assert subprocess.run(cmd,capture_output=True).returncode==2
    assert out.read_bytes()==original
