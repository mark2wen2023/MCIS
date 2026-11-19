"""Normal in-memory composition only. Associations below are TEST FIXTURE DATA.
No application imports, storage, media bytes, network, permission or Save calls.
"""
import ast
from copy import deepcopy
import json
from pathlib import Path
import runpy
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
MODULES = ROOT/'service/mcis_service/reports'


def functions_only(relative, names, env):
    tree = ast.parse((ROOT/relative).read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), relative, 'exec'), env)
    return env


# Reuse only existing handmade fixture builders; never execute their test files.
fixtures = functions_only('tests_acceptance/media-report-reference/check.py', ['fixture'],
                         dict(A='a'*64, B='b'*64, C='c'*64, D='d'*64))
reports = functions_only('tests_acceptance/report-generation-snapshot/check.py',
                         ['report', 'inputs'], dict(deepcopy=deepcopy))
loader = functions_only('tests_acceptance/audio-reference-range/check.py', ['load'],
                        dict(ast=ast, MODULES=MODULES))['load']
projection = loader('media_reference.py')
reader_code = loader('media_reference_reader.py', projection)
range_read = loader('audio_reference_range.py', reader_code)['read_exact_audio_range']
sentence_read = runpy.run_path(str(MODULES/'generation_snapshot.py'))['generation_sentence']
validator = Draft202012Validator(json.loads((ROOT/'contracts/schemas/report.schema.json').read_text()))


def validate(name, doc):
    assert name == 'report'
    validator.validate(doc)


def scenario(unknown):
    data = fixtures['fixture']('audio')
    initial, first = [r['doc'] for r in data['saved_rows']]
    initial['audio'] = dict(format='PCM_WAV', channels=1, sampleWidthBytes=2,
                            sampleRateHz=8000, frames=96000)
    initial['machineDraft']['version'] = 3
    initial['machineDraft']['source'].update(durationMs=12000, frameCount=96000, sampleRateHz=8000)
    first.update(reason='synthetic', operator='synthetic', role='Investigator',
                 utc='2026-01-01T00:00:00Z', speaker={'status':'unknown','id':None},
                 startMs=None if unknown else 1000, endMs=None if unknown else 2500,
                 timeStatus='unknown' if unknown else 'operator_declared')
    later = deepcopy(data['saved_rows'][1])
    later['revision'] = 2
    later['doc'].update(revision=2, expectedRevision=1, startMs=4000, endMs=5500,
                        timeStatus='operator_declared')
    available = deepcopy(data['saved_rows'])
    calls = []

    class MemoryReader:
        case_id = 'CASE-SYN'
        def read_revision(self, media, run, revision):
            calls.append(('revision', media, run, revision))
            return deepcopy([r for r in available if r['case_id'] == self.case_id
                             and r['run_id'] == run and r['revision'] == revision])
        def read_evidence(self, eid):
            calls.append(('evidence', eid))
            return deepcopy(next(i for i in data['evidence_items'] if i['evidenceId'] == eid))

    def reference(revision):
        return reader_code['read_exact_media_reference'](reader=MemoryReader(), media='audio',
            case_id='CASE-SYN', evidence_id='EV-A', evidence_role='audio',
            run_id='RUN-SYN', revision=revision)['referenceSha256']

    old_report = reports['report']('RPT-'+'1'*20, 1, 'Synthetic first sentence')
    old_report.update(caseId='CASE-SYN', reportHref='#/report?case=CASE-SYN')
    old_inputs = reports['inputs'](old_report, 1)
    # Explicit manual TEST association, not generated or persisted by any service.
    old_link = dict(fixtureOnly=True, sourceVerified=False, persistentBinding=False,
                    caseId='CASE-SYN', reportId=old_report['reportId'],
                    snapshotId=old_inputs['snapshot']['snapshotId'],
                    sectionId='section-synthetic', sentenceId='sentence-synthetic',
                    evidenceId='EV-A', runId='RUN-SYN', revision=1, segmentId='SEG-SYN',
                    referenceSha256=reference(1))

    def connected(values, link):
        assert link['fixtureOnly'] and not link['sourceVerified'] and not link['persistentBinding']
        assert values['snapshot']['snapshotId'] == link['snapshotId']
        sentence = sentence_read(case_id=link['caseId'], report_id=link['reportId'],
            section_id=link['sectionId'], sentence_id=link['sentenceId'],
            validate_contract=validate, **values)
        calls.clear()
        result = range_read(reader=MemoryReader(), case_id=sentence['caseId'],
            evidence_id=link['evidenceId'], run_id=link['runId'], revision=link['revision'],
            segment_id=link['segmentId'], expected_reference_sha256=link['referenceSha256'])
        assert calls == [('revision','audio','RUN-SYN',0),
                         ('revision','audio','RUN-SYN',link['revision']),('evidence','EV-A')]
        assert result['caseId'] == sentence['caseId'] == link['caseId']
        assert result['referenceSha256'] == link['referenceSha256']
        assert not sentence['sourceVerified'] and not sentence['persistentBinding']
        assert not result['mediaRetrieved'] and not result['factVerified']
        assert result['timeBasis'] == dict(kind='file-relative-milliseconds', frames=96000, sampleRateHz=8000)
        return sentence, result

    old = connected(old_inputs, old_link)
    available.append(later)
    new_report = reports['report']('RPT-'+'2'*20, 2, 'Synthetic second sentence', old_report['reportId'])
    new_report.update(caseId='CASE-SYN', reportHref='#/report?case=CASE-SYN')
    new_inputs = reports['inputs'](new_report, 2, old_report)
    new_link = dict(old_link, reportId=new_report['reportId'],
                   snapshotId=new_inputs['snapshot']['snapshotId'], revision=2,
                   referenceSha256=reference(2))
    before = deepcopy((available, data, old_inputs, new_inputs, old_link, new_link))
    new = connected(new_inputs, new_link)
    reread = connected(old_inputs, old_link)
    assert reread == old
    assert old[0]['sentence']['textZh'] == 'Synthetic first sentence'
    assert new[0]['sentence']['textZh'] == 'Synthetic second sentence'
    assert (old[1]['startMs'],old[1]['endMs']) == ((None,None) if unknown else (1000,2500))
    assert old[1]['rangeStatus'] == ('unknown' if unknown else 'operator_declared')
    assert (new[1]['startMs'],new[1]['endMs']) == (4000,5500)
    assert old[1]['revision'] == 1 and new[1]['revision'] == 2
    assert old_link['referenceSha256'] != new_link['referenceSha256']
    assert before == (available, data, old_inputs, new_inputs, old_link, new_link)
    print('PASS synthetic composition:', 'independent unknown old time' if unknown else 'two declared ranges')


scenario(False)
scenario(True)
print('COMPLETE: fixture associations only; no persistent binding, authority, original audio or real snapshot transaction verified')
