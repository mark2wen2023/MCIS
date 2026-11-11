"""W6 独立验收：真实进程 + 无头 Chrome。

- 后端用正式入口 `python -m mcis_service`，临时端口 + 临时数据目录（自动播种），不碰 8765 与 service/data。
- 前端 vite build 到 /tmp，再用 vite preview 起临时端口（代理到临时后端）。
- 检查监听地址（ss），抓 DOM（--dump-dom），重拍 1440/1920 × 虚构/公开报告 截图。
测完关掉自己起的进程，删除临时目录。
"""
from __future__ import annotations

import os
import re
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

from conftest import HAILI, ROOT

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "screenshots"
# I1 写入 runs/<时间戳>/，不覆盖 screenshots/ 下的基线截图
from datetime import datetime
I1_RUN_TS = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
I1_RUN_DIR = SHOTS / "runs" / I1_RUN_TS
CHROME = shutil.which("google-chrome") or shutil.which("chromium")
pytestmark = pytest.mark.skipif(CHROME is None, reason="无无头浏览器")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait(url: str, timeout: float = 60) -> None:
    t = time.time()
    while time.time() - t < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except Exception:
            time.sleep(0.4)
    raise RuntimeError(f"等待超时：{url}")


@pytest.fixture(scope="module")
def stack():
    tmp = Path(tempfile.mkdtemp(prefix="w6-e2e-"))
    bport, fport = _free_port(), _free_port()
    env = dict(os.environ, MCIS_DATA_DIR=str(tmp / "data"), MCIS_PORT=str(bport), MCIS_SEED_DEMO="1",
               PYTHONDONTWRITEBYTECODE="1", MCIS_API=f"http://127.0.0.1:{bport}")
    procs = []
    log = open(tmp / "backend.log", "w")
    procs.append(subprocess.Popen([str(ROOT / "service/.venv/bin/python"), "-m", "mcis_service"], cwd=ROOT / "service",
                                  env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True))
    _wait(f"http://127.0.0.1:{bport}/api/v1/health")
    dist = tmp / "dist"
    subprocess.run(["npx", "vite", "build", "--outDir", str(dist), "--emptyOutDir", "--logLevel", "error"],
                   cwd=ROOT / "web", env=env, check=True, capture_output=True, timeout=300)
    flog = open(tmp / "frontend.log", "w")
    procs.append(subprocess.Popen(["npx", "vite", "preview", "--outDir", str(dist), "--host", "127.0.0.1", "--port", str(fport),
                                   "--strictPort"], cwd=ROOT / "web", env=env, stdout=flog, stderr=subprocess.STDOUT,
                                  start_new_session=True))
    _wait(f"http://127.0.0.1:{fport}/")
    try:
        yield {"bport": bport, "fport": fport, "base": f"http://127.0.0.1:{fport}", "tmp": tmp, "pids": [p.pid for p in procs]}
    finally:
        for p in procs:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for p in procs:
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
        log.close(); flog.close()
        shutil.rmtree(tmp, ignore_errors=True)


def _chrome(args: list[str], timeout=90) -> str:
    # 注：本机 headless Chrome 配 --user-data-dir 全新目录会卡死在首启，故用默认临时 profile
    r = subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=1", "--virtual-time-budget=15000", *args],
                       capture_output=True, text=True, timeout=timeout)
    return r.stdout


@pytest.fixture(scope="module")
def doms(stack):
    base = stack["base"]
    return {"fict": _chrome(["--window-size=1920,1080", "--dump-dom", f"{base}/#/colreg"]),
            "pub": _chrome(["--window-size=1920,1080", "--dump-dom", f"{base}/#/colreg?case={HAILI}"])}


def _listen_addrs(port: int) -> list[str]:
    out = subprocess.run(["ss", "-Hltn", f"sport = :{port}"], capture_output=True, text=True).stdout
    return [ln.split()[3] for ln in out.strip().splitlines() if ln.strip()]


def test_G1_backend_listens_loopback_only(stack):
    addrs = _listen_addrs(stack["bport"])
    assert addrs, "未监听"
    assert all(a.startswith("127.0.0.1:") for a in addrs), addrs


def test_G2_frontend_listens_loopback_only(stack):
    addrs = _listen_addrs(stack["fport"])
    assert addrs and all(a.startswith("127.0.0.1:") for a in addrs), addrs


def test_G3_backend_not_reachable_on_other_interfaces(stack):
    ips = [ip for ip in subprocess.run(["hostname", "-I"], capture_output=True, text=True).stdout.split() if not ip.startswith("127.")]
    for ip in ips[:3]:
        with socket.socket(socket.AF_INET6 if ":" in ip else socket.AF_INET) as s:
            s.settimeout(1)
            assert s.connect_ex((ip, stack["bport"])) != 0, f"{ip} 上可连接"


def test_G4_existing_8765_untouched_and_loopback():
    addrs = _listen_addrs(8765)
    assert all(a.startswith("127.0.0.1:") for a in addrs), addrs


@pytest.mark.parametrize("mode", ["fict", "pub"])
def test_H1_page_renders_disclaimer(doms, mode):
    d = doms[mode]
    assert 'data-testid="colreg-page"' in d, "页面未渲染（可能后端未连通）"
    m = re.search(r'data-testid="colreg-disclaimer"[^>]*>([^<]*)<', d)
    assert m and "不作责任认定" in m.group(1)


@pytest.mark.parametrize("mode", ["fict", "pub"])
def test_H2_switcher_has_both_modes(doms, mode):
    m = re.search(r'data-testid="case-switcher".*?</span></span>', doms[mode], re.S)
    assert m, "无切换控件"
    assert "Lily / Mary" in m.group(0) and "海力5" in m.group(0)
    assert m.group(0).count('class="on"') == 1


def test_H3_mode_tags(doms):
    assert "示例数据（虚构）" in doms["fict"] and "真实案例（公开报告）" not in doms["fict"]
    assert "真实案例（公开报告）" in doms["pub"] and "示例数据（虚构）" not in doms["pub"]


def test_H4_public_mode_bands_and_tags(doms):
    d = doms["pub"]
    assert len(re.findall(r'data-band="HL-B\d"', d)) == 4
    assert d.count("【直接") >= 4 and "标注【直接】/【推算】" in d
    assert "doubt-mark" in d and "失控" in d and "紧迫局面" in d


def test_H5_public_mode_needsreview_and_notassessable(doms):
    d = doms["pub"]
    assert "需研判" in d and "缺证据" in d
    assert 'st-pur">? 需研判' in d and 'st-info">∅ 缺证据' in d


def test_H6_fict_mode_bands_and_evidence(doms):
    d = doms["fict"]
    assert len(re.findall(r'data-band="B\d"', d)) == 5
    assert re.search(r'data-testid="evidence-links".*?EV-\d{3}', d, re.S)


def test_H7_service_addr_from_mcis_api(doms, stack):
    """页头地址来自构建时注入的 __MCIS_API__ / MCIS_API，不得写死 8765。"""
    d = doms["fict"]
    assert re.search(r'data-testid="service-addr"[^>]*>LIVE · 127\.0\.0\.1:' + str(stack["bport"]), d), d[d.find("LIVE") : d.find("LIVE")+80] if "LIVE" in d else "无 LIVE"
    if stack["bport"] != 8765:
        assert f'LIVE · 127.0.0.1:8765' not in d


@pytest.mark.parametrize("mode", ["fict", "pub"])
def test_H8_prototype_layout_present(doms, mode):
    """原型补齐：DCPA/TCPA 曲线、分船责任/实际操纵行、分船判定列、应采取 vs 实际表、章节草稿按钮。"""
    d = doms[mode]
    assert 'data-testid="dcpa-chart"' in d
    assert 'data-testid="colreg-pivot"' in d
    assert 'data-testid="colreg-actions"' in d
    assert 'data-testid="btn-draft"' in d
    assert "生成规则分析章节草稿" in d
    assert "应采取" in d and "实际" in d
    assert 'data-testid="row-resp-' in d
    assert 'data-testid="row-act-' in d
    assert "DCPA" in d and "TCPA" in d


SHOT_SET = [("1440", 1440, 900, "fict"), ("1440", 1440, 900, "pub"), ("1920", 1920, 1080, "fict"), ("1920", 1920, 1080, "pub")]


@pytest.mark.parametrize("tag,w,h,mode", SHOT_SET)
def test_I1_screenshots(stack, tag, w, h, mode):
    I1_RUN_DIR.mkdir(parents=True, exist_ok=True)
    out = I1_RUN_DIR / f"w6-colreg-{'haili5' if mode == 'pub' else 'fict'}-{tag}.png"
    url = f"{stack['base']}/#/colreg" + (f"?case={HAILI}" if mode == "pub" else "")
    _chrome([f"--window-size={w},{h}", f"--screenshot={out}", url])
    assert out.exists() and out.stat().st_size > 30_000, f"截图失败或空白：{out}"
    from struct import unpack
    with open(out, "rb") as f:
        head = f.read(24)
    assert unpack(">II", head[16:24]) == (w, h)
    # 不得覆盖基线
    baseline = SHOTS / out.name
    if baseline.exists():
        assert baseline.resolve() != out.resolve()
