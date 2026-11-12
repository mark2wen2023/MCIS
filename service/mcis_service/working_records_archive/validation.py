"""Strict archive-only validation. Never executes a nested source package."""
from dataclasses import dataclass
from datetime import datetime
import hashlib,json,re,uuid
from urllib.parse import urlsplit,parse_qsl,unquote
from jsonschema import Draft202012Validator
from ..common import contracts
from ..common.context import problem

PATH='working-records/backup.v1.json'
FORMAT='MCIS-WORKING-RECORDS'
PROFILE='MCIS-WORKING-RECORDS-1'
MAX_BYTES=16*1024*1024
HEX=re.compile(r'^[a-f0-9]{64}$')
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')
KEYS={'format','version','caseId','receiptPolicy','interviews','reports','reportSnapshots','manualReceipts','importHistory','historicalArtifacts','lineage'}
STATUSES={'Draft','Confirmed','Modified','Dismissed'}

def fail(message='工作记录归档结构、来源、版本或历史关联无效',code='WORKING_ARCHIVE_INVALID',status=422):
    raise problem(status,code,message)

def exact(obj,keys):
    if not isinstance(obj,dict) or set(obj)!=set(keys):fail()

def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def digest(obj):return hashlib.sha256(canonical(obj)).hexdigest()
def text(v,n=256,empty=False):
    if not isinstance(v,str) or len(v)>n or (not empty and not v) or any(0xd800<=ord(c)<=0xdfff for c in v):fail()
    return v

def sha(v):
    if not isinstance(v,str) or not HEX.fullmatch(v):fail()

def integer(v,lo=0,hi=2**31-1):
    if type(v)is not int or not lo<=v<=hi:fail()

def stamp(v):
    text(v,64)
    try:
        dt=datetime.fromisoformat(v.replace('Z','+00:00'))
        if dt.utcoffset() is None or dt.utcoffset().total_seconds()!=0:fail()
    except ValueError:fail()

def schema(name,obj):
    try:contracts.validate(name,obj)
    except Exception:fail('历史文档不符合已支持字段模式')

def uuid_key(v):
    try:
        if not isinstance(v,str) or str(uuid.UUID(v))!=v:fail()
    except (ValueError,AttributeError):fail()

def rows(entries,name,idfield,case_id,limit):
    if not isinstance(entries,list) or len(entries)>limit:fail('工作记录数量超过工程预算，不截断历史')
    out={}
    for row in entries:
        exact(row,{'key','createdUtc','updatedUtc','doc'})
        text(row['key']);stamp(row['createdUtc']);stamp(row['updatedUtc'])
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',row['key']):fail()
        d=row['doc'];schema(name,d)
        if d.get('caseId')!=case_id or d.get(idfield)!=row['key'] or row['key']in out:fail()
        out[row['key']]=d
    return out

@dataclass(frozen=True)
class ValidatedArchive:
    raw:bytes
    data:dict
    @property
    def summary(self):
        result = {'version':PROFILE if self.data['version']==1 else 'MCIS-WORKING-RECORDS-2','interviewCount':len(self.data['interviews']),'reportCount':len(self.data['reports']),
                'reportSnapshotCount':len(self.data['reportSnapshots']),'manualReceiptCount':len(self.data['manualReceipts']),
                'receiptMode':'archive-only','identityMode':'unverified-self-reported'}
        if self.data['version']==2:result['trackReceiptCount']=sum(h['kind']=='track-intake'for h in self.data['importHistory'])
        return result


def uri(href,page,params):
    text(href,2048)
    if not href.startswith('#/') or '\\'in href or any(ord(c)<32 for c in href) or href.count('#')!=1:fail()
    raw=href[2:];path,sep,query=raw.partition('?')
    if path!=page or not sep or re.search(r'%(?![0-9A-Fa-f]{2})',query):fail()
    try:pairs=parse_qsl(query,keep_blank_values=True,strict_parsing=True,encoding='utf-8',errors='strict')
    except (ValueError,UnicodeError):fail()
    if len(dict(pairs))!=len(pairs) or dict(pairs)!=params:fail('来源链接与原始对象关联不一致')


def citations(d,case_id,evidence,interviews):
    if isinstance(d,list):
        for v in d:citations(v,case_id,evidence,interviews)
    elif isinstance(d,dict):
        if 'citations'in d:
            for c in d['citations']:
                kind=c['kind'];ident=text(c['id']);reg=c['registration']
                if c['unregistered'] is not (reg=='unregistered'):fail()
                ref=c.get('sourceRef','')
                if kind=='evidence':
                    uri(c['href'],'evidence',{'id':ident,'case':case_id})
                    if ref!='evidence/'+ident:fail()
                    if reg=='registered' and ident not in evidence:fail('已登记来源没有被完整纳入归档')
                elif kind=='interview-crosscheck':
                    match=re.fullmatch(r'interviews/([^/]+)/crosscheck/([^/]+)',ref)
                    if not match or match[2]!=ident:fail()
                    rid=match[1];uri(c['href'],'interview',{'case':case_id,'id':rid,'statement':ident})
                    if reg=='registered':
                        iv=interviews.get(rid)
                        if iv is None or sum(x.get('statementId')==ident for x in iv.get('crossChecks',[]))!=1:fail()
                elif kind in ('colreg-check','recommendation','whatif','systemic'):
                    if reg=='registered':fail('报告含未支持模块的已登记来源，不能局部恢复')
                    if kind=='recommendation':
                        uri(c['href'],'recs',{'case':case_id,'id':ident})
                        if ref!='recommendations/'+ident:fail()
                    elif kind=='colreg-check':
                        q=dict(parse_qsl(c['href'].partition('?')[2]));text(q.get('run'))
                        uri(c['href'],'colreg',{'case':case_id,'check':ident,'run':q['run']})
                        if ref!='colreg/current/checks/'+ident:fail()
                    else:
                        page='analysis'if kind=='whatif'else'systemic';placeholder='W14'if kind=='whatif'else'W15'
                        q=dict(parse_qsl(c['href'].partition('?')[2]))
                        if set(q)=={'case'}:
                            if ident!=placeholder or ref!=placeholder:fail()
                            uri(c['href'],page,{'case':case_id})
                        else:
                            key='scenario'if kind=='whatif'else'id';text(q.get(key));text(ref,512)
                            if kind=='systemic'and q[key]!=ident:fail()
                            uri(c['href'],page,{'case':case_id,key:q[key]})
                else:fail()
        for k,v in d.items():
            if k!='citations':citations(v,case_id,evidence,interviews)


def report_graph(reports):
    pairs=set()
    for rid,r in reports.items():
        stamp(r['createdUtc']);uri(r['reportHref'],'report',{'case':r['caseId'],'report':rid})
        pair=(r['familyId'],r['version'])
        if pair in pairs:fail()
        pairs.add(pair)
        parent=r['parentReportId']
        if parent is None:
            if r['familyId']!=rid:fail()
        elif parent not in reports or reports[parent]['familyId']!=r['familyId'] or reports[parent]['version']>=r['version']:fail()
        seen={rid}
        while parent is not None:
            if parent in seen:fail()
            seen.add(parent);parent=reports[parent]['parentReportId']
        ids=set()
        for section in r['sections']:
            if section['sectionId']in ids:fail()
            ids.add(section['sectionId']);sent=set()
            for sentence in section['sentences']:
                if sentence['sentenceId']in sent:fail()
                sent.add(sentence['sentenceId'])


def review_shape(value,sentence):
    if not isinstance(value,dict) or 'reviews'in value:fail()
    schema('report#/$defs/'+('sentence'if sentence else'section'),{**value,'reviews':[]})


def error_list(errors):
    if not isinstance(errors,list) or len(errors)>2048:fail()
    for e in errors:
        exact(e,{'fieldId','code','message'});text(e['fieldId']);text(e['message'],16000,True)
        if e['code']not in {'field_unknown','field_required','field_type','field_enum','field_range','field_length','field_pattern','field_checksum','field_utc'}:fail()


def snapshots(entries,reports,audit_lines,case_id):
    from ..package_intake.parser import strict_json
    if not isinstance(entries,list) or len(entries)>1024:fail()
    events={i:strict_json(line.encode()) for i,line in enumerate(audit_lines,1)}
    byseq={};bykey={}
    for row in entries:
        exact(row,{'key','createdUtc','updatedUtc','doc'});text(row['key']);stamp(row['createdUtc']);stamp(row['updatedUtc'])
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',row['key']):fail()
        d=row['doc'];exact(d,{'reportId','sectionId','sentenceId','reason','beforeValue','afterValue','summary','auditSeq'})
        text(d['reason'],MAX_BYTES,True);text(d['summary'],200,True);integer(d['auditSeq'],1)
        if row['key']in bykey or d['auditSeq']in byseq:fail()
        bykey[row['key']]=d;byseq[d['auditSeq']]=d
        e=events.get(d['auditSeq']);rid=d['reportId'];sid=d['sectionId'];tid=d['sentenceId']
        if rid is not None and rid not in reports:fail('报告快照缺少原报告，不能丢弃或虚构')
        if e is None or e.get('category')!='Report' or e.get('snapshot_ref')!='report-snapshot:'+row['key'] or e.get('reason','')!=d['reason']:fail()
        if e.get('entity_type')!=('report'if rid else'gisis') or e.get('entity_id')!=(rid or case_id):fail()
        action=e['action'];before=d['beforeValue'];after=d['afterValue']
        if action in ('report.generate','report.colreg.draft','report.regenerate'):
            if not rid or sid is not None or tid is not None:fail()
            schema('report',after)
            if after['reportId']!=rid or after['caseId']!=case_id:fail()
            if action=='report.regenerate':
                schema('report',before)
                if before['reportId']!=after['parentReportId'] or before['familyId']!=after['familyId'] or before['caseId']!=case_id:fail()
            elif before is not None:fail()
        elif action in ('report.review.confirm','report.review.dismiss','report.review.modify'):
            if not rid or not isinstance(sid,str):fail()
            review_shape(before,tid is not None);review_shape(after,tid is not None)
            field='sentenceId'if tid is not None else'sectionId';ident=tid or sid
            if before[field]!=ident or after[field]!=ident or after['status']!={'confirm':'Confirmed','dismiss':'Dismissed','modify':'Modified'}[action.rsplit('.',1)[1]]:fail()
            # Replaced generated sentences can exist only in historical snapshots.
            if not any(x['sectionId']==sid for x in reports[rid]['sections']):fail()
        elif action=='report.export':
            if not rid or sid is not None or tid is not None:fail()
            exact(before,{'status'});exact(after,{'format','lang','sha256'})
            if before['status']not in STATUSES or after['format']not in ('pdf','docx') or after['lang']not in ('zh','en','bilingual'):fail()
            sha(after['sha256'])
        elif action.startswith('report.gisis.'):
            if rid is not None or sid is not None or tid is not None:fail()
            if action=='report.gisis.validate':
                schema('report#/$defs/gisis',before)
                if before['caseId']!=case_id:fail()
                exact(after,{'values','valid','errors','fields'})
                if not isinstance(after['values'],dict) or type(after['valid'])is not bool or not isinstance(after['fields'],list):fail()
                error_list(after['errors'])
                if after['valid'] != (not after['errors']):fail()
                for f in after['fields']:schema('report#/$defs/gisisField',f)
            elif action in ('report.gisis.export','report.gisis.export_rejected'):
                if before is not None:fail()
                exact(after,{'format','validated','sha256'if action.endswith('.export')else'errors'})
                if after['format']not in ('json','csv') or type(after['validated'])is not bool:fail()
                if action.endswith('.export'):sha(after['sha256'])
                else:
                    if after['validated']:fail()
                    error_list(after['errors'])
            else:fail('未知报告历史操作，不推断其快照格式')
        else:fail('未知报告历史操作，不推断其快照格式')
    for seq,e in events.items():
        ref=e.get('snapshot_ref','')
        if e.get('category')=='Report' or e.get('action','').startswith('report.') or ref.startswith('report-snapshot:'):
            if seq not in byseq or ref!='report-snapshot:'+next(k for k,v in bykey.items() if v is byseq[seq]):fail('报告审计缺少完整快照')
    def reviews(v,rid,section=None,sentence=None):
        if not isinstance(v,dict):return
        if 'sectionId'in v:section=v['sectionId']
        if 'sentenceId'in v:sentence=v['sentenceId']
        for rev in v.get('reviews',[]):
            seq=rev['auditSeq'];s=byseq.get(seq);e=events.get(seq)
            if s is None or e is None or s['reportId']!=rid or s['sectionId']!=section or s['sentenceId']!=sentence:fail()
            if e['action']!='report.review.'+rev['action'] or e['operator']!=rev['operator'] or s['reason']!=rev['reason']:fail()
            if s['beforeValue']!=rev['beforeValue'] or s['afterValue']!=rev['afterValue']:fail()
            stamp(rev['utc']) # separately generated audit UTC need not equal it
        for k,child in v.items():
            if k in ('reviews','beforeValue','afterValue'):continue
            if isinstance(child,dict):reviews(child,rid,section,sentence)
            elif isinstance(child,list):
                for item in child:reviews(item,rid,section,sentence)
    for rid,report in reports.items():reviews(report,rid)


def manual_receipts(entries,case_id):
    if not isinstance(entries,list) or len(entries)>2048:fail()
    seen=set()
    for d in entries:
        exact(d,{'case_id','request_id','operation','record_id','request_digest','operator','role','receipt'})
        uuid_key(d['request_id']);sha(d['request_digest']);text(d['operator'],16000,True)
        if d['case_id']!=case_id or d['request_id']in seen or d['role']not in ('Investigator','LeadInvestigator') or d['operation']not in ('create','append-turn'):fail()
        if not re.fullmatch(r'IR-[0-9]{2,}',text(d['record_id'],64)):fail()
        seen.add(d['request_id']);r=d['receipt']
        exact(r,{'requestId','operation','recordId','beforeDigest','afterDigest','turnRound','appliedUtc'})
        if (r['requestId'],r['operation'],r['recordId'])!=(d['request_id'],d['operation'],d['record_id']):fail()
        sha(r['afterDigest']);stamp(r['appliedUtc'])
        if d['operation']=='create':
            if r['beforeDigest']is not None or r['turnRound']is not None:fail()
        else:sha(r['beforeDigest']);integer(r['turnRound'],1,256)


def inspect_historical_packages(data,files,case_id,outer_member_count=None):
    from ..package_intake.parser import read_bounded,strict_json
    from ..package.mcase import CASE_FIELDS,CASE_EXT_FIELDS,infer_role
    artifacts=data['historicalArtifacts'];history=data['importHistory'];lineage=data['lineage']
    if not isinstance(artifacts,list) or len(artifacts)>32 or not isinstance(history,list) or len(history)>2048:fail()
    exact(lineage,{'nodes'})
    if not isinstance(lineage['nodes'],list) or len(lineage['nodes'])>32:fail()
    art={};nodes={};expanded=sum(len(b)for b in files.values());members=len(files)if outer_member_count is None else outer_member_count
    for a in artifacts:
        exact(a,{'sha256','sizeBytes','relativePath','mediaType'});sha(a['sha256']);integer(a['sizeBytes'],0,MAX_BYTES)
        h=a['sha256'];path='history/artifacts/'+h+'.bin'
        if h in art or a['relativePath']!=path or a['mediaType']!='application/octet-stream' or path not in files:fail()
        raw=files[path]
        if len(raw)!=a['sizeBytes'] or hashlib.sha256(raw).hexdigest()!=h:fail()
        # Count declared expansion BEFORE extraction, then the bounded reader checks actual sizes/CRC.
        import zipfile,io
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                infos=z.infolist();expanded+=sum(x.file_size for x in infos);members+=len(infos)
        except (ValueError,zipfile.BadZipFile):fail()
        if expanded>64*1024*1024 or members>2048:fail('历史源包累计检查超过64MiB/2048成员预算，不丢弃祖先','ARCHIVE_BUDGET',413)
        inside=read_bounded(raw)
        if 'manifest.json'not in inside or 'case.json'not in inside or 'case.ext.json'not in inside:fail()
        m=strict_json(inside['manifest.json'])
        exact(m,{'packageFormat','packageVersion','caseId','createdAtUtc','lastModifiedAtUtc','generatorVersion','files'})
        if m['packageFormat']!='MCIS-MCASE' or m['packageVersion']not in ('1.0.0','1.1.0','1.2.0','1.3.0') or m['caseId']!=case_id:fail('历史源包版本或案件关联不支持')
        stamp(m['createdAtUtc']);stamp(m['lastModifiedAtUtc']);text(m['generatorVersion'])
        if not isinstance(m['files'],list):fail()
        listed=set()
        for f in m['files']:
            exact(f,{'relativePath','role','sizeBytes','sha256'});p=f['relativePath']
            if not isinstance(p,str) or p in listed or p=='manifest.json' or p not in inside:fail()
            if f['role']!=infer_role(p) or type(f['sizeBytes'])is not int or f['sizeBytes']!=len(inside[p]) or f['sha256']!=hashlib.sha256(inside[p]).hexdigest():fail()
            listed.add(p)
        if listed!=inside.keys()-{'manifest.json'}:fail()
        c=strict_json(inside['case.json']);ext=strict_json(inside['case.ext.json'])
        exact(c,CASE_FIELDS)
        if not isinstance(ext,dict) or set(ext)-set(CASE_EXT_FIELDS):fail()
        schema('case',{**c,**ext})
        if c['caseId']!=case_id:fail()
        art[h]={**a,'_packageVersion':m['packageVersion']}
    for n in lineage['nodes']:
        exact(n,{'artifactSha256','parentArtifactSha256s'});h=n['artifactSha256'];parents=n['parentArtifactSha256s']
        if h not in art or h in nodes or not isinstance(parents,list) or len(parents)!=len(set(parents)) or any(p not in art or p==h for p in parents):fail()
        nodes[h]=parents
    if nodes.keys()!=art.keys():fail()
    def depth(h,path):
        if h in path:fail('历史外部索引成环')
        if len(path)>=8:fail('历史外部索引超过8层预算','ARCHIVE_BUDGET',413)
        for p in nodes[h]:depth(p,path|{h})
    for h in nodes:depth(h,set())
    return art


def import_history(data,files,evidence,custody_lines,case_id,art):
    from ..package_intake.parser import strict_json
    from ..evidence_intake.parser import PREFIX,preview,PROFILE as EVIDENCE_PROFILE
    from ..evidence.service import custody_line
    events={i:strict_json(line.encode())for i,line in enumerate(custody_lines,1)}
    seen=set();refs=set();evidence_receipts={}
    for h in data['importHistory']:
        exact(h,{'kind','caseId','key','createdUtc','updatedUtc','metadata','sourceArtifactSha256'})
        if h['kind']not in ('package-intake','evidence-intake','track-intake') or h['caseId']!=case_id:fail()
        sha(h['key']);key=(h['kind'],h['key'])
        if key in seen:fail()
        seen.add(key);m=h['metadata']
        if h['kind']=='track-intake':
            continue # Exact source/index association is validated against reconstructed originals below.
        if h['kind']=='package-intake':
            stamp(h['createdUtc']);stamp(h['updatedUtc'])
            if h['sourceArtifactSha256']!=h['key'] or h['key']not in art:fail()
            refs.add(h['key'])
            required={'profile','caseId','title','sourceSha256','byteLength','counts','warnings','importedUtc','replayed'}
            optional={'packageVersion','hfacsExtension','workingRecordsExtension'}
            if not isinstance(m,dict) or required-set(m) or set(m)-required-optional:fail()
            if m['profile']!='MCIS-BASIC-INTAKE-1' or m['caseId']!=case_id or m['sourceSha256']!=h['key'] or m['byteLength']!=art[h['key']]['sizeBytes'] or type(m['replayed'])is not bool:fail()
            if m.get('packageVersion','1.0.0')!=art[h['key']]['_packageVersion']:fail()
            for field in ('hfacsExtension','workingRecordsExtension'):
                summary=m.get(field)
                if summary is not None:
                    counts=('draftCount','revisionCount','receiptCount')if field=='hfacsExtension'else(('interviewCount','reportCount','reportSnapshotCount','manualReceiptCount','trackReceiptCount')if summary.get('version')=='MCIS-WORKING-RECORDS-2'else('interviewCount','reportCount','reportSnapshotCount','manualReceiptCount'))
                    exact(summary,{'version','receiptMode','identityMode',*counts})
                    if summary['version']!=('MCIS-HFACS-PACKAGE-1'if field=='hfacsExtension'else ('MCIS-WORKING-RECORDS-2'if summary.get('version')=='MCIS-WORKING-RECORDS-2'else PROFILE))or summary['receiptMode']!='archive-only'or summary['identityMode']!='unverified-self-reported':fail()
                    for count in counts:integer(summary[count])
            stamp(m['importedUtc']);text(m['title'],16000,True)
            if not isinstance(m['counts'],dict) or set(m['counts'])!={'vessels','tracks','environment','evidence','custodyEvents','auditEvents'}:fail()
            for v in m['counts'].values():integer(v)
            if not isinstance(m['warnings'],list):fail()
            for v in m['warnings']:text(v,16000,True)
        else:
            if any(h[k]is not None for k in ('createdUtc','updatedUtc','sourceArtifactSha256')):fail()
            exact(m,{'custodySeq','evidenceId','requestDigest','binding','sourceSha256','relativePath'})
            integer(m['custodySeq'],1);sha(m['sourceSha256'])
            e=events.get(m['custodySeq']);item=evidence.get(m['evidenceId'])
            if e is None or item is None or m['requestDigest']!=h['key'] or m['relativePath']!='raw/evidence-intakes/'+h['key']+'/source.bin':fail()
            if m['evidenceId']in evidence_receipts:fail()
            evidence_receipts[m['evidenceId']]=h
            if e.get('action')!='custody.register' or e.get('evidence_id')!=m['evidenceId'] or not e.get('detail','').startswith(PREFIX):fail()
            detail=strict_json(e['detail'][len(PREFIX):].encode());exact(detail,{'binding','requestDigest'})
            if detail!={'binding':m['binding'],'requestDigest':h['key']}:fail()
            b=m['binding'];raw=files.get(m['relativePath'])
            if raw is None or item['relativePath']!=m['relativePath'] or item['sha256']!=m['sourceSha256'] or hashlib.sha256(raw).hexdigest()!=m['sourceSha256']:fail()
            try:
                body={**b['metadata'],'profile':EVIDENCE_PROFILE,'fileName':b['fileName']}
                result,rebuilt=preview(body,raw,case_id,b['operator'],b['role'])
            except Exception:fail()
            if rebuilt!=b or result['requestDigest']!=h['key'] or b['role']not in ('Investigator','LeadInvestigator'):fail()
            expected={'caseId':case_id,'evidenceId':m['evidenceId'],'relativePath':m['relativePath'],'sha256':m['sourceSha256'],**b['metadata']}
            if any(item.get(k)!=v for k,v in expected.items()if k!='note') or e['operator']!=b['operator']:fail()
            original=custody_line(seq=e['seq'],utc=e['utc'],operator=e['operator'],kind='Register',evidence_id=m['evidenceId'],sha256=m['sourceSha256'],previous_sha256='',detail=e['detail'],matched=None,prev=e['prev'],item=expected)
            if original!=custody_lines[m['custodySeq']-1]:fail()
    if refs!=art.keys():fail('历史原包缺少明确来源索引')
    # No original custody-derived credential may silently remain active after restore.
    for e in events.values():
        if e.get('action')=='custody.register'and e.get('detail','').startswith(PREFIX):
            h=evidence_receipts.get(e['evidence_id'])
            if h is None or h['metadata']['custodySeq']!=e['seq']:fail('证据登记历史缺少禁用凭证索引')


def validate(raw,case_id,files,evidence,audit_lines,custody_lines,*,outer_member_count=None):
    from ..package_intake.parser import strict_json
    if len(raw)>MAX_BYTES:fail('工作记录成员超过16MiB','ARCHIVE_BUDGET',413)
    data=strict_json(raw);exact(data,KEYS)
    # Classify engineering capacity separately from malformed schema/semantics.
    for key,cap in {'interviews':128,'reports':256,'reportSnapshots':1024,'manualReceipts':2048,'importHistory':2048,'historicalArtifacts':32}.items():
        if isinstance(data.get(key),list) and len(data[key])>cap:
            fail('工作记录列表超过完整保全预算，不截断历史','ARCHIVE_BUDGET',413)
    lineage=data.get('lineage')
    if isinstance(lineage,dict) and isinstance(lineage.get('nodes'),list):
        if len(lineage['nodes'])>32:fail('历史索引超过节点预算','ARCHIVE_BUDGET',413)
        for node in lineage['nodes']:
            if isinstance(node,dict) and isinstance(node.get('parents'),list) and len(node['parents'])>32:
                fail('历史索引超过父引用预算','ARCHIVE_BUDGET',413)
    schema('working-record-archive-v2'if data.get('version')==2 else'working-record-archive',data)
    if data['format']!=FORMAT or type(data['version'])is not int or data['version']not in (1,2) or data['caseId']!=case_id or data['receiptPolicy']!='archive-only-on-import':fail()
    # Ensures recursive finite/scalar encoding, including surrogate strings.
    try:canonical(data)
    except (ValueError,UnicodeError,RecursionError):fail()
    interviews=rows(data['interviews'],'interview','recordId',case_id,128)
    reports=rows(data['reports'],'report','reportId',case_id,256)
    for iv in interviews.values():
        eid=iv.get('evidenceId');h=iv.get('sourceSha256')
        if eid:
            if eid not in evidence or h!=evidence[eid]['sha256']:fail('笔录来源引用或登记摘要不一致')
        if h:sha(h)
        rounds=iv.get('turns',[])
        if len(rounds)>256 or any(type(t['round'])is not int or t['round']!=n for n,t in enumerate(rounds,1)):fail()
        statements=iv.get('statements',[]);ids=set()
        for st in statements:
            if st['recordId']!=iv['recordId']or st['statementId']in ids:fail()
            ids.add(st['statementId']);sp=st['span'];n=sp['round']
            if not 1<=n<=len(rounds):fail()
            source=rounds[n-1]['question'if sp['field']=='Question'else'answer'].encode('utf-16-le')
            try:quote=source[sp['start']*2:(sp['start']+sp['length'])*2].decode('utf-16-le')
            except UnicodeError:fail()
            if (sp['start']+sp['length'])*2>len(source)or quote!=st['quote']:fail()
        for cc in iv.get('crossChecks',[]):
            if cc.get('statementId')not in ids or cc.get('recordId',iv['recordId'])!=iv['recordId']:fail()
            for ref in cc.get('evidenceIds',[]):
                if ref not in evidence:fail()
    report_graph(reports);snapshots(data['reportSnapshots'],reports,audit_lines,case_id)
    for coll in (data['reports'],data['reportSnapshots']):citations(coll,case_id,evidence,interviews)
    manual_receipts(data['manualReceipts'],case_id)
    art=inspect_historical_packages(data,files,case_id,outer_member_count)
    import_history(data,files,evidence,custody_lines,case_id,art)
    from ..track_history.validation import collect
    track_entries=collect(files,case_id)
    saved_tracks=[h for h in data['importHistory']if h['kind']=='track-intake']
    if bool(track_entries)!=(data['version']==2)or canonical(sorted(track_entries,key=lambda x:x['key']))!=canonical(sorted(saved_tracks,key=lambda x:x['key'])):fail('航迹历史索引缺失或不一致')
    for line in audit_lines:
        e=strict_json(line.encode())
        if e.get('category')=='Agent':fail('不支持智能体审计与草稿状态的局部归档')
    return ValidatedArchive(raw,data)
