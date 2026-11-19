"""Offline directory/plan check only. Never authorizes or starts an application."""
import argparse
import json
from pathlib import Path
import stat

SAMPLE = 'synthetic-markers-v1'
GENERATOR_COMMIT = 'c10b2cd787f4b70d404893be9b9bfeb4f7de4361'
GENERATOR_PATH = 'tests_acceptance/synthetic-audio-review/make_wav.py'
MEMBERS = ('demo.db', 'materials/synthetic-markers.wav', 'materials/manifest.json')


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def member_path(root, member):
    # An exact allowlist, not normalization of caller-provided arbitrary paths.
    need(type(member) is str and member in MEMBERS, 'member not allowlisted')
    relative = Path(member)
    need(not relative.is_absolute() and '..' not in relative.parts, 'invalid member path')
    result = root / relative
    need(result.is_relative_to(root), 'member escapes root')
    return result


def plan(root, sample):
    need(sample == SAMPLE, 'sample not allowlisted')
    root = Path(root)
    need(root.is_absolute() and '..' not in root.parts, 'explicit absolute root required')
    # Metadata only along the explicitly supplied root, no recursive traversal.
    # No environment variables, checkout scan, mounted-directory scan or file reads.
    for part in reversed((root, *root.parents)):
        need(stat.S_ISDIR(part.lstat().st_mode), 'root and ancestors must be ordinary directories')
    need(root.name.startswith('mcis-report-audio-'), 'dedicated temporary root name required')
    need(next(root.iterdir(), None) is None, 'root must be empty')
    paths = {name: str(member_path(root, name)) for name in MEMBERS}
    return dict(status='empty-directory-plan-checked', startupAllowed=False,
                isolationVerified=False, filesCreated=False, databaseOpened=False,
                root=str(root), sample=sample, plannedMembers=paths,
                generator=dict(commit=GENERATOR_COMMIT, path=GENERATOR_PATH,
                               outputDirectory=str(root/'materials'), executed=False),
                proposedConfiguration=dict(seed_demo=False, host='127.0.0.1', port=8766,
                                           modelRuntime='disabled', applied=False),
                warning='Plan only; no startup approval. Caller must control a newly created stable directory. '
                        'Existing fixture digests are placeholders, not this WAV or registered evidence.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--sample', required=True)
    args = parser.parse_args()
    try:
        result = plan(args.root, args.sample)
    except (ValueError, OSError):
        # Do not print directory contents or filesystem exception details.
        parser.exit(2, 'Preflight failed: sample/root must meet the documented empty-directory allowlist.\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
