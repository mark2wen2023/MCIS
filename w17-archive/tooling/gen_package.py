"""Build a synthetic 1.4 .mcase using populate/exported/client_at from the pinned worktree tests. Source DB only; not the target store."""
import hashlib, json, sys
from pathlib import Path
REPO = Path('/workspace/mcis-w17-archive-d40e3b5')
sys.path.insert(0, str(REPO/'service'))
from tests.test_bounded_timeline_archive_increment import populate, exported
from tests.test_working_record_archive import client_at
from mcis_service.package.mcase import read_zip
from mcis_service.timeline.models import TimelineEventRow
from sqlalchemy import select

src = Path('/workspace/mcis-w17-archive-report/source-db')
out = Path('/workspace/mcis-w17-archive-report/fixtures/synthetic-1.4.mcase')
meta_path = Path('/workspace/mcis-w17-archive-report/fixtures/expected.json')
src.mkdir(parents=True, exist_ok=True)
with client_at(src, True) as a:
    report = populate(a)
    with a.app.state.db.session() as s:
        ev = [{'eventId': r.key, 'title': r.doc.get('title'), 'timeSec': r.doc.get('timeSec'), 'kind': r.doc.get('kind')}
              for r in s.scalars(select(TimelineEventRow).where(TimelineEventRow.case_id=='CASE-INTAKE').order_by(TimelineEventRow.key))]
    raw = exported(a)
    manifest = json.loads(read_zip(raw)['manifest.json'])
sha = hashlib.sha256(raw).hexdigest()
assert manifest.get('packageVersion')=='1.4.0', manifest
assert len(ev)==2, ev
out.write_bytes(raw)
meta = {
    'caseId': manifest.get('caseId') or 'CASE-INTAKE',
    'packageVersion': manifest['packageVersion'],
    'sourceSha256': sha,
    'byteLength': len(raw),
    'manifestKeys': sorted(manifest),
    'manifest': {k: manifest[k] for k in manifest if k in ('caseId','packageVersion','createdAtUtc','generatorVersion','profile','schemaVersion','title') or isinstance(manifest[k], (str,int,float,bool,type(None)))},
    'events': ev,
    'reportId': report.get('reportId') if isinstance(report, dict) else None,
    'packagePath': str(out),
}
meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(meta, ensure_ascii=False, indent=2))
