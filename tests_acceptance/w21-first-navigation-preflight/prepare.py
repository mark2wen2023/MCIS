#!/usr/bin/env python3
"""Prepare an isolated W21 replay runner without starting a browser."""
import argparse
import hashlib
import json
from pathlib import Path

MCIS = "2048c60fd6650c6f2c99a76a16be463a3895655d"
MCIS3D = "de9356a4616c0ef593ffff0ca81fd959ff24c1b3"
ORIGINAL = "dc3f64541c3572c10997118e006491f02bd87f7e200e943ae6ab3acc66ba27a4"
VARIANT = "26a36ec86bf072d61c47e8fa4ae8eee574bdf5cefc3bc47a0aca7c36600e81c1"
FILES = {
    "vessel-a.json": "a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c",
    "vessel-b.json": "07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca",
    "vessel-mismatch.json": "f785399311f5dd045eec6cc8a6a2105d95b376e9aa894342fd4da4f5985dc2f4",
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def prepare(source, mcis_fixtures, mcis3d_fixtures, out):
    original = source.read_bytes()
    if sha(original) != ORIGINAL:
        raise ValueError("runner bytes do not match the fixed mcis-3d revision")
    for name, expected in FILES.items():
        a = (mcis_fixtures / name).read_bytes()
        b = (mcis3d_fixtures / name).read_bytes()
        if a != b or sha(a) != expected:
            raise ValueError(f"{name}: fixed cross-repository bytes do not match")
    old = b"    runPw(session, ['open', args.url], runTmpDir);"
    new = b"    runPw(session, ['open', 'about:blank'], runTmpDir);"
    if original.count(old) != 1:
        raise ValueError("expected unique original navigation command")
    variant = original.replace(old, new, 1)
    if sha(variant) != VARIANT:
        raise ValueError("unexpected runner difference")
    out.mkdir(exist_ok=False)
    (out / "verify-first-app-navigation.mjs").write_bytes(variant)
    (out / "prepare-receipt.json").write_text(json.dumps({
        "sourceFixtureRevision": MCIS, "sourceRunnerRevision": MCIS3D,
        "verifiedFixtureSha256": FILES, "originalRunnerSha256": ORIGINAL,
        "derivedRunnerSha256": VARIANT, "browserExecuted": False,
        "scope": "exact input and runner preparation only; no browser or network result",
    }, indent=2) + "\n")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for option in ("source", "mcis-fixtures", "mcis3d-fixtures", "out"):
        p.add_argument("--" + option, type=Path, required=True)
    args = p.parse_args()
    try:
        prepare(args.source, args.mcis_fixtures, args.mcis3d_fixtures, args.out)
    except (OSError, ValueError) as e:
        p.exit(1, f"W21 preparation stopped: {e}\n")
