"""在全新目录创建独立 Python 环境，默认从本地 wheel 仓安装。"""
import argparse
from pathlib import Path
import platform
import subprocess
import sys
import venv

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--venv", required=True, type=Path)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--wheelhouse", type=Path)
    source.add_argument("--online", action="store_true")
    p.add_argument("--lock", type=Path, help="指定平台的带哈希锁文件")
    args = p.parse_args()
    if args.lock is None:
        key=(sys.platform,platform.machine(),sys.version_info[:2])
        name={("darwin","arm64",(3,13)):"macos-arm64-cp313.lock",("linux","x86_64",(3,13)):"linux-amd64-cp313.lock"}.get(key)
        if not name:
            p.error("此平台尚无已验证的默认锁；可显式指定 --lock")
        args.lock=Path(__file__).resolve().parents[1]/"references"/name
    if args.venv.exists() or not args.lock.is_file() or (args.wheelhouse and not args.wheelhouse.is_dir()):
        p.error("请提供新环境目录、有效锁文件和有效软件包目录")
    venv.create(args.venv, with_pip=True)
    python = str(args.venv.resolve()/"bin/python")
    options = ["--no-index","--find-links",str(args.wheelhouse.resolve())] if args.wheelhouse else []
    subprocess.run([python,"-m","pip","--disable-pip-version-check","install","--only-binary=:all:",*options,"-r",str(args.lock)], check=True)
    subprocess.run([python,"-m","pip","check"], check=True)
    subprocess.run([python,str(Path(__file__).with_name("preflight.py"))], check=True)
