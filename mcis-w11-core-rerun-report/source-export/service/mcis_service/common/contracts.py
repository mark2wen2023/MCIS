"""运行时按 contracts/schemas/*.schema.json 校验进出数据（契约即真相）。"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from ..config import PROJECT_ROOT
from .context import problem

SCHEMA_DIR = PROJECT_ROOT / "contracts" / "schemas"
BASE = "https://mcis.local/contracts/v1/"


@lru_cache(maxsize=1)
def registry() -> Registry:
    resources = []
    for p in Path(SCHEMA_DIR).glob("*.schema.json"):
        doc = json.loads(p.read_text(encoding="utf-8"))
        resources.append((doc["$id"], Resource.from_contents(doc)))
    return Registry().with_resources(resources)


@lru_cache(maxsize=64)
def validator(ref: str) -> Draft202012Validator:
    """ref 形如 'case' 或 'interview#/$defs/statement'。"""
    name, _, frag = ref.partition("#")
    uri = BASE + name + ".schema.json"
    schema = {"$ref": uri + ("#" + frag if frag else "")}
    return Draft202012Validator(schema, registry=registry(), format_checker=FormatChecker())


def errors(ref: str, doc: Any) -> list[str]:
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}" for e in validator(ref).iter_errors(doc)]


def validate(ref: str, doc: Any) -> None:
    errs = errors(ref, doc)
    if errs:
        raise problem(422, "CONTRACT_VIOLATION", f"不符合契约 {ref}", errs[:20])
