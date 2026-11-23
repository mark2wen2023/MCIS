"""Acceptance only. Default preflight does not create a DB or execute .NET."""
import os
os.environ['GIT_NO_LAZY_FETCH'] = '1'
import argparse
import asyncio
import base64
from copy import deepcopy
import hashlib
import importlib
import importlib.abc
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

PRODUCT = 'db90fdf73de7bd26ba75819f0102fc03d0789faf'
ECFC = 'd9187fef1f979866ac4d8ce2064d1ac92f34bb36'
FIXTURE = 'b61aa93128ceb0cbe80ce9204579d35c7d31497d'
RAW_SHA = '418be9609b46a00062c41fb49073911986098e9a61e010f4311aa86946ecd3ea'
MODULES = '''__init__ config db common/__init__ common/contracts common/context common/timeutil common/csjson
cases/__init__ cases/models cases/service audit/__init__ audit/models audit/service
evidence/__init__ evidence/models evidence/service evidence_intake/__init__ evidence_intake/parser evidence_intake/router
redaction/__init__ redaction/models redaction/policy redaction/gateway reports/__init__ reports/models reports/access
interviews/__init__ interviews/models interviews/access manual_interviews/__init__ manual_interviews/models
working_records_archive/__init__ working_records_archive/models working_records_archive/validation working_records_archive/service
track_history/__init__ track_history/models track_history/service report_output/__init__ report_output/attachment_access'''.split()
ECFC_MODULES = ['ecfc_drafts/__init__', 'ecfc_drafts/models', 'ecfc_drafts/router']
CORE = '''tools/mcis-ecfc/mcis-ecfc.sh tools/mcis-ecfc/build.py tools/mcis-ecfc/McisEcfc.csproj tools/mcis-ecfc/src/Program.cs
unity/Assets/_Project/Scripts/Core/Primitives/SimTime.cs unity/Assets/_Project/Scripts/Domain/Common/GeoPrimitives.cs
unity/Assets/_Project/Scripts/Domain/Common/EcfcAndDamageEnums.cs unity/Assets/_Project/Scripts/Domain/Models/EcfcModels.cs
unity/Assets/_Project/Scripts/Domain/Ecfc/EcfcValidator.cs'''.split()
CID = 'SYN-XREPO-001'


def require(condition, label):
    if not condition:
        raise RuntimeError(label)


def materialize(repo, root):
    def copy(ref, path):
        cmd = ['git', '-C', str(repo)]
        entry = subprocess.check_output(cmd + ['ls-tree', ref, '--', path]).decode().split()
        mode = '100755' if path.endswith('/mcis-ecfc.sh') else '100644'
        require(len(entry) == 4 and entry[:2] == [mode, 'blob'] and entry[3] == path, 'fixed_blob_missing')
        raw = subprocess.check_output(cmd + ['show', ref + ':' + path])
        require(hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest() == entry[2], 'fixed_blob_mismatch')
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as f:
            f.write(raw)
        if mode == '100755':
            target.chmod(0o700)  # Only this newly materialized original launcher.
        return raw
    for name in MODULES:
        copy(PRODUCT, 'service/mcis_service/' + name + '.py')
    for name in ECFC_MODULES:
        copy(ECFC, 'service/mcis_service/' + name + '.py')
    for name in ('case', 'common', 'evidence-item'):
        copy(PRODUCT, 'contracts/schemas/' + name + '.schema.json')
    for path in CORE:
        copy(ECFC, path)
    raw = copy(FIXTURE, 'tests_acceptance/w11-t109-registered-source/communication.txt')
    require(hashlib.sha256(raw).hexdigest() == RAW_SHA, 'fixture_sha')
    require(raw[97:121].decode('utf-8') == '2026-02-01T12:01:49.000Z', 'fixture_locator')
    require(raw.decode('utf-8').startswith('纯合成通联记录'), 'fixture_scope')
    return raw


def load_modules(root):
    # No module replacement: only pinned ordinary modules may be imported.
    names = {'mcis_service' + ('.' + n.replace('/__init__', '').replace('/', '.') if n != '__init__' else '')
             for n in MODULES + ECFC_MODULES}
    require(not any(n == 'mcis_service' or n.startswith('mcis_service.') for n in sys.modules), 'already_loaded_product')
    class Whitelist(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.startswith('mcis_service.') and fullname not in names:
                raise ImportError('Product module outside pinned whitelist: ' + fullname)
    sys.meta_path.insert(0, Whitelist())
    sys.path.insert(0, str(root / 'service'))
    api = importlib.import_module('mcis_service.ecfc_drafts.router')
    intake = importlib.import_module('mcis_service.evidence_intake.router')
    for name, module in tuple(sys.modules.items()):
        if name == 'mcis_service' or name.startswith('mcis_service.'):
            require(name in names and Path(module.__file__).resolve().is_relative_to(root), 'import_origin')
    return api, intake


class Body:
    """Synthetic request-body transport only; no HTTP client/server or auth stub."""
    headers = {'content-type': 'application/json'}
    def __init__(self, value):
        self.raw = json.dumps(value).encode()
    async def stream(self):
        yield self.raw


def graph(eid):
    return {'scope': 'Synthetic pending communication association; not event proof',
            'nodes': [{'id': n, 'kind': 'Event', 'text': 'Synthetic pending ' + n,
                       'timeSeconds': None, 'lane': 0, 'isPrimaryIncident': False,
                       'evidenceIds': [eid]} for n in ('start', 'end')],
            'edges': [{'id': 'communication', 'from': 'start', 'to': 'end'}]}


def exercise(root, api, intake, raw):
    from sqlalchemy import text, select
    from mcis_service.db import Database, Base, put_doc, APPEND_ONLY_TABLES, WRITE_LOCK
    from mcis_service.common.context import Ctx
    from mcis_service.common import contracts
    from mcis_service.cases.models import CaseRow
    from mcis_service.evidence.models import EvidenceRow, CustodyEventRow
    from mcis_service.audit.models import AuditEventRow
    from mcis_service.audit.service import verify_chain, all_lines
    from mcis_service.redaction.models import AccessPolicyRow
    from mcis_service.redaction.policy import default_policy
    from mcis_service.working_records_archive.models import ArchiveImportHistoryRow
    from mcis_service.track_history.models import LocalReceipt
    from mcis_service.ecfc_drafts.models import EcfcWorksheetRow, EcfcAuditRow, EcfcRequestRow
    db = Database('sqlite:///' + str(root / 'fresh.sqlite'))
    try:
        models = (CaseRow, EvidenceRow, CustodyEventRow, AuditEventRow, AccessPolicyRow,
                  ArchiveImportHistoryRow, LocalReceipt, EcfcWorksheetRow, EcfcAuditRow, EcfcRequestRow)
        Base.metadata.create_all(db.engine, tables=[m.__table__ for m in models])
        with db.engine.begin() as c:
            for table in APPEND_ONLY_TABLES:
                for op in ('UPDATE', 'DELETE'):
                    c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_no_{op.lower()} BEFORE {op} ON {table} BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END;"))
        blobs = root / 'blobs'; blobs.mkdir()
        state = SimpleNamespace(db=db, settings=SimpleNamespace(blob_dir=blobs))
        request = SimpleNamespace(app=SimpleNamespace(state=state))
        ctx = Ctx(role='LeadInvestigator', operator='Synthetic ECFC acceptance', request=request)
        # Only initial case/policy scaffolding; never insert evidence, graph, audit or receipt results.
        case = {'caseId': CID, 'schemaVersion': '1.0.0', 'title': 'Synthetic ECFC acceptance',
                'accidentType': 'Synthetic', 'isFictionalDemo': True,
                'caseEpochUtc': '2026-02-01T12:00:00Z', 'incidentTimeUtc': '2026-02-01T12:00:00Z',
                'incidentLocation': {'lonDeg': -130, 'latDeg': -30}, 'displayTimeZoneOffsetMinutes': 0}
        contracts.validate('case', case)
        with db.session() as s:
            put_doc(s, CaseRow, CID, CID, case)
            put_doc(s, AccessPolicyRow, CID, 'policy', default_policy())
        body = {'profile': 'mcis-evidence-intake-v1', 'fileName': 'communication.txt',
                'title': 'Synthetic communication', 'source': 'Fixed handmade synthetic fixture',
                'extractedBy': 'Synthetic author', 'extractedUtc': '2026-02-01T00:00:00Z',
                'category': 'Document', 'confidentiality': 'Restricted', 'note': 'No real material',
                'contentBase64': base64.b64encode(raw).decode()}
        preview = asyncio.run(intake.preview_input(CID, Body(body), ctx))
        receipt = asyncio.run(intake.commit_input(CID, Body({**body, 'requestDigest': preview['requestDigest'], 'confirmed': True}), ctx))
        require(receipt['sourceSha256'] == RAW_SHA and receipt['caseId'] == CID, 'registration')
        context = json.loads(api.context(CID, ctx).body)
        sources = [s for s in context['sources'] if s['evidenceId'] == receipt['evidenceId']]
        require(len(sources) == 1, 'registered_source')
        draft = graph(receipt['evidenceId'])
        pb, expected = api.validate_body({'draft': draft, 'expectedSources': sources}, preview=True)
        p = api.preview_sync(ctx, CID, pb, expected)
        require(p['persisted'] is False and p['validation']['nodes'][0]['isPresumptive'] is True, 'preview')
        with db.session() as s:
            require(all(s.query(m).count() == 0 for m in (EcfcWorksheetRow, EcfcAuditRow, EcfcRequestRow)), 'preview_wrote')
        sb, expected = api.validate_body({'draft': draft, 'expectedSources': sources,
            'requestId': '00000000-0000-4000-8000-000000000001', 'expectedDigest': None,
            'acknowledgeArchiveLimitation': True})
        saved = api.save_sync(ctx, CID, sb, expected)
        reopened_response = api.get_draft(CID, ctx)  # Opens a new real DB session.
        require(reopened_response.status_code == 200, 'reopen_status')
        reopened = json.loads(reopened_response.body)
        require(saved['document'] == reopened['document'] and reopened['sourceStatus'] == 'unchanged', 'reopen_identity')
        doc = reopened['document']; require(doc['revision'] == 1 and doc['draft'] == draft, 'saved_graph')
        denied = api.get_draft(CID, Ctx(role='Investigator', operator='Synthetic denied', request=request))
        require(denied.status_code == 403, 'original_policy_denial')
        with db.session() as s:
            require(tuple(s.query(m).count() for m in (EcfcWorksheetRow, EcfcAuditRow, EcfcRequestRow)) == (1, 1, 1), 'saved_counts')
            event = s.scalars(select(EcfcAuditRow).where(EcfcAuditRow.case_id == CID)).one()
            require(api.validate_event(event.doc, CID, 1)['after'] == doc, 'saved_audit')
        # Local test-host association only, derived AFTER genuine save/reopen and registration.
        # No product resolver or frontend callback is installed.
        binding = {'caseId': CID, 'revision': doc['revision'], 'digest': doc['digest'],
                   'edge': deepcopy(doc['draft']['edges'][0]), 'receipt': deepcopy(receipt)}
        with WRITE_LOCK:
            with db.session() as s:
                api.begin(s, write=True)
                current = s.get(EcfcWorksheetRow, CID).doc
                api.validate_document(current, CID)
                latest = s.scalars(select(EcfcAuditRow).where(EcfcAuditRow.case_id == CID)
                                   .order_by(EcfcAuditRow.revision.desc()).limit(1)).one()
                require(api.validate_event(latest.doc, CID, latest.revision)['after'] == current, 'current_audit')
                require(api.check_document_sources(s, ctx, CID, current) == 'unchanged', 'current_sources')
                require(current['revision'] == binding['revision'] and current['digest'] == binding['digest']
                        and current['draft']['edges'] == [binding['edge']], 'binding_changed')
                got, content = intake._read_original_for_access(ctx, s, CID, receipt['requestDigest'],
                    'Synthetic explicit open of saved ECFC association')
                require(all(got[k] == receipt[k] for k in ('caseId', 'evidenceId', 'requestDigest', 'sourceSha256')), 'pin')
                require(content == raw and content[97:121].decode() == '2026-02-01T12:01:49.000Z', 'excerpt')
        with db.session() as s:
            require(s.query(CustodyEventRow).filter_by(kind='Access').count() == 1, 'access_count')
            require(s.get(EcfcWorksheetRow, CID).doc == doc, 'read_changed_graph')
            require(verify_chain(all_lines(s, CID))['valid'], 'access_audit_chain')
        print(json.dumps({'phase': 'real_save_reopen_and_read', 'passed': True, 'syntheticOnly': True,
                          'revision': 1, 'access': 1, 'productBinding': False, 'seekAvailable': False}))
    finally:
        db.engine.dispose()


def main():
    require(sys.flags.isolated and not sys.flags.optimize, 'Use Python -I -B without -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--dotnet', type=Path)
    args = parser.parse_args()
    require(not args.run or args.dotnet and args.dotnet.is_absolute() and args.dotnet.is_file(), 'run_requires_absolute_dotnet')
    with tempfile.TemporaryDirectory(prefix='ecfc-direct-acceptance-') as folder:
        root = Path(folder)
        raw = materialize(args.repo.resolve(), root)
        api, intake = load_modules(root)
        # Genuine pure input validation only; this is not a saved graph or a core result.
        draft = graph('EV-001')
        api.validate_body({'draft': draft, 'expectedSources': [{'evidenceId': 'EV-001', 'title': 'Synthetic', 'sha256': RAW_SHA}]}, preview=True)
        print(json.dumps({'phase': 'preflight', 'passed': True, 'databaseCreated': False, 'coreRun': False,
                          'dependencies': {n: importlib.metadata.version(n) for n in ('SQLAlchemy', 'fastapi', 'jsonschema')}}), flush=True)
        if not args.run:
            print('PENDING: real core, registration, preview/save/reopen and Access; use explicit --run --dotnet')
            return
        os.environ.update(MCIS_DOTNET=str(args.dotnet), DOTNET_CLI_TELEMETRY_OPTOUT='1',
                          DOTNET_NOLOGO='1', DOTNET_CLI_HOME=str(root / 'cli-home'), NuGetAudit='false',
                          RestoreSources=str(root / 'empty-feed'))
        (root / 'empty-feed').mkdir(); (root / 'cli-home').mkdir()
        require(subprocess.check_output([str(args.dotnet), '--version'], text=True).strip() == '8.0.428', 'sdk_version')
        api.run_core({'action': 'validate', 'draft': {'scope': 'Synthetic smoke', 'nodes': [], 'edges': []}})
        out = root / 'tools/mcis-ecfc/out'
        manifest = json.loads((out / 'build-manifest.json').read_text())
        require(manifest['sdk'] == '8.0.428' and manifest['contract'] == 'mcis-ecfc-build/1', 'manifest')
        require(manifest['recipeSha256'] == hashlib.sha256((root / 'tools/mcis-ecfc/build.py').read_bytes()).hexdigest(), 'recipe')
        for path, digest in manifest['inputs'].items():
            require(path in CORE and hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, 'core_input')
        require(set(manifest['inputs']) == set(CORE) - {'tools/mcis-ecfc/mcis-ecfc.sh', 'tools/mcis-ecfc/build.py'}, 'core_input_set')
        require(bool(manifest['artifacts']), 'core_artifacts')
        for name, digest in manifest['artifacts'].items():
            require(Path(name).name == name and hashlib.sha256((out / name).read_bytes()).hexdigest() == digest, 'core_artifact')
        print('PASS: genuine core smoke; now creating fresh synthetic SQLite', flush=True)
        exercise(root, api, intake, raw)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # No raw subprocess logs, identities, paths or snippets emitted by this harness.
        print(json.dumps({'passed': False, 'errorType': type(exc).__name__,
                          'code': getattr(exc, 'code', 'ACCEPTANCE_BLOCKED_OR_FAILED')}), file=sys.stderr)
        raise SystemExit(1)
