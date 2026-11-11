#!/usr/bin/env python3
"""Validate one or more COLREG contract JSON documents against colreg.schema.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "contracts" / "schemas"
BASE = "https://mcis.local/contracts/v1/"


def registry() -> Registry:
    resources = []
    for p in SCHEMA_DIR.glob("*.schema.json"):
        doc = json.loads(p.read_text(encoding="utf-8"))
        resources.append((doc["$id"], Resource.from_contents(doc)))
    return Registry().with_resources(resources)


def validate(doc: dict) -> list[str]:
    schema = {"$ref": BASE + "colreg.schema.json"}
    v = Draft202012Validator(schema, registry=registry(), format_checker=FormatChecker())
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}" for e in v.iter_errors(doc)]


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: validate_colreg_schema.py <file.json> [file.json...]", file=sys.stderr)
        return 2
    failed = 0
    for path in argv[1:]:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        errs = validate(doc)
        if errs:
            failed += 1
            print(f"FAIL {path}")
            for e in errs:
                print(" ", e)
        else:
            print(f"OK {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
