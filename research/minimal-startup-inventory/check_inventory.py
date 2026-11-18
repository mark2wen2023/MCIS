"""Inventory-only research utility. Never imports application code or authorizes startup."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys

def inspect(root, manifest):
    result = {"inventory_matches": False, "startup_allowed": False,
              "reasons": ["EXECUTABLE_CLOSURE_NOT_PROVEN"], "files": []}
    if not isinstance(manifest, dict) or manifest.get("format") != 1:
        result["reasons"].append("INVALID_MANIFEST")
        return result
    entries = manifest.get("files")
    if not isinstance(entries, list):
        result["reasons"].append("INVALID_FILES")
        return result
    expected = {}
    for row in entries:
        if not isinstance(row, dict):
            result["reasons"].append("INVALID_ENTRY")
            return result
        p, h = row.get("path"), row.get("sha256")
        if (not isinstance(p, str) or not p or "\\" in p or
            PurePosixPath(p).is_absolute() or
            any(x in ("", ".", "..") for x in p.split("/")) or
            p in expected or not isinstance(h, str) or len(h) != 64 or
            any(c not in "0123456789abcdef" for c in h)):
            result["reasons"].append("INVALID_ENTRY")
            return result
        expected[p] = h
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        result["reasons"].append("INVALID_ROOT")
        return result
    found = {}
    def scan_error(error):
        raise error

    try:
        # Metadata inventory first: never read unexpected files or traverse links.
        for parent, dirs, names in os.walk(root, followlinks=False, onerror=scan_error):
            for name in dirs + names:
                path = Path(parent) / name
                mode = path.lstat().st_mode
                if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                    result["reasons"].append("UNSUPPORTED_MEMBER")
                    return result
                if stat.S_ISREG(mode):
                    found[path.relative_to(root).as_posix()] = path
    except OSError:
        result["reasons"].append("SCAN_INCOMPLETE")
        return result
    if set(found) != set(expected):
        result["reasons"].append("FILE_SET_INCOMPLETE_OR_EXTRA")
        return result
    for name in sorted(expected):
        digest = hashlib.sha256(found[name].read_bytes()).hexdigest()
        result["files"].append({"path": name, "sha256": digest})
        if digest != expected[name]:
            result["reasons"].append("CONTENT_MISMATCH")
    result["inventory_matches"] = len(result["reasons"]) == 1
    return result

def main():
    if len(sys.argv) != 3:
        print("Inventory only: supply controlled synthetic directory and manifest; no startup.")
        return 2
    try:
        result = inspect(sys.argv[1], json.loads(Path(sys.argv[2]).read_text()))
    except (OSError, ValueError):
        result = {"startup_allowed": False, "inventory_matches": False,
                  "reasons": ["INSPECTION_INCOMPLETE"]}
    print(json.dumps(result, indent=2))
    return 2  # Intentionally never provides an execution-success exit code.

if __name__ == "__main__":
    raise SystemExit(main())
