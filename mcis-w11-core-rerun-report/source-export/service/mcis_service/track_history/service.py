from sqlalchemy import select
from ..working_records_archive.models import ArchiveImportHistoryRow
from ..working_records_archive.validation import fail,canonical
from ..reports.access import require_content
from ..common.context import problem
from .models import LocalReceipt

def entries(s,cid):return s.scalars(select(ArchiveImportHistoryRow).where(ArchiveImportHistoryRow.case_id==cid,ArchiveImportHistoryRow.kind=='track-intake')).all()
def archived(s,cid,digest):return s.get(ArchiveImportHistoryRow,(cid,'track-intake',digest))
def historical():raise problem(409,'ARCHIVE_HISTORY_ONLY','该航迹导入仅为归档历史，不是本次保存回执')
def local(s,cid,digest):return s.get(LocalReceipt,(cid,digest))
def active_gate(ctx,s,cid,digest):
    h=archived(s,cid,digest);p=local(s,cid,digest)
    if h is not None:
        require_content(s,cid,ctx.role)
        if p is not None:fail('历史与本地来源标记冲突','ARCHIVE_HISTORY_INTEGRITY',409)
        historical()
    return p

def reserved(s,cid):
    ids=set()
    for row in entries(s,cid):
        m=row.doc['metadata'];ids.update((m['sourceEvidenceId'],m['reportEvidenceId']))
    for row in s.scalars(select(LocalReceipt).where(LocalReceipt.case_id==cid)):ids.update((row.source_evidence_id,row.report_evidence_id))
    return ids

def evidence_archived(s,cid,eid):return any(eid in (r.doc['metadata']['sourceEvidenceId'],r.doc['metadata']['reportEvidenceId'])for r in entries(s,cid))

def collect_export(s,cid,files):
    from .validation import collect
    result=collect(files,cid);index={e['key']:e for e in result}
    historical_rows={r.key:r.doc for r in entries(s,cid)}
    for h,d in historical_rows.items():
        if h not in index or canonical(index[h])!=canonical(d):fail('历史航迹索引与原件不一致')
    for p in s.scalars(select(LocalReceipt).where(LocalReceipt.case_id==cid)):
        if p.preview_digest in historical_rows:fail('历史与本地来源标记冲突')
        entry=index.get(p.preview_digest)
        if entry is None:fail('本地航迹来源标记孤立')
        m=entry['metadata']
        if (p.source_evidence_id,p.report_evidence_id,p.report_sha256)!=(m['sourceEvidenceId'],m['reportEvidenceId'],m['reportSha256']):fail('本地航迹来源标记不一致')
    return result

def read(ctx,s,cid,h):
    from fastapi import HTTPException
    try:return _read(ctx,s,cid,h)
    except HTTPException as exc:
        if exc.status_code in (403,404,409,413):raise
        fail('历史航迹索引或原件不一致','ARCHIVE_HISTORY_INTEGRITY',409)
    except (KeyError,TypeError,ValueError,UnicodeError,RecursionError):fail('历史航迹索引或原件不一致','ARCHIVE_HISTORY_INTEGRITY',409)

def _read(ctx,s,cid,h):
    from ..cases.service import load_case
    from ..interviews.access import source
    from ..working_records_archive.service import read_blob
    from ..package_intake.parser import strict_json
    from hashlib import sha256
    require_content(s,cid,ctx.role);load_case(s,cid)
    row=archived(s,cid,h)
    if row is None:raise problem(404,'HISTORY_NOT_FOUND','没有可读取的航迹历史')
    if local(s,cid,h)is not None:fail('历史来源标记冲突','ARCHIVE_HISTORY_INTEGRITY',409)
    m=row.doc['metadata'];raws=[]
    from ..working_records_archive.validation import exact
    exact(m,{'vesselId','sourceEvidenceId','reportEvidenceId','sourceSha256','reportSha256','sourceRelativePath','reportRelativePath','record'})
    if m['sourceRelativePath']!=f'raw/track-imports/{h}/source.csv'or m['reportRelativePath']!=f'raw/track-imports/{h}/report.json':fail('历史路径不一致','ARCHIVE_HISTORY_INTEGRITY',409)
    for prefix,limit in(('source',1024*1024),('report',256*1024)):
        from ..evidence.models import EvidenceRow
        if s.scalar(select(EvidenceRow).where(EvidenceRow.case_id==cid,EvidenceRow.key==m[prefix+'EvidenceId']))is None:fail('历史登记缺失','ARCHIVE_HISTORY_INTEGRITY',409)
        item=source(s,cid,ctx.role,m[prefix+'EvidenceId'])
        raw=read_blob(ctx.settings.blob_dir,cid,m[prefix+'RelativePath'],limit)
        if item['caseId']!=cid or item['relativePath']!=m[prefix+'RelativePath']or item['sha256']!=m[prefix+'Sha256']or sha256(raw).hexdigest()!=m[prefix+'Sha256']:fail('历史原件完整性异常','ARCHIVE_HISTORY_INTEGRITY',409)
        raws.append(raw)
    if canonical(strict_json(raws[1]))!=canonical(m['record']):fail('历史原件记录不一致','ARCHIVE_HISTORY_INTEGRITY',409)
    summary={'caseId':cid,'vesselId':m['vesselId'],'digest':h,'mode':'archive-only','sourceEvidenceId':m['sourceEvidenceId'],'reportEvidenceId':m['reportEvidenceId'],'sourceSha256':m['sourceSha256'],'reportSha256':m['reportSha256'],'pointCount':m['record']['receipt']['pointCount'],'identityMode':'unverified-self-reported'}
    return summary,raws
