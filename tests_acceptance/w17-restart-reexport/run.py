"""Verify the exact pinned source, then run the portable synthetic acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from tempfile import TemporaryDirectory

BASE = "d40e3b5fd2e208af84c84d6faf61095d0a0a89fb"
HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path,
                        help="read-only source tree exported from " + BASE)
    options = parser.parse_args()
    source = options.source.resolve(strict=True)
    manifest = json.loads((HERE / "pins.json").read_text())
    pins = manifest["gitBlobPins"]
    if manifest["commit"] != BASE or len(pins) != 190:
        parser.error("unexpected acceptance pin manifest")
    if not sys.flags.isolated or not sys.dont_write_bytecode or sys.flags.optimize:
        parser.error("invoke as python -I -B (assertions required)")
    with TemporaryDirectory(prefix="w17-pinned-product-") as work:
        work = Path(work)
        for name, expected in pins.items():
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or path.parts[0] not in ("service", "contracts"):
                parser.error(f"unrecognized pinned path: {name}")
            try:
                item = (source / path).resolve(strict=True)
                if item != source / path or not item.is_file():
                    parser.error(f"pinned path is not a plain source file: {name}")
                data = item.read_bytes()
            except OSError:
                parser.error(f"missing/unreadable pinned file: {name}")
            actual = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            if actual != expected:
                parser.error(f"Git blob pin mismatch: {name} expected {expected}, got {actual}")
            target = work / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        print(f"Verified {len(pins)} {BASE} source blob pins", file=sys.stderr)
        env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "MCIS_"))}
        env.update(PYTHONPATH=str(work / "service"), PYTHONDONTWRITEBYTECODE="1",
                   PYTHONNOUSERSITE="1")
        return subprocess.run([sys.executable, "-B", "-s", str(HERE / "check.py")],
                              cwd=work, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
