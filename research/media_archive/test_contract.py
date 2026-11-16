"""Fabricated byte/JSON fixtures only; no actual media, OCR/ASR or product import."""
import base64
import copy
import json
import pytest
from .contract import FORMAT, digest, validate


def fixture(kind='audio', status='succeeded'):
    index = dict(format=FORMAT, caseId='SYN', restoreReady=False,
                 taskPolicy='inactive-history-never-execute', members={}, sources=[], runs=[], tasks=[], audit=[])
    blobs = {}
    def put(name, value):
        raw = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()
        blobs[name] = raw
        index['members'][name] = dict(size=len(raw), sha256=digest(raw))
        return name
    def source(name, typ, location):
        sha = digest(b'synthetic-'+name.encode())
        row = dict(id=name, caseId='SYN', kind=typ, evidenceId='EV-'+name,
                   receiptMember=put(name+'-receipt', dict(caseId='SYN', evidenceId='EV-'+name, sourceSha256=sha)),
                   originalMember=put(name+'-original', b'synthetic-'+name.encode()),
                   registeredSha256=sha, currentSha256=sha, location=location)
        index['sources'].append(row)
        return row
    if kind == 'audio':
        src = source('SRC', 'audio', dict(frameCount=16001, sampleRateHz=16000, channels=1, sampleWidthBytes=2))
    else:
        pdf = source('PDF', 'pdf', None)
        src = source('SRC', 'page-image', dict(pdfSourceId='PDF', pdfPage1Based=6, printedPage='4',
                     mappingBasis='manual-declaration-not-verified', width=100, height=200))
    prefix = 'asr' if kind == 'audio' else 'ocr'
    def audit(command, action):
        seq = len(index['audit']) + 1
        prev = digest(blobs[index['audit'][-1]['member']]) if seq > 1 else '0'*64
        m = put('audit-'+str(seq), dict(seq=seq, prev=prev, command=command, action=action,
                operator='Synthetic', role='LeadInvestigator', utc='2026-01-01T00:00:00Z'))
        index['audit'].append(dict(caseId='SYN', seq=seq, member=m))
        return seq
    first = audit('TASK', prefix+'.task.start')
    run_id = 'RUN' if status == 'succeeded' else None
    task_doc = dict(taskId='TASK', caseId='SYN', status=status, runId=run_id)
    task = dict(id='TASK', caseId='SYN', sourceId='SRC', recordedStatus=status, runId=run_id,
                recordMember=put('task', task_doc), auditSeqs=[first], executionPolicy='never')
    index['tasks'].append(task)
    if status == 'succeeded':
        raw = put('raw', {'text': '明确标注的合成输出', 'timestamp': None})
        if kind == 'audio':
            machine = dict(source=dict(currentSha256=src['currentSha256'], frameCount=16001, sampleRateHz=16000),
                           recognizerResultSha256=digest(blobs[raw]), transcript={'unlocatedSegments': [{'id': 'u1', 'text': '合成'}]})
        else:
            machine = dict(source=dict(image_sha256=src['currentSha256'], pdf_sha256=pdf['currentSha256'],
                           raw_sha256=digest(blobs[raw]), pdf_page_1based=6), text_lines=[{'text': '合成', 'polygon': [[0,0],[5,0],[5,5],[0,5]]}])
        candidate = put('machine', machine)
        initial_doc = dict(artifactTaskId='TASK', operator='Synthetic')
        initial_doc['machineDraft' if kind == 'audio' else 'candidate'] = machine
        initial = put('initial', initial_doc)
        task_doc['artifacts'] = {k: {'sha256': digest(blobs[m])} for k,m in [('raw',raw),('candidate',candidate)]}
        if kind == 'audio':
            task_doc.update(raw=json.loads(blobs[raw]), candidate=machine)
        else:
            task_doc.update(rawBase64=base64.b64encode(blobs[raw]).decode(), candidateBase64=base64.b64encode(blobs[candidate]).decode())
        put('task',task_doc)
        seq = audit('TASK', prefix+'.task.succeeded'); task['auditSeqs'].append(seq)
        human = dict(revision=1, expectedRevision=0, factVerified=False, operator='Synthetic', role='LeadInvestigator',
                     utc='2026-01-01T00:00:01Z', reason='合成校对', text='人工输入，不是事实认定')
        human.update(dict(startMs=None, endMs=None, timeStatus='unknown', speaker={'status':'unknown','id':None}) if kind == 'audio' else dict(lineIndex=0))
        run = dict(id='RUN', caseId='SYN', sourceId='SRC', initialMember=initial, machineMember=candidate, rawMember=raw,
                   recognizerMember=put('recognizer', {'model':'synthetic-not-executed','version':'test-only'}),
                   historyStatus='prior-history-unknown', taskId='TASK', revisions=[dict(revision=0, member=initial, auditSeq=seq),
                   dict(revision=1, member=put('human', human), auditSeq=audit('RUN', 'audio.human.revise' if kind=='audio' else 'ocr.review'))])
        index['runs'].append(run)
    return index, blobs, put


@pytest.mark.parametrize('kind', ['audio', 'image'])
@pytest.mark.parametrize('status', ['succeeded','failed','running_or_unknown','interrupted_unknown'])
def test_preserve_bytes_unknown_and_never_execute(kind, status):
    i,b,_=fixture(kind,status); before=copy.deepcopy((i,b))
    result=validate(i,b)
    assert result['restore_ready'] is False and result['execution_allowed'] is False
    assert (i,b)==before
    assert result['runCount']==(1 if status=='succeeded' else 0)


@pytest.mark.parametrize('field', ['rawMember','recognizerMember','initialMember','machineMember','historyStatus','revisions'])
def test_missing_required_run_field_rejected(field):
    i,b,_=fixture(); del i['runs'][0][field]
    with pytest.raises(ValueError): validate(i,b)


@pytest.mark.parametrize('change', [
    lambda i,b:i.update(restoreReady=True),
    lambda i,b:i['tasks'][0].update(executionPolicy='resume'),
    lambda i,b:i['tasks'][0].update(recordedStatus='queued'),
    lambda i,b:i['runs'][0].update(caseId='OTHER'),
    lambda i,b:i['sources'][0].update(currentSha256='0'*64),
    lambda i,b:i['runs'][0]['revisions'][1].update(revision=2),
    lambda i,b:i['runs'][0]['revisions'][1].update(auditSeq=1),
    lambda i,b:i['tasks'][0].update(runId=None),
    lambda i,b:i['sources'][0]['location'].update(sampleRateHz=0),
    lambda i,b:i['runs'][0].update(taskId='MISSING'),
    lambda i,b:b.pop('raw'),
    lambda i,b:b.update(raw=b'changed'),
])
def test_invalid_or_missing_association_rejected(change):
    i,b,_=fixture(); change(i,b)
    with pytest.raises(ValueError): validate(i,b)


@pytest.mark.parametrize('start,end,valid', [(None,None,True),(0,1000,True),(0,1001,False),(0,0,False),(None,1,False)])
def test_exact_nonintegral_sample_clock_and_unknown(start,end,valid):
    i,b,put=fixture(); doc=json.loads(b['human']); doc.update(startMs=start,endMs=end,timeStatus='unknown' if start is None and end is None else 'operator_declared'); put('human',doc)
    if valid: assert validate(i,b)['restore_ready'] is False
    else:
        with pytest.raises(ValueError): validate(i,b)


@pytest.mark.parametrize('change', [lambda i:i['sources'][1]['location'].update(pdfPage1Based=0),
                                   lambda i:i['sources'][1]['location'].update(pdfSourceId='MISSING'),
                                   lambda i:i['sources'][1]['location'].update(mappingBasis='verified')])
def test_page_declaration_not_automatic_verification(change):
    i,b,_=fixture('image');change(i)
    with pytest.raises(ValueError):validate(i,b)


@pytest.mark.parametrize('field', ['raw','candidate','artifacts'])
def test_successful_task_missing_saved_output_is_rejected(field):
    i,b,put=fixture(); doc=json.loads(b['task']); del doc[field]; put('task',doc)
    with pytest.raises(ValueError): validate(i,b)


def test_initial_document_must_retain_same_machine_result():
    i,b,put=fixture(); doc=json.loads(b['initial']); doc['machineDraft']={}; put('initial',doc)
    with pytest.raises(ValueError): validate(i,b)


def test_audit_gap_is_not_reconstructed():
    i,b,_=fixture(); i['audit'].pop(1)
    with pytest.raises(ValueError): validate(i,b)


def test_extra_member_is_not_silently_dropped():
    i,b,put=fixture(); put('unmapped',{'synthetic':True})
    with pytest.raises(ValueError): validate(i,b)


@pytest.mark.parametrize('status',['failed','interrupted_unknown'])
def test_native_asr_incomplete_action_retained(status):
    i,b,put=fixture('audio',status)
    previous=digest(b[i['audit'][-1]['member']])
    member=put('audit-incomplete',dict(seq=2,prev=previous,command='TASK',action='asr.task.incomplete'))
    i['audit'].append(dict(caseId='SYN',seq=2,member=member))
    i['tasks'][0]['auditSeqs'].append(2)
    assert validate(i,b)['execution_allowed'] is False
