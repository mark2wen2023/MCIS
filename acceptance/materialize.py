"""Materialize the frozen isolated production allowlist (db90fdf).

Current mainline/c150548 removed _read_original_for_access from evidence_intake.
This tree is not copied into official service routes, storage or contracts.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRODUCT = "db90fdf73de7bd26ba75819f0102fc03d0789faf"
PIN_FIXTURE = "2048c60fd6650c6f2c99a76a16be463a3895655d"
SHA_A = "a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c"
SHA_B = "07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca"


def _sums(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split(None, 1)
        out[rel] = digest
    return out


def materialize(destination: Path, *, git_dir: Path, allowlist: Path | None = None) -> Path:
    allowlist = allowlist or (HERE / "ALLOWLIST_SHA256SUMS")
    expected = _sums(allowlist)
    if not expected:
        raise RuntimeError("empty allowlist")
    for rel, digest in expected.items():
        raw = subprocess.check_output(["git", "-C", str(git_dir), "show", f"{PRODUCT}:{rel}"])
        actual = hashlib.sha256(raw).hexdigest()
        if actual != digest:
            raise RuntimeError(f"allowlist SHA mismatch for {rel}: {actual} != {digest}")
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return destination


def require_sha(path: Path, expected: str, label: str) -> str:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(f"SHA mismatch for {label}: {actual} != {expected}")
    return actual
