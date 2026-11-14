"""First registration of a supplied opaque file; SQLite/file crash ACID is not promised."""
import json
import os
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from ..cases.service import load_case
from ..common import contracts
from ..common.context import Ctx, CtxDep, problem
from ..common.timeutil import iso, now_utc
from ..db import WRITE_LOCK, put_doc
from ..evidence import service as evidence
from ..evidence.models import EvidenceRow, CustodyEventRow
from ..redaction.gateway import require, filter_evidence, get_policy, level_of
from .parser import (PROFILE, VERSION, PREFIX, MAX_BODY, MAX_BYTES, SAFE_ID, DIGEST,
                     canonical, sha, inputs, preview, text)

from ..reports.access import NoStoreRoute
router=APIRouter(prefix='/api/v1/cases/{case_id}',tags=['evidence-intake'],route_class=NoStoreRoute)


def authorize(ctx,s,case_id,*,write=False):
    if ctx.role not in ('Investigator','LeadInvestigator'):
        raise problem(403,'FORBIDDEN','本登记原件仅调查组可访问')
    if not SAFE_ID.fullmatch(case_id): raise problem(422,'CASE_ID','案件编号不适用于本登记切片')
    load_case(s,case_id)
    level=require(ctx,s,case_id,'evidence_meta',write=write)
    policy=get_policy(s,case_id)
    if level not in ('ReadOnly','ReadWrite') or level_of(policy,ctx.role,'testimony') not in ('ReadOnly','ReadWrite'):
        raise problem(403,'FORBIDDEN','本原件登记路径不提供脱敏视图，须具有完整读取权限')
    if not filter_evidence([{'confidentiality':'Restricted'}],ctx.role,get_policy(s,case_id)):
        raise problem(403,'FORBIDDEN','当前策略不允许访问受限原件')


async def body_bounded(request):
    if request.headers.get('content-type','').split(';')[0].strip().lower()!='application/json':
        raise problem(415,'CONTENT_TYPE','仅接受application/json')
    data=bytearray()
    async for chunk in request.stream():
        if len(data)+len(chunk)>MAX_BODY: raise problem(413,'INTAKE_REQUEST_LIMIT','本切片请求体工程上限为12MiB')
        data.extend(chunk)
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d: raise ValueError('duplicate key')
            d[k]=v
        return d
    try:
        return json.loads(data.decode('utf-8',errors='strict'),object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError,UnicodeError,RecursionError):
        raise problem(422,'INTAKE_JSON','请求必须为无重复键的有效UTF-8 JSON')


def rel_for(digest):
    if not isinstance(digest,str) or not DIGEST.fullmatch(digest): raise problem(422,'INTAKE_DIGEST','摘要格式无效')
    return f'raw/evidence-intakes/{digest}/source.bin'


def file_path(ctx,case_id,rel):
    root=ctx.settings.blob_dir.resolve(); path=root/case_id/rel; current=root
    for part in path.relative_to(root).parts:
        current=current/part
        if current.is_symlink(): raise problem(409,'INTAKE_PATH','原件路径含符号链接，已拒绝')
    return path


def read_file(path):
    # Reject special files, avoid unbounded reads. O_NOFOLLOW closes the leaf-link race.
    import stat
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    with os.fdopen(fd,'rb') as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode): raise ValueError('not regular file')
        raw=f.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES: raise ValueError('file budget')
    return raw


def exclusive_write(path: Path,raw,created):
    path.parent.mkdir(parents=True,exist_ok=True)
    try: fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
    except FileExistsError: raise problem(409,'INTAKE_BLOB_EXISTS','原件路径已存在，不覆盖；请核查先前登记状态')
    created.append(path)
    with os.fdopen(fd,'wb') as f:
        f.write(raw);f.flush();os.fsync(f.fileno())


def load_receipt(ctx,s,case_id,digest):
    from ..working_records_archive.service import archived_evidence,historical_only
    if archived_evidence(s,case_id,digest=digest) is not None:
        from ..reports.access import require_content
        require_content(s,case_id,ctx.role)
        historical_only()
    rel=rel_for(digest)
    rows=s.scalars(select(EvidenceRow).where(EvidenceRow.case_id==case_id,
                           EvidenceRow.doc['relativePath'].as_string()==rel).limit(2)).all()
    # Also discover an orphan Register if its Evidence row disappeared.
    regs=s.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id==case_id,
                    CustodyEventRow.kind=='Register',CustodyEventRow.detail.startswith(PREFIX),
                    CustodyEventRow.detail.contains('"requestDigest":"'+digest+'"')).limit(2)).all()
    if not rows and not regs:
        if file_path(ctx,case_id,rel).exists():
            raise problem(409,'INTAKE_INTEGRITY','仅发现无登记引用的原件；不视为保存成功，也不覆盖')
        return None
    if len(rows)!=1 or len(regs)!=1: raise problem(409,'INTAKE_INTEGRITY','登记记录缺失或重复，不能核对为完整保存')
    item=dict(rows[0].doc);reg=regs[0]
    if not filter_evidence([item],ctx.role,get_policy(s,case_id)): raise problem(403,'FORBIDDEN','受限原件')
    try:
        if len(reg.detail)>32768: raise ValueError('metadata budget')
        saved=json.loads(reg.detail[len(PREFIX):])
        if set(saved)!= {'binding','requestDigest'} or saved['requestDigest']!=digest: raise ValueError('binding')
        binding=saved['binding']
        if binding['profile']!=PROFILE or binding['version']!=VERSION or binding['caseId']!=case_id:
            raise ValueError('profile/case')
        if binding['role'] not in ('Investigator','LeadInvestigator'): raise ValueError('role')
        raw=read_file(file_path(ctx,case_id,rel))
        body={**binding['metadata'],'profile':PROFILE,'fileName':binding['fileName']}
        result,rebuilt=preview(body,raw,case_id,binding['operator'],binding['role'])
        if canonical(rebuilt)!=canonical(binding) or result['requestDigest']!=digest: raise ValueError('digest')
        expected={'caseId':case_id,'evidenceId':reg.evidence_id,'relativePath':rel,'sha256':sha(raw),
                  **binding['metadata']}
        # Existing note edits remain legal; original note is preserved in Register.detail.
        if any(item.get(k)!=v for k,v in expected.items() if k!='note'): raise ValueError('snapshot')
        if rows[0].key!=reg.evidence_id or reg.evidence_id!=item['evidenceId'] or reg.sha256!=sha(raw):
            raise ValueError('identity')
        events=evidence.custody_events(s,case_id,reg.evidence_id)
        if sum(e.kind=='Register' for e in events)!=1 or any(e.kind=='Change' for e in events):
            raise ValueError('register/change')
        if reg.operator!=binding['operator']: raise ValueError('operator')
        expected_line=evidence.custody_line(seq=reg.seq,utc=reg.utc,operator=reg.operator,kind='Register',
             evidence_id=reg.evidence_id,sha256=reg.sha256,previous_sha256='',detail=reg.detail,
             matched=None,prev=reg.prev_line_hash,item=expected)
        if reg.line!=expected_line: raise ValueError('registration line')
        receipt={'caseId':case_id,'evidenceId':item['evidenceId'],'requestDigest':digest,'sourceSha256':sha(raw),
                 'fileName':binding['fileName'],'byteLength':len(raw),'metadata':binding['metadata'],
                 'registeredUtc':reg.utc,'registeredBy':reg.operator,'registeredRole':binding['role'],
                 'evidence':evidence.derive(item,events),'replayed':True}
        return receipt,raw
    except (OSError,ValueError,KeyError,TypeError,UnicodeError,RecursionError,HTTPException):
        raise problem(409,'INTAKE_INTEGRITY','原件或登记快照/绑定信息缺失、篡改或不支持变更；未修复，也未核对为完整保存')


@router.post('/evidence-intakes:preview')
async def preview_input(case_id:str,request:Request,ctx:Ctx=CtxDep):
    with ctx.db.session() as s: authorize(ctx,s,case_id,write=True)
    body=await body_bounded(request);_,raw=inputs(body)
    with ctx.db.session() as s:
        authorize(ctx,s,case_id,write=True)
        return preview(body,raw,case_id,ctx.operator,ctx.role)[0]


@router.post('/evidence-intakes:commit')
async def commit_input(case_id:str,request:Request,ctx:Ctx=CtxDep):
    with ctx.db.session() as s: authorize(ctx,s,case_id,write=True)
    body=await body_bounded(request);meta,raw=inputs(body,commit=True);created=[]
    with WRITE_LOCK:
        try:
            with ctx.db.session() as s:
                authorize(ctx,s,case_id,write=True)
                result,binding=preview(body,raw,case_id,ctx.operator,ctx.role);digest=result['requestDigest']
                if digest!=body['requestDigest']: raise problem(409,'INTAKE_STALE','原件、声明或操作身份变化，请重新预览')
                found=load_receipt(ctx,s,case_id,digest)
                if found:return found[0]
                eid=evidence.next_id(s,case_id);rel=rel_for(digest)
                item={'caseId':case_id,'evidenceId':eid,'relativePath':rel,'sha256':sha(raw),**meta}
                contracts.validate('evidence-item',item)
                put_doc(s,EvidenceRow,case_id,eid,item)
                detail=PREFIX+canonical({'binding':binding,'requestDigest':digest}).decode('utf-8')
                reg=evidence.append_custody(s,case_id=case_id,evidence_id=eid,kind='Register',operator=ctx.operator,
                         role=ctx.role,sha256=sha(raw),detail=detail,item=item)
                exclusive_write(file_path(ctx,case_id,rel),raw,created)
                receipt={'caseId':case_id,'evidenceId':eid,'requestDigest':digest,'sourceSha256':sha(raw),
                    'fileName':body['fileName'],'byteLength':len(raw),'metadata':meta,'registeredUtc':reg.utc,
                    'registeredBy':ctx.operator,'registeredRole':ctx.role,'evidence':evidence.derive(item,[reg]),'replayed':False}
            return receipt
        except BaseException as error:
            failed=False
            for path in reversed(created):
                try:path.unlink()
                except FileNotFoundError:pass
                except OSError:failed=True
            if failed:raise problem(500,'INTAKE_CLEANUP_FAILED','登记未成功，本次原件清理未全部完成；请检查存储，勿视为已登记') from error
            raise


@router.get('/evidence-intakes/{digest}')
def receipt_input(case_id:str,digest:str,ctx:Ctx=CtxDep):
    with ctx.db.session() as s:
        authorize(ctx,s,case_id)
        found=load_receipt(ctx,s,case_id,digest)
        if not found:raise problem(404,'INTAKE_NOT_FOUND','未找到本次摘要的登记回执')
        return found[0]


@router.get('/evidence/{evidence_id}/intake')
def receipt_evidence(case_id:str,evidence_id:str,ctx:Ctx=CtxDep):
    with ctx.db.session() as s:
        authorize(ctx,s,case_id)
        from ..working_records_archive.service import archived_evidence,historical_only
        if archived_evidence(s,case_id,evidence_id=evidence_id) is not None:
            from ..reports.access import require_content
            require_content(s,case_id,ctx.role)
            historical_only()
        item=evidence.load_item(s,case_id,evidence_id)
        if not filter_evidence([item],ctx.role,get_policy(s,case_id)):raise problem(403,'FORBIDDEN','受限原件')
        match=re.fullmatch(r'raw/evidence-intakes/([0-9a-f]{64})/source\.bin',item.get('relativePath',''))
        if not match:
            linked=s.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id==case_id,
                CustodyEventRow.evidence_id==evidence_id,CustodyEventRow.kind=='Register',
                CustodyEventRow.detail.startswith(PREFIX)).limit(1)).first()
            if linked:raise problem(409,'INTAKE_INTEGRITY','本片登记路径已变化，不能核对原件')
            raise problem(404,'INTAKE_NOT_FOUND','该条目不是本片登记，不假定已迁移')
        found=load_receipt(ctx,s,case_id,match.group(1))
        if not found:raise problem(409,'INTAKE_INTEGRITY','登记回执缺失')
        return found[0]


@router.post('/evidence-intakes/{digest}:download')
async def download(case_id:str,digest:str,request:Request,ctx:Ctx=CtxDep):
    with ctx.db.session() as s:authorize(ctx,s,case_id)
    body=await body_bounded(request)
    try:
        if not isinstance(body,dict) or set(body)!={'purpose'}:raise ValueError('fields')
        purpose=text(body['purpose'],1000)
        text(ctx.operator,200,multiline=False)
    except (ValueError,UnicodeError):raise problem(422,'INTAKE_PURPOSE','下载必须提供有效有限长度的访问目的及操作人（操作人不超过200字符且无控制符）')
    with WRITE_LOCK:
        with ctx.db.session() as s:
            from ..reports.access import begin
            begin(s)
            authorize(ctx,s,case_id);found=load_receipt(ctx,s,case_id,digest)
            if not found:raise problem(404,'INTAKE_NOT_FOUND','未找到登记原件')
            receipt,raw=found
            from ..report_output.attachment_access import protect_container
            protect_container(s,case_id,ctx.role,raw)
            evidence.append_custody(s,case_id=case_id,evidence_id=receipt['evidenceId'],kind='Access',
                       operator=ctx.operator,role=ctx.role,sha256=receipt['sourceSha256'],detail=purpose)
        return Response(raw,media_type='application/octet-stream',headers={
             'Content-Disposition':'attachment; filename="source.bin"','X-Sha256':sha(raw),
             'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
