"""Explicit local-file adapter for the offline research preview. No network."""
import argparse
import json
import os
import stat
import sys
from gate import Invalid, Source, exact, pairs
from render_preview import render


def read_regular(path, limit):
    # Nonblocking open prevents FIFO input from hanging before fstat.
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise Invalid('INPUT_NOT_REGULAR')
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise Invalid('INPUT_BUDGET')
    return data


def build(candidates_path, sources_path):
    try:
        body = json.loads(read_regular(sources_path, 4 * 1024 * 1024).decode('utf-8'),
                          object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Invalid('INVALID_JSON')))
        exact(body, 'sources')
        rows = body['sources']
        if type(rows) is not list or len(rows) > 16:
            raise Invalid('SOURCE_BUDGET')
        sources = []
        for row in rows:
            exact(row, 'sourceId version sourceType locator content')
            sources.append(Source(row['sourceId'], row['version'], row['sourceType'], row['locator'], row['content']))
        return render(read_regular(candidates_path, 65536), sources).encode('utf-8')
    except (UnicodeError, ValueError, RecursionError, TypeError) as error:
        if isinstance(error, Invalid):
            raise
        raise Invalid('INVALID_SOURCE_MANIFEST') from None


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local research preview only; source labels are operator assertions, not authentication.')
    parser.add_argument('--candidates', required=True)
    parser.add_argument('--sources', required=True)
    parser.add_argument('--output', required=True, help='New HTML file only; existing paths are never overwritten')
    args = parser.parse_args(argv)
    try:
        data = build(args.candidates, args.sources)
        # Exclusive creation protects existing files and symlinks; validation precedes creation.
        with open(args.output, 'xb') as stream:
            stream.write(data)
        return 0
    except Invalid as error:
        print('Preview rejected: ' + str(error), file=sys.stderr)
        return 4
    except OSError:
        # Do not echo paths or payloads into logs. An I/O failure may leave a partial output.
        print('Preview I/O failure; output not verified. Use a new output path after checking storage.', file=sys.stderr)
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
