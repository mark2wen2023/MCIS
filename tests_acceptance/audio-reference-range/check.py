"""Only normal handcrafted reads. No ORM, application imports, Save or network."""
import ast
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULES = ROOT / 'service/mcis_service/reports'


def load(name, dependencies=None):
    tree = ast.parse((MODULES / name).read_text())
    # Only explicit local pure dependencies; do not import package __init__.
    tree.body = [n for n in tree.body if not (isinstance(n, ast.ImportFrom) and n.level)]
    env = dict(dependencies or {})
    exec(compile(tree, name, 'exec'), env)
    return env


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


p = load('media_reference.py')
r = load('media_reference_reader.py', p)
f = load('audio_reference_range.py', r)['read_exact_audio_range']
# The existing acceptance fixture function only; no existing tests executed.
tree = ast.parse((ROOT/'tests_acceptance/media-report-reference/check.py').read_text())
env = dict(A='a'*64, B='b'*64, C='c'*64, D='d'*64)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'fixture'], type_ignores=[]), '<synthetic fixture only>', 'exec'), env)

for version, unknown in [(2, False), (3, False), (3, True)]:
    data = env['fixture']('audio')
    initial, first = [x['doc'] for x in data['saved_rows']]
    initial['audio'] = dict(format='PCM_WAV', channels=1, sampleWidthBytes=2, sampleRateHz=8000, frames=96000)
    initial['machineDraft']['version'] = version
    source = initial['machineDraft']['source']; source['durationMs'] = 12000
    if version == 3:
        source.update(frameCount=96000, sampleRateHz=8000)
    first.update(reason='synthetic', operator='synthetic', role='Investigator', utc='2026-01-01T00:00:00Z',
                 startMs=None if unknown else 1000, endMs=None if unknown else 2500,
                 timeStatus='unknown' if unknown else 'operator_declared', speaker={'status':'unknown','id':None})
    later = deepcopy(data['saved_rows'][1]); later['revision'] = 2
    later['doc'].update(revision=2, expectedRevision=1, startMs=4000, endMs=5500, timeStatus='operator_declared')
    available = data['saved_rows']; calls = []
    class Reader:
        case_id = 'CASE-SYN'
        def read_revision(self, media, run, revision):
            calls.append(('revision', media, run, revision))
            return deepcopy([row for row in available if row['case_id'] == self.case_id and row['run_id'] == run and row['revision'] == revision])
        def read_evidence(self, eid):
            calls.append(('evidence', eid))
            return deepcopy(next(i for i in data['evidence_items'] if i['evidenceId'] == eid))
    args = {k:data[k] for k in ('media','case_id','run_id','revision','evidence_id','evidence_role')}
    old = r['read_exact_media_reference'](reader=Reader(), **args)
    available = data['saved_rows'] + [later]
    before = deepcopy(available)
    calls.clear()
    result = f(reader=Reader(), case_id='CASE-SYN', evidence_id='EV-A', run_id='RUN-SYN', revision=1,
               segment_id='SEG-SYN', expected_reference_sha256=old['referenceSha256'])
    require(calls == [('revision','audio','RUN-SYN',0),('revision','audio','RUN-SYN',1),('evidence','EV-A')], 'one exact read sequence')
    require((result['startMs'],result['endMs']) == ((None,None) if unknown else (1000,2500)), 'old range or explicit unknown')
    require(result['rangeStatus'] == ('unknown' if unknown else 'operator_declared'), 'range status')
    require(result['timeBasis'] == {'kind':'file-relative-milliseconds','frames':96000,'sampleRateHz':8000}, 'original sample basis')
    new = r['read_exact_media_reference'](reader=Reader(), **dict(args,revision=2))
    newer = f(reader=Reader(), case_id='CASE-SYN', evidence_id='EV-A', run_id='RUN-SYN', revision=2,
              segment_id='SEG-SYN', expected_reference_sha256=new['referenceSha256'])
    require((newer['startMs'],newer['endMs']) == (4000,5500), 'later exact range')
    require(new['projection']['humanText'] == old['projection']['humanText'], 'same text')
    require(r['read_exact_media_reference'](reader=Reader(), **args) == old, 'default projection and digest unchanged')
    require(available == before and result['mediaRetrieved'] is False and result['factVerified'] is False, 'no mutation/media/approval')
    print('PASS normal range read:', version, 'unknown' if unknown else 'declared')
print('NOT RUN: real snapshot/ORM/authorization, failure paths, media, report routes, HTTP, Save, browser or models')
