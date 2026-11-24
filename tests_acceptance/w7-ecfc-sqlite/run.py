"""Prepare the byte-pinned synthetic acceptance in an isolated temporary directory."""
from argparse import ArgumentParser
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


def main():
    cli = ArgumentParser(description=__doc__)
    modes = cli.add_mutually_exclusive_group()
    modes.add_argument("--repository", type=Path, help="Local MCIS clone with both pinned commits")
    modes.add_argument("--source-dir", type=Path, help="Previously exported source files matching SOURCES")
    args = cli.parse_args()
    base = Path(__file__).resolve().parent
    repo = args.repository or base.parents[1]
    with TemporaryDirectory(prefix="mcis-w7-ecfc-test-") as directory:
        run = Path(directory)
        covered = set()
        for blob, ref, name in (line.split() for line in (base / "SOURCES").read_text().splitlines()):
            item = Path(name)
            if item.is_absolute() or ".." in item.parts or item in covered:
                cli.error(f"Invalid or duplicate pinned path: {name}")
            if not all(re.fullmatch(r"[0-9a-f]{40}", x) for x in (blob, ref)):
                cli.error(f"Invalid Git pin for {name}")
            covered.add(item)
            if args.source_dir:
                data = (args.source_dir / item).read_bytes()
            else:
                proc = subprocess.run(
                    ["git", "-C", str(repo), "show", f"{ref}:{name}"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
                )
                if proc.returncode:
                    cli.error(f"Local repository is missing {ref}:{name}; fetch the two pinned refs first.")
                data = proc.stdout
            git_blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            if git_blob != blob:
                cli.error(f"Source Git blob mismatch: {name}")
            dest = run / "source" / item
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        for name in ("check.py", "SOURCES"):
            shutil.copyfile(base / name, run / name)
        return subprocess.run([sys.executable, "-I", "-B", str(run / "check.py")], cwd=run).returncode


if __name__ == "__main__":
    raise SystemExit(main())
