"""Generated document and actual JS -> existing strict CLI protocol checks."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
sys.path.insert(0, str(Path(__file__).parent))
import render_browser_review as b
import export_review as e
from test_render_review_independent import Parser

ROOT = Path(__file__).parent


def inputs():
    c, cs = e.load(ROOT / 'jiangxin9-provisional.json')
    p, ps = e.load(ROOT / 'jiangxin9-real-predictions.json')
    return c, cs, p, ps


def test_document_binding_content_csp_and_immutable_inputs():
    args = inputs()
    before = copy.deepcopy(args)
    raw = b.render_browser(*args).decode()
    assert args == before
    parser = Parser(); parser.feed(raw)
    assert len([t for t, _ in parser.tags if t == 'script']) == 2
    assert not any(t in {'iframe', 'object', 'img', 'link', 'form'} for t, _ in parser.tags)
    assert not any(k.startswith('on') or k in {'src', 'srcdoc'} for _, attrs in parser.tags for k in attrs)
    script = (ROOT / 'browser_review.js').read_bytes()
    digest = base64.b64encode(hashlib.sha256(script).digest()).decode()
    csp = next(a['content'] for t, a in parser.tags if t == 'meta' and a.get('http-equiv') == 'Content-Security-Policy')
    assert "script-src 'sha256-" + digest + "'" in csp
    assert "connect-src 'none'" in csp and "default-src 'none'" in csp
    for row in args[2]['predictions']:
        assert e.esc(row['rationale']) in raw and e.esc(row['label']) in raw
    for row in args[0]['items']:
        assert e.esc(row['sourceText']) in raw and e.esc(row['citation']['quote']) in raw
    assert args[1] in raw and args[3] in raw
    assert '未勾选不表示核实通过' in raw and '无作者认证' in raw


def test_downloaded_json_passes_strict_cli_roundtrip(tmp_path):
    args = inputs()
    page = tmp_path / 'review.html'; worksheet = tmp_path / 'notes.json'
    page.write_bytes(b.render_browser(*args))
    run = subprocess.run(['node', str(ROOT / 'browser-review.test.cjs'), str(page), str(worksheet)], capture_output=True, text=True, timeout=15)
    assert run.returncode == 0, run.stdout + run.stderr
    notes, digest = e.load(worksheet)
    e.validate_worksheet(notes, e.template(*args))
    output = e.export(*args, notes, digest).decode()
    assert e.esc(notes['items'][0]['note']) in output
    assert digest in output and args[1] in output and args[3] in output
    assert '<script>alert(1)</script>' not in output


def test_injected_model_text_stays_literal():
    args = inputs()
    evil = '</script><script>alert(1)</script><img src="https://invalid">'
    args[2]['predictions'][0]['rationale'] = evil
    raw = b.render_browser(*args).decode()
    assert e.esc(evil) in raw
    parser = Parser(); parser.feed(raw)
    assert len([t for t, _ in parser.tags if t == 'script']) == 2
    assert not any(t == 'img' for t, _ in parser.tags)


def test_generator_cli_rejects_overwrite_and_bad_input(tmp_path):
    out = tmp_path / 'page.html'
    cmd = [sys.executable, str(ROOT / 'render_browser_review.py'), '--corpus', str(ROOT / 'jiangxin9-provisional.json'), '--predictions', str(ROOT / 'jiangxin9-real-predictions.json'), '--output', str(out)]
    assert subprocess.run(cmd, capture_output=True).returncode == 0
    content = out.read_bytes()
    assert subprocess.run(cmd, capture_output=True).returncode == 2
    assert out.read_bytes() == content
    bad = tmp_path / 'bad.json'; bad.write_text('{"private":"NO_ECHO"}')
    cmd[3] = str(bad); cmd[-1] = str(tmp_path / 'absent')
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 2 and 'NO_ECHO' not in result.stdout + result.stderr
    assert not (tmp_path / 'absent').exists()
