"""Standard-library handmade temporary directories only; ordinary path validation.
No permission denial, writes-rejected, application, database or service probes.
"""
from pathlib import Path
import runpy
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
module = runpy.run_path(str(ROOT/'tools/report_audio_preflight/check.py'))
plan, member_path = module['plan'], module['member_path']

def rejected(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError('ordinary invalid input unexpectedly accepted')

# Explicit /tmp avoids environment-based temporary-root selection.
with TemporaryDirectory(prefix='mcis-report-audio-', dir='/tmp') as directory:
    root = Path(directory)
    result = plan(root, 'synthetic-markers-v1')
    assert set(result['plannedMembers']) == set(module['MEMBERS'])
    assert result['plannedMembers']['demo.db'] == str(root/'demo.db')
    assert result['generator']['outputDirectory'] == str(root/'materials')
    assert all(Path(p).is_relative_to(root) for p in result['plannedMembers'].values())
    assert not any(result[k] for k in ('startupAllowed','isolationVerified','filesCreated','databaseOpened'))
    assert result['proposedConfiguration']['seed_demo'] is False
    assert list(root.iterdir()) == []
    rejected(lambda: plan(root, 'unlisted-handmade-sample'))
    rejected(lambda: plan('relative-synthetic-root', 'synthetic-markers-v1'))
    rejected(lambda: plan(root/'..'/'elsewhere', 'synthetic-markers-v1'))
    for member in ('../outside.wav', '/outside.wav', 'materials/../demo.db', 'extra.wav'):
        rejected(lambda: member_path(root, member))
    # A normal file in a caller-owned synthetic directory is not an empty root.
    (root/'synthetic-note.txt').write_text('synthetic fixture only')
    rejected(lambda: plan(root, 'synthetic-markers-v1'))
    assert (root/'synthetic-note.txt').read_text() == 'synthetic fixture only'
print('PASS normal empty-root plan and ordinary invalid sample/path/nonempty checks; no application or database')
