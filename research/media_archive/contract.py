"""Offline proposed member/index validation only. No ZIP/DB/filesystem/worker adapter."""
import base64
import hashlib
import json
import re

FORMAT = 'MCIS-MEDIA-ARCHIVE-RESEARCH-1'
LIMIT = 16 * 1024 * 1024


def need(ok, message):
    if not ok:
        raise ValueError(message)


def shape(value, keys):
    need(type(value) is dict and set(value) == set(keys.split()), 'fields')


def integer(value, minimum=0):
    need(type(value) is int and value >= minimum, 'integer')


def ident(value):
    need(type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value), 'identifier')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            need(key not in out, 'duplicate JSON key')
            out[key] = value
        return out
    def constant(_):
        raise ValueError('nonfinite JSON')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)


def validate(index, payloads):
    """Check a bounded proposed index plus exact bytes; never return restore permission."""
    shape(index, 'format caseId restoreReady taskPolicy members sources runs tasks audit')
    need(index['format'] == FORMAT and index['restoreReady'] is False and
         index['taskPolicy'] == 'inactive-history-never-execute', 'research-only')
    ident(index['caseId'])
    need(type(payloads) is dict and type(index['members']) is dict, 'members')
    need(set(payloads) == set(index['members']) and len(payloads) <= 512, 'membership')
    need(all(type(b) is bytes and len(b) <= LIMIT for b in payloads.values()), 'member size')
    need(sum(map(len, payloads.values())) <= 64 * 1024 * 1024, 'aggregate size')
    used = set()
    for name, desc in index['members'].items():
        ident(name)
        shape(desc, 'size sha256')
        integer(desc['size'])
        need(desc['size'] == len(payloads[name]) and desc['sha256'] == digest(payloads[name]), 'digest')

    def member(name, as_json=False):
        ident(name)
        need(name in payloads, 'missing member')
        used.add(name)
        return parse(payloads[name]) if as_json else payloads[name]

    def records(key, fields, id_field='id'):
        values = index[key]
        need(type(values) is list and len(values) <= 1024, key)
        out = {}
        for row in values:
            shape(row, fields)
            ident(row[id_field])
            need(row[id_field] not in out and row['caseId'] == index['caseId'], 'case/id')
            out[row[id_field]] = row
        return out

    sources = records('sources', 'id caseId kind evidenceId receiptMember originalMember registeredSha256 currentSha256 location')
    for src in sources.values():
        ident(src['evidenceId'])
        receipt = member(src['receiptMember'], True)  # preserved inactive document, not credential
        need(type(receipt) is dict and receipt.get('caseId') == index['caseId'] and
             receipt.get('evidenceId') == src['evidenceId'] and receipt.get('sourceSha256') == src['registeredSha256'], 'registration association')
        raw = member(src['originalMember'])
        need(bool(raw), 'empty original')
        need(src['registeredSha256'] == src['currentSha256'] == digest(raw), 'source version')
        loc = src['location']
        if src['kind'] == 'pdf':
            need(loc is None, 'pdf location')
        elif src['kind'] == 'page-image':
            shape(loc, 'pdfSourceId pdfPage1Based printedPage mappingBasis width height')
            parent = sources.get(loc['pdfSourceId'])
            need(parent is not None and parent['kind'] == 'pdf', 'PDF parent')
            integer(loc['pdfPage1Based'], 1)
            need(loc['printedPage'] is None or type(loc['printedPage']) is str, 'printed page')
            need(loc['mappingBasis'] == 'manual-declaration-not-verified', 'page claim')
            integer(loc['width'], 1); integer(loc['height'], 1)
        elif src['kind'] == 'audio':
            shape(loc, 'frameCount sampleRateHz channels sampleWidthBytes')
            for value in loc.values():
                integer(value, 1)
        else:
            raise ValueError('source kind')

    # Retain full existing case audit lines; no reconstructed or truncated audit history.
    need(type(index['audit']) is list, 'audit')
    audits = {}
    previous = '0' * 64
    for seq, item in enumerate(index['audit'], 1):
        shape(item, 'caseId seq member')
        need(item['caseId'] == index['caseId'] and type(item['seq']) is int and item['seq'] == seq, 'audit sequence')
        raw = member(item['member'])
        doc = parse(raw)
        need(doc.get('seq') == seq and doc.get('prev') == previous, 'audit chain')
        audits[seq] = doc
        previous = digest(raw)

    def audit_link(seq, command, actions):
        integer(seq, 1)
        event = audits.get(seq)
        need(event is not None and event.get('command') == command and event.get('action') in actions, 'audit link')

    runs = records('runs', 'id caseId sourceId initialMember machineMember rawMember recognizerMember historyStatus revisions taskId')
    tasks = records('tasks', 'id caseId sourceId recordMember recordedStatus runId auditSeqs executionPolicy')
    for run in runs.values():
        src = sources.get(run['sourceId'])
        need(src is not None and src['kind'] in ('page-image', 'audio'), 'run source')
        for name in ('initialMember', 'machineMember', 'rawMember', 'recognizerMember'):
            need(type(member(run[name], True)) is dict, 'result object')
        machine = member(run['machineMember'], True)
        initial = member(run['initialMember'], True)
        native_key = 'candidate' if src['kind'] == 'page-image' else 'machineDraft'
        need(initial.get(native_key) == machine, 'initial machine document')
        need(initial.get('artifactTaskId') == run['taskId'], 'initial task association')
        raw_sha = digest(member(run['rawMember']))
        if src['kind'] == 'page-image':
            binding = machine.get('source', {})
            need(binding.get('image_sha256') == src['currentSha256'] and
                 binding.get('pdf_sha256') == sources[src['location']['pdfSourceId']]['currentSha256'] and
                 binding.get('raw_sha256') == raw_sha and
                 binding.get('pdf_page_1based') == src['location']['pdfPage1Based'], 'image result source')
            need(type(machine.get('text_lines')) is list, 'image lines')
        else:
            binding = machine.get('source', {})
            need(binding.get('currentSha256') == src['currentSha256'] and
                 binding.get('frameCount') == src['location']['frameCount'] and
                 binding.get('sampleRateHz') == src['location']['sampleRateHz'] and
                 machine.get('recognizerResultSha256') == raw_sha, 'audio result source')
        need(run['historyStatus'] in ('captured-from-initial', 'prior-history-unknown'), 'history status')
        revisions = run['revisions']
        need(type(revisions) is list and 1 <= len(revisions) <= 1001, 'revisions')
        prefix = 'ocr' if src['kind'] == 'page-image' else 'audio'
        for n, rev in enumerate(revisions):
            shape(rev, 'revision member auditSeq')
            need(type(rev['revision']) is int and rev['revision'] == n, 'revision continuity')
            doc = member(rev['member'], True)
            if n == 0:
                need(rev['member'] == run['initialMember'], 'initial linkage')
                actions = ('ocr.import', 'ocr.task.succeeded') if prefix == 'ocr' else ('audio.draft.attach', 'asr.task.succeeded')
                command = run['taskId'] if run['taskId'] is not None else run['id']
            else:
                need(doc.get('revision') == n and doc.get('expectedRevision') == n - 1 and doc.get('factVerified') is False, 'revision document')
                for k in ('operator', 'role', 'utc', 'reason'):
                    need(type(doc.get(k)) is str and bool(doc[k].strip()), 'revision provenance')
                if src['kind'] == 'audio':
                    start, end = doc.get('startMs'), doc.get('endMs')
                    need('startMs' in doc and 'endMs' in doc, 'missing time declaration')
                    if start is None and end is None:
                        need(doc.get('timeStatus') == 'unknown', 'unknown time')
                    else:
                        integer(start); integer(end, 1)
                        need(start < end and end * src['location']['sampleRateHz'] <= src['location']['frameCount'] * 1000 and
                             doc.get('timeStatus') == 'operator_declared', 'exact sample boundary')
                    need(doc.get('speaker') == {'status': 'unknown', 'id': None}, 'speaker claim')
                else:
                    integer(doc.get('lineIndex'))
                    need(doc['lineIndex'] < len(machine['text_lines']), 'line index')
                actions = ('ocr.review',) if prefix == 'ocr' else ('audio.human.revise',)
                command = run['id']
            audit_link(rev['auditSeq'], command, actions)
        if run['taskId'] is not None:
            task = tasks.get(run['taskId'])
            need(task is not None and task['runId'] == run['id'] and task['recordedStatus'] == 'succeeded' and task['sourceId'] == run['sourceId'], 'task result')
    for task in tasks.values():
        need(task['sourceId'] in sources and task['executionPolicy'] == 'never', 'inactive task')
        need(task['recordedStatus'] in ('succeeded', 'failed', 'running_or_unknown', 'interrupted_unknown'), 'task status')
        doc = member(task['recordMember'], True)
        need(doc.get('taskId') == task['id'] and doc.get('caseId') == index['caseId'] and doc.get('status') == task['recordedStatus'] and doc.get('runId') == task['runId'], 'task document')
        if task['recordedStatus'] == 'succeeded':
            need(task['runId'] in runs and runs[task['runId']]['taskId'] == task['id'], 'missing successful run')
            run = runs[task['runId']]
            artifacts = doc.get('artifacts', {})
            for key, field in (('raw', 'rawMember'), ('candidate', 'machineMember')):
                raw = member(run[field])
                need(artifacts.get(key, {}).get('sha256') == digest(raw), 'task artifact digest')
                if sources[task['sourceId']]['kind'] == 'page-image':
                    encoded = doc.get(key+'Base64')
                    need(type(encoded) is str, 'missing task result')
                    need(base64.b64decode(encoded, validate=True) == raw, 'task result bytes')
                else:
                    need(doc.get(key) == parse(raw), 'task result JSON')
        else:
            need(task['runId'] is None, 'unfinished task result')
        need(type(task['auditSeqs']) is list and len(task['auditSeqs']) >= 1 and len(set(task['auditSeqs'])) == len(task['auditSeqs']), 'task audit')
        prefix = 'ocr' if sources[task['sourceId']]['kind'] == 'page-image' else 'asr'
        for seq in task['auditSeqs']:
            audit_link(seq, task['id'], tuple(prefix+'.task.'+s for s in ('start', 'succeeded', 'failed', 'unknown')))
    need(used == set(payloads), 'unreferenced member')
    return {'restore_ready': False, 'execution_allowed': False, 'scope': 'offline-index-and-member-consistency-only',
            'sourceCount': len(sources), 'runCount': len(runs), 'taskCount': len(tasks)}
