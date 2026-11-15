"""Offline conflict boundary inspection; never a restorable ParsedPackage or HTTP route."""
from dataclasses import dataclass
import hashlib
import re
from ..common import contracts
from ..package.mcase import PACKAGE_FORMAT, CASE_FIELDS, CASE_EXT_FIELDS, infer_role
from ..package_intake.parser import read_bounded, safe_path, strict_json
from ..redaction.policy import default_policy
from . import conflicts
from .validation import canonical

# Experimental envelope tag, not an allocated supported .mcase version.
VERSION = '1.5.0-draft.conflicts.1'
PATH = 'conflicts/records.v1.json'
MIRROR = 'analysis/time-alignment.json'
REQUIRED = {'manifest.json','case.json','case.ext.json','vessels.json',
            'evidence/index.json','audit/audit.jsonl','audit/custody.jsonl',
            'access-policy.json',PATH,MIRROR}
EMPTY = {'analysis/timeline.json':{'events':[]}, 'analysis/colreg.json':{},
         'recommendations.json':[], 'consultation/rounds.json':[], 'agents/drafts.json':[]}


@dataclass(frozen=True)
class BoundaryInspection:
    case_id: str
    envelope_sha256: str
    record_count: int
    revision_count: int
    unknown_history_count: int
    restore_ready: bool = False


def inspect_envelope(raw, *, expected_sha256):
    """Inspect exact supplied ZIP bytes. Declared checksum is not authentication.

    No filesystem publication/DB mutation; result intentionally cannot be restored.
    """
    try:
        return _inspect(raw, expected_sha256)
    except conflicts.ConflictArchiveInvalid:
        raise
    except Exception as exc:
        raise conflicts.ConflictArchiveInvalid('invalid conflict envelope/dependencies') from exc


def _inspect(raw, expected_sha256):
    require = conflicts.require
    require(isinstance(raw,bytes) and isinstance(expected_sha256,str) and re.fullmatch('[0-9a-f]{64}',expected_sha256), 'envelope type/checksum')
    require(len(raw) <= 32*1024*1024 and hashlib.sha256(raw).hexdigest()==expected_sha256,'envelope checksum/budget')
    files = read_bounded(raw)
    require(REQUIRED <= files.keys(), 'missing required member')
    manifest = strict_json(files['manifest.json'])
    require(isinstance(manifest,dict) and set(manifest)=={'packageFormat','packageVersion','caseId','createdAtUtc','lastModifiedAtUtc','generatorVersion','files'},'manifest fields')
    require(manifest['packageFormat']==PACKAGE_FORMAT and manifest['packageVersion']==VERSION,'experimental envelope version')
    for field in ('createdAtUtc','lastModifiedAtUtc'):conflicts.stamp(manifest[field])
    require(isinstance(manifest['generatorVersion'],str),'generator declaration')
    require(isinstance(manifest['files'],list),'manifest inventory')
    listed = set()
    for entry in manifest['files']:
        require(isinstance(entry,dict) and set(entry)=={'relativePath','role','sizeBytes','sha256'},'manifest entry')
        path = safe_path(entry['relativePath'])
        require(path not in listed and path!='manifest.json' and path in files,'missing/duplicate inventory member')
        require(entry['role']==infer_role(path),'member role')
        require(type(entry['sizeBytes']) is int and entry['sizeBytes']==len(files[path]) and entry['sha256']==hashlib.sha256(files[path]).hexdigest(),'member size/digest')
        listed.add(path)
    require(listed==files.keys()-{'manifest.json'},'unlisted member')
    case = strict_json(files['case.json']); ext = strict_json(files['case.ext.json'])
    require(isinstance(case,dict) and set(case)==set(CASE_FIELDS) and isinstance(ext,dict) and set(ext)<=set(CASE_EXT_FIELDS),'case shape')
    case = {**case,**ext};contracts.validate('case',case)
    cid = case['caseId']
    require(cid==manifest['caseId'] and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,63}',cid),'case identity')
    require(case['schemaVersion']=='1.0.0' and -840<=case['displayTimeZoneOffsetMinutes']<=840 and case.get('durationSec',0)>=0,'case version/time range')
    require(strict_json(files['access-policy.json'])==default_policy(),'unsupported policy')
    vessels = strict_json(files['vessels.json']); require(isinstance(vessels,list),'vessel list')
    vessel_ids = set()
    for vessel in vessels:
        contracts.validate('vessel',vessel)
        require(vessel['caseId']==cid and vessel['vesselId'] not in vessel_ids,'vessel identity')
        vessel_ids.add(vessel['vesselId'])
    evidence = strict_json(files['evidence/index.json']); require(isinstance(evidence,list),'evidence list')
    evidence_by_id = {}; paths = set()
    for doc in evidence:
        contracts.validate('evidence-item',doc)
        eid = doc['evidenceId']; path = safe_path(doc['relativePath'])
        require(doc['caseId']==cid and eid not in evidence_by_id and path.startswith('raw/') and path not in paths,'evidence identity/path')
        require(path in files and hashlib.sha256(files[path]).hexdigest()==doc['sha256'],'packaged evidence bytes/digest')
        evidence_by_id[eid] = doc;paths.add(path)
    allowed = REQUIRED | paths
    for path,empty in EMPTY.items():
        if path in files:
            require(strict_json(files[path])==empty,'unsupported business content')
            allowed.add(path)
    require(files.keys()==allowed,'unsupported members/profile combination')

    def lines(path):
        text = files[path].decode('utf-8')
        result = text.split('\n')
        if result[-1]=='':result.pop()
        return result
    audit_lines = lines('audit/audit.jsonl'); custody_lines = lines('audit/custody.jsonl')
    custody = conflicts.chain(custody_lines,cid)
    registered = set(); current = {}
    from ..evidence_intake.parser import PREFIX
    require(not any(PREFIX in line for line in custody_lines),'unsupported active intake history')
    for row,_ in custody.values():
        eid = row.get('evidence_id');require(eid in evidence_by_id,'custody evidence')
        doc = evidence_by_id[eid];action = row['action']
        if action=='custody.register':
            require(eid not in registered,'duplicate registration');registered.add(eid)
            for src,dst in (('sha256','sha256'),('path','relativePath'),('title','title'),('source','source'),('extracted_by','extractedBy'),('extracted_utc','extractedUtc')):
                require(row.get(src,'')==doc.get(dst,''),'registration metadata mismatch')
            require(row.get('confidentiality','Normal')==doc['confidentiality'],'registration confidentiality')
            current[eid] = doc['sha256']
        else:
            require(eid in registered,'custody before registration')
            if action=='custody.change': current[eid]=row.get('sha256')
    require(registered==evidence_by_id.keys(),'missing registration')
    require(all(current[eid]==doc['sha256'] for eid,doc in evidence_by_id.items()),'replaced-original history unsupported')
    member = conflicts.parse(files[PATH],case_id=cid,evidence=evidence,audit_lines=audit_lines,
                             custody_lines=custody_lines,vessel_ids=vessel_ids)
    mirror = strict_json(files[MIRROR])
    require(canonical(mirror)==canonical({'conflicts':[r['doc'] for r in member['records']]}),'conflict mirror mismatch')
    return BoundaryInspection(cid,expected_sha256,len(member['records']),
        sum(len(r['revisions']) for r in member['records']),
        sum(r['coverage']=='unknown-before-capture' for r in member['records']))
