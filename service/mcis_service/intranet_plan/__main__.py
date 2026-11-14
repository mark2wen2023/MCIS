"""Bounded offline JSON transport. No filesystem persistence or network access."""
import json
import sys
from . import build_plan


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


def main():
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise ValueError()
        document = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=unique,
                              parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        result = build_plan(document)
    except (ValueError, RecursionError, UnicodeError):
        result = build_plan(None)
    sys.stdout.write(json.dumps(result, ensure_ascii=True) + '\n')
    return 4 if result['status'] == 'validation_failed' else 0


if __name__ == '__main__':
    sys.exit(main())
