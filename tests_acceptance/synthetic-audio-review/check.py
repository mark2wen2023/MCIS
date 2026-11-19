"""Normal-path only. Reads two fixed pure sources (Git blobs or explicit offline directory), never imports MCIS packages."""
import argparse
import ast
import copy
import hashlib
from pathlib import Path
import subprocess
from make_fixture import fixture, timed_fixture

ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT = '3a19c75221dc770042708972bf7a1a36d681e121'
PINS = {
    'media_reference.py': 'd6eb37ec028a1dd01607af3421ed375d8cf87c1f1a09099b95c59bc30f49e959',
    'media_reference_reader.py': '717f87364d5a7205195a81d72b620a420b854599425cecbfd55f5aafdf459c50'
}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-dir', type=Path,
                    help='Explicit directory containing the two exact pinned .py files; never downloaded')
args = parser.parse_args()


def source_bytes(name):
    if args.source_dir is not None:
        path = args.source_dir / name
        require(path.is_file(), 'Pinned source file missing; stop, no fallback or fetch.')
        raw = path.read_bytes()
    else:
        result = subprocess.run(['git', '-C', str(ROOT), 'show',
                                 SOURCE_COMMIT + ':service/mcis_service/reports/' + name],
                                capture_output=True, check=False)
        require(result.returncode == 0, 'Pinned pure source object unavailable; stop, no automatic fetch.')
        raw = result.stdout
    require(hashlib.sha256(raw).hexdigest() == PINS[name], 'Pinned source hash mismatch: ' + name)
    return raw


# Verify BOTH byte sequences before compiling/executing either. Execute only the
# checked in-memory bytes, not a subsequently re-opened file.
verified = {name: source_bytes(name) for name in PINS}


def source(name):
    return ast.parse(verified[name], filename=name)


# Match the existing acceptance approach: resolve only the pure relative import.
projector = {}
exec(compile(source('media_reference.py'), '<pinned pure projector>', 'exec'), projector)
tree = source('media_reference_reader.py')
relative = [n for n in tree.body if isinstance(n, ast.ImportFrom) and n.level]
require(len(relative) == 1 and relative[0].module == 'media_reference',
        'Unexpected dependency; stop')
tree.body.remove(relative[0])
reader_env = {k: projector[k] for k in ('ProjectionUnavailable', 'project_saved_media')}
exec(compile(tree, '<pinned pure exact reader>', 'exec'), reader_env)
read = reader_env['read_exact_media_reference']
data = fixture()
before = copy.deepcopy(data)
calls = []


class SavedShapeReader:
    """Explicit in-memory adapter; not a service or real persisted storage."""
    case_id = data['request']['case_id']

    def read_revision(self, media, run_id, revision):
        calls.append(('revision', revision))
        return copy.deepcopy([row for row in available
                              if row['case_id'] == self.case_id and row['run_id'] == run_id
                              and row['revision'] == revision])

    def read_evidence(self, evidence_id):
        calls.append(('evidence', evidence_id))
        require(evidence_id == data['evidenceItem']['evidenceId'], 'Unexpected item read')
        return copy.deepcopy(data['evidenceItem'])


available = data['rows'][:2]
old = read(reader=SavedShapeReader(), **data['request'])
require(old['projection']['revision'] == 1, 'First reference must pin revision 1')
require(old['projection']['humanText'] == available[1]['doc']['text'], 'First text lost')
# This is a serialized reference fixture, NOT an exported report document.
stored_reference = copy.deepcopy(old)
available = data['rows']
second = read(reader=SavedShapeReader(), **dict(data['request'], revision=2))
require(second['projection']['revision'] == 2, 'Second reference must pin revision 2')
require(second['projection']['humanText'] == data['rows'][2]['doc']['text'], 'Second text lost')
require(second['projection']['humanText'] != old['projection']['humanText'],
        'Second text must differ from first text')
require(second['referenceSha256'] != old['referenceSha256'], 'Revision references must differ')
require(second['projection']['humanRevisionSha256'] != old['projection']['humanRevisionSha256'],
        'Human content must be separately bound')
calls.clear()
reopened = read(reader=SavedShapeReader(), expected_reference_sha256=stored_reference['referenceSha256'],
                **data['request'])
require(reopened == stored_reference, 'Old exact reference changed after second revision')
require(calls == [('revision', 0), ('revision', 1),
                  ('evidence', data['request']['evidence_id'])], 'Unexpected latest/history read')
for row in data['rows'][1:]:
    d = row['doc']
    require(d['startMs'] is None and d['endMs'] is None and d['timeStatus'] == 'unknown',
            'Do not convert a time interval in reference text into audio localization')
    require(d['speaker'] == {'status': 'unknown', 'id': None} and d['factVerified'] is False,
            'No identity or fact verification')
require(data == before, 'Input fixture mutated')
print('PASS one normal synthetic scenario: first/second exact reference and old-reference re-read')
# A separate normal input: same text, two declared within-file ranges.
data = timed_fixture()
before = copy.deepcopy(data)
for row in data['rows'][1:]:
    d = row['doc']
    audio = data['rows'][0]['doc']['audio']
    require(type(d['startMs']) is int and type(d['endMs']) is int
            and 0 <= d['startMs'] < d['endMs'] <= data['rows'][0]['doc']['machineDraft']['source']['durationMs']
            and d['endMs'] * audio['sampleRateHz'] <= audio['frames'] * 1000,
            'Handmade range must fit synthetic sample basis')
    require(d['timeStatus'] == 'operator_declared' and d['factVerified'] is False,
            'Declared times are not verified incident times')
available = data['rows'][:2]
early = read(reader=SavedShapeReader(), **data['request'])
available = data['rows']
calls.clear()
late = read(reader=SavedShapeReader(), **dict(data['request'], revision=2))
require(calls == [('revision', 0), ('revision', 2),
                  ('evidence', data['request']['evidence_id'])], 'Late exact read order')
require(early['projection']['revision'] == 1 and late['projection']['revision'] == 2,
        'Explicit early/late revision')
require(early['projection']['humanText'] == late['projection']['humanText']
        == data['rows'][1]['doc']['text'] == data['rows'][2]['doc']['text'], 'Identical text')
require(early['referenceSha256'] != late['referenceSha256'], 'Distinct revision references')
calls.clear()
again = read(reader=SavedShapeReader(), expected_reference_sha256=early['referenceSha256'],
             **data['request'])
require(again == early, 'Old range reference digest remains stable')
require(calls == [('revision', 0), ('revision', 1),
                  ('evidence', data['request']['evidence_id'])], 'Early exact re-read order')
# Controlled normal input sensitivity, NOT a stored-row mutation or failure probe.
# Hold every field, including revision, utc and expectedRevision, identical.
control = copy.deepcopy(data)
control['rows'][1]['doc'].update(startMs=4000, endMs=5500)
changed_keys = {k for k in before['rows'][1]['doc']
                if before['rows'][1]['doc'][k] != control['rows'][1]['doc'][k]}
require(changed_keys == {'startMs', 'endMs'}, 'Only time bounds may vary')
require(control['rows'][0] == data['rows'][0] and control['rows'][2] == data['rows'][2]
        and control['evidenceItem'] == data['evidenceItem'], 'Other inputs identical')
available = control['rows']
sensitive = read(reader=SavedShapeReader(), **data['request'])
require(sensitive['projection']['revision'] == early['projection']['revision'] == 1
        and sensitive['projection']['humanText'] == early['projection']['humanText'],
        'Control fixes revision and text')
require(sensitive['projection']['humanRevisionSha256'] != early['projection']['humanRevisionSha256']
        and sensitive['referenceSha256'] != early['referenceSha256'],
        'Fixed-revision bounds must affect both digests')
for result in (early, late, again, sensitive):
    require(result['projection']['target'] == {'segmentId': 'SEG-SYN-1'}
            and 'startMs' not in result['projection'] and 'endMs' not in result['projection'],
            'Current projection does not return playback bounds')
require(data == before, 'Original timed fixture must remain unchanged')
print('PASS timed synthetic scenario: exact early/late, old digest re-read, fixed-revision bounds sensitivity')
print('NOT RUN: authorization, missing-evidence, HTTP, ORM, save, report export/reopen, browser, ASR')
print('Source:', SOURCE_COMMIT, '| no media candidate code merged into this UI-derived branch')

print('Input mode:', 'explicit offline directory' if args.source_dir is not None else 'fixed local Git objects')
