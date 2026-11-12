"""Bounded, closed-world working-record archive assembly/restoration."""
from pathlib import Path
import hashlib,os,stat
from sqlalchemy import select,inspect,text as sqltext
from ..db import put_doc
from ..common.context import problem
from ..reports.access import require_content
from ..interviews.access import document as protect_interview,source as protect_source
from ..cases.models import CaseRow
from ..interviews.models import InterviewRow
from ..reports.models import ReportRow,ReportAuditRow
from ..evidence.models import EvidenceRow,CustodyEventRow
from ..manual_interviews.models import InterviewRequestReceiptRow
from .models import ArchivedManualReceiptRow,ArchiveImportHistoryRow,ArchiveArtifactRow
from .validation import PATH,FORMAT,MAX_BYTES,canonical,fail,sha

ALLOWED_TABLES={'cases','vessels','track_points','evidence_items','custody_events','audit_events','environment_observations',
'access_policies','interviews','investigation_reports','report_operation_snapshots','interview_request_receipts',
'archived_manual_interview_receipts','archive_import_history','archive_historical_artifacts','package_intake_receipts',
'hfacs_worksheets','hfacs_worksheet_audit','hfacs_worksheet_requests','hfacs_archived_requests'}
GLOBALS={'knowledge_cards','knowledge_audit','sqlite_sequence'}


def read_blob(root,case_id,rel,limit=MAX_BYTES):
    p=Path(root)/case_id/rel;current=Path(root)
    if current.is_symlink():fail('历史文件路径异常','ARCHIVE_HISTORY_INTEGRITY',409)
    for part in p.relative_to(current).parts:
        if part in ('..','.')or '\\'in part:fail()
        current=current/part
        if current.is_symlink():fail('历史文件路径异常','ARCHIVE_HISTORY_INTEGRITY',409)
    try:
        fd=os.open(p,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
        with os.fdopen(fd,'rb')as f:
            if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):raise ValueError()
            raw=f.read(limit+1)
    except (OSError,ValueError):fail('历史原件缺失或不可读取','ARCHIVE_HISTORY_INTEGRITY',409)
    if len(raw)>limit:fail('历史原件超过单成员16MiB预算，未截断','ARCHIVE_BUDGET',413)
    return raw


def reject_unsupported_tables(s,case_id):
    # Inspect actual database tables, not the incomplete models_registry alone.
    inspector=inspect(s.connection())
    for name in inspector.get_table_names():
        if name in ALLOWED_TABLES or name in GLOBALS:continue
        cols={c['name']for c in inspector.get_columns(name)}
        quoted='"'+name.replace('"','""')+'"'
        where=' WHERE case_id=:cid'if 'case_id'in cols else''
        if s.execute(sqltext('SELECT 1 FROM '+quoted+where+' LIMIT 1'),{'cid':case_id}).first():
            fail('存在未支持的业务状态，不能部分归档')


def full_access(s,ctx,case_id):
    require_content(s,case_id,ctx.role)
    for r in s.scalars(select(InterviewRow).where(InterviewRow.case_id==case_id)):protect_interview(s,ctx,r.doc)
    for r in s.scalars(select(EvidenceRow).where(EvidenceRow.case_id==case_id)):protect_source(s,case_id,ctx.role,r.key)


def has_history(s,case_id):
    models=(InterviewRow,ReportRow,ReportAuditRow,InterviewRequestReceiptRow,ArchivedManualReceiptRow,ArchiveImportHistoryRow,ArchiveArtifactRow)
    for model in models:
        if s.scalars(select(model).where(model.case_id==case_id).limit(1)).first()is not None:return True
    from ..package_intake.router import IntakeReceipt
    if s.scalars(select(IntakeReceipt).where(IntakeReceipt.case_id==case_id)).first()is not None:return True
    from ..evidence_intake.parser import PREFIX
    return s.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id==case_id,CustodyEventRow.kind=='Register',CustodyEventRow.detail.startswith(PREFIX)).limit(1)).first()is not None


def build(s,root,ctx,case_id):
    from ..package.mcase import build_files,CASE_FIELDS,CASE_EXT_FIELDS
    from ..package_intake.router import IntakeReceipt
    from ..package_intake.parser import strict_json
    from ..evidence_intake.parser import PREFIX
    full_access(s,ctx,case_id);reject_unsupported_tables(s,case_id)
    c=s.scalars(select(CaseRow).where(CaseRow.case_id==case_id)).first()
    if c is None:raise problem(404,'CASE_NOT_FOUND','案件不存在')
    if 'incidentTimeUtc'not in c.doc or 'caseEpochUtc'not in c.doc:fail('案件时间基础字段缺失，不能构造可恢复包')
    if set(c.doc)-set(CASE_FIELDS)-set(CASE_EXT_FIELDS):fail('案件含未支持字段，不能静默丢失')
    data={'format':FORMAT,'version':1,'caseId':case_id,'receiptPolicy':'archive-only-on-import',
          'interviews':[],'reports':[],'reportSnapshots':[],'manualReceipts':[],'importHistory':[],'historicalArtifacts':[],'lineage':{'nodes':[]}}
    for model,key in ((InterviewRow,'interviews'),(ReportRow,'reports'),(ReportAuditRow,'reportSnapshots')):
        for r in s.scalars(select(model).where(model.case_id==case_id).order_by(model.key)):
            data[key].append({'key':r.key,'createdUtc':r.created_utc,'updatedUtc':r.updated_utc,'doc':r.doc})
    receipts={}
    for r in s.scalars(select(InterviewRequestReceiptRow).where(InterviewRequestReceiptRow.case_id==case_id)):
        receipts[r.request_id]={k:getattr(r,k)for k in ('case_id','request_id','operation','record_id','request_digest','operator','role','receipt')}
    for r in s.scalars(select(ArchivedManualReceiptRow).where(ArchivedManualReceiptRow.case_id==case_id)):
        if r.request_id in receipts:fail('当前与历史请求标识冲突')
        receipts[r.request_id]=r.doc
    data['manualReceipts']=[receipts[k]for k in sorted(receipts)]
    # Reject malformed/incomplete business records before touching source bytes.
    from .validation import rows,report_graph,snapshots,manual_receipts
    from ..audit.service import all_lines
    rows(data['interviews'],'interview','recordId',case_id,128)
    report_docs=rows(data['reports'],'report','reportId',case_id,256)
    report_graph(report_docs);snapshots(data['reportSnapshots'],report_docs,all_lines(s,case_id),case_id)
    manual_receipts(data['manualReceipts'],case_id)
    histories={};artifacts={};nodes={};files=build_files(s,root,case_id)
    for p in list(files):
        if p.startswith('testimony/'):del files[p] # originals exist ONLY in authoritative extension
    for r in s.scalars(select(ArchiveImportHistoryRow).where(ArchiveImportHistoryRow.case_id==case_id)):
        histories[(r.kind,r.key)]=r.doc
    for r in s.scalars(select(ArchiveArtifactRow).where(ArchiveArtifactRow.case_id==case_id)):
        artifacts[r.sha256]=r.doc;nodes[r.sha256]=r.parents
        files[r.doc['relativePath']]=read_blob(root,case_id,r.doc['relativePath'])
    current=s.scalars(select(IntakeReceipt).where(IntakeReceipt.case_id==case_id)).all()
    if len(current)>1:fail()
    for r in current:
        h=r.key;sha(h);raw=read_blob(root,case_id,'_package_intake/source.mcase')
        if hashlib.sha256(raw).hexdigest()!=h or r.doc.get('sourceSha256')!=h or r.doc.get('byteLength')!=len(raw)or r.doc.get('caseId')!=case_id:fail('原包与当前导入记录不一致','ARCHIVE_HISTORY_INTEGRITY',409)
        if ('package-intake',h)in histories:fail('当前导入与已归档请求重复')
        parents=sorted(set(nodes)-{p for ps in nodes.values()for p in ps})
        if h in nodes and nodes[h]!=parents:fail()
        nodes[h]=parents;rel='history/artifacts/'+h+'.bin'
        artifacts[h]={'sha256':h,'sizeBytes':len(raw),'relativePath':rel,'mediaType':'application/octet-stream'};files[rel]=raw
        histories[('package-intake',h)]={'kind':'package-intake','caseId':case_id,'key':h,'createdUtc':r.created_utc,'updatedUtc':r.updated_utc,'metadata':r.doc,'sourceArtifactSha256':h}
    for r in s.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id==case_id,CustodyEventRow.kind=='Register',CustodyEventRow.detail.startswith(PREFIX))):
        d=strict_json(r.detail[len(PREFIX):].encode());h=d.get('requestDigest');sha(h)
        key=('evidence-intake',h)
        entry={'kind':'evidence-intake','caseId':case_id,'key':h,'createdUtc':None,'updatedUtc':None,'sourceArtifactSha256':None,
            'metadata':{'custodySeq':r.seq,'evidenceId':r.evidence_id,'requestDigest':h,'binding':d['binding'],'sourceSha256':r.sha256,'relativePath':'raw/evidence-intakes/'+h+'/source.bin'}}
        if key in histories and histories[key]!=entry:fail('证据历史禁用索引与原始登记链不一致')
        histories[key]=entry
    data['importHistory']=[histories[k]for k in sorted(histories)]
    data['historicalArtifacts']=[artifacts[k]for k in sorted(artifacts)]
    data['lineage']={'nodes':[{'artifactSha256':k,'parentArtifactSha256s':nodes[k]}for k in sorted(nodes)]}
    # Every actual per-case file must be explicitly retained, including operational source bytes.
    allowed=set(files)|({'_package_intake/source.mcase'}if current else set())
    case_root=Path(root)/case_id
    if case_root.is_symlink():fail()
    if case_root.exists():
        for p in case_root.rglob('*'):
            if p.is_symlink()or not(p.is_dir()or p.is_file()):fail('案件目录有未支持的文件类型')
            if p.is_file()and p.relative_to(case_root).as_posix()not in allowed:fail('存在未支持的案件文件，不能静默丢失')
    files[PATH]=canonical(data)
    return files,data


def restore(s,root,validated,files):
    from ..evidence.service import blob_path
    data=validated.data;cid=data['caseId']
    for model,key in ((InterviewRow,'interviews'),(ReportRow,'reports'),(ReportAuditRow,'reportSnapshots')):
        for r in data[key]:
            row=model(case_id=cid,key=r['key'],doc=r['doc'],created_utc=r['createdUtc'],updated_utc=r['updatedUtc']);s.add(row)
    for r in data['manualReceipts']:
        s.add(ArchivedManualReceiptRow(case_id=cid,request_id=r['request_id'],record_id=r['record_id'],doc=r))
    for h in data['importHistory']:
        s.add(ArchiveImportHistoryRow(case_id=cid,kind=h['kind'],key=h['key'],evidence_id=h['metadata']['evidenceId']if h['kind']=='evidence-intake'else None,doc=h))
    nodes={n['artifactSha256']:n['parentArtifactSha256s']for n in data['lineage']['nodes']}
    for a in data['historicalArtifacts']:
        s.add(ArchiveArtifactRow(case_id=cid,sha256=a['sha256'],doc=a,parents=nodes[a['sha256']]))
        p=blob_path(root,cid,a['relativePath']);p.parent.mkdir(parents=True,exist_ok=True)
        with open(p,'xb')as f:f.write(files[a['relativePath']])
    s.flush()


def archived_evidence(s,case_id,evidence_id=None,digest=None):
    q=select(ArchiveImportHistoryRow).where(ArchiveImportHistoryRow.case_id==case_id,ArchiveImportHistoryRow.kind=='evidence-intake')
    if evidence_id is not None:q=q.where(ArchiveImportHistoryRow.evidence_id==evidence_id)
    if digest is not None:q=q.where(ArchiveImportHistoryRow.key==digest)
    return s.scalars(q).first()


def historical_only():raise problem(409,'ARCHIVE_HISTORY_ONLY','这是只读历史记录，不作为本次成功请求或活跃凭证')
