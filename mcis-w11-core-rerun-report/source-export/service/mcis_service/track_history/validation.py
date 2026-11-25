"""Pure strict validation from original archive bytes, not receipt reactivation."""
import re,base64
from ..working_records_archive.validation import exact,fail,sha,stamp,integer,text,canonical
from ..package_intake.parser import strict_json
from ..tracks_import.parser import inputs,preview,MAX_BYTES
LIMITATIONS=['原件是本次上传的 CSV 字节，不证明原始 AIS 报文或采集链完整。','reported 为来源声明；未清洗或插值，未评定时间精度。']
PATTERN=re.compile(r'raw/track-imports/([a-f0-9]{64})/(source\.csv|report\.json)')

def markers(files):
    if any(p.casefold().startswith('raw/track-imports')for p in files):return True
    for p in ('evidence/index.json','audit/audit.jsonl'):
        raw=files.get(p,b'')
        if b'raw/track-imports'in raw.lower()or b'track.import'in raw or b'track-import'in raw:return True
    return any(b'CSV:'in b for p,b in files.items()if p.startswith('derived/tracks/'))

def collect(files,case_id):
    try:return _collect(files,case_id)
    except (KeyError,TypeError,ValueError,UnicodeError,RecursionError,IndexError):fail()

def _collect(files,case_id):
    case={**strict_json(files['case.json']),**strict_json(files.get('case.ext.json',b'{}'))}
    evidence=strict_json(files['evidence/index.json']);evidence={x['evidenceId']:x for x in evidence}
    vessels={v['vesselId']for v in strict_json(files['vessels.json'])}
    audit=[strict_json(x)for x in files['audit/audit.jsonl'].splitlines()if x]
    custody=[strict_json(x)for x in files['audit/custody.jsonl'].splitlines()if x]
    pairs={}
    for path in files:
        if path.casefold().startswith('raw/track-imports'):
            m=PATTERN.fullmatch(path)
            if not m:fail('航迹历史路径不完整或不受支持')
            pairs.setdefault(m[1],set()).add(m[2])
    result=[];used=set();used_vessels=set()
    for h,parts in sorted(pairs.items()):
        if parts!={'source.csv','report.json'}:fail('航迹历史原件不完整')
        sp=f'raw/track-imports/{h}/source.csv';rp=f'raw/track-imports/{h}/report.json';raw=files[sp];rb=files[rp]
        if len(raw)>MAX_BYTES or len(rb)>256*1024:fail('航迹历史原件超出原W10预算','ARCHIVE_BUDGET',413)
        record=strict_json(rb);exact(record,{'format','receipt','metadata','preview','operator','role','pointSourceFormat','limitations'})
        if record['format']!='MCIS-TRACK-IMPORT-1'or record['role']not in ('Investigator','LeadInvestigator')or record['limitations']!=LIMITATIONS:fail()
        text(record['operator'],32768)
        r=record['receipt'];exact(r,{'caseId','vesselId','previewDigest','sourceSha256','pointCount','sourceEvidenceId','reportEvidenceId','committedUtc'})
        exact(record['metadata'],{'profile','vesselId','fileName','source','timeBasis'})
        stamp(r['committedUtc']);integer(r['pointCount'],1);sha(h)
        for key in ('caseId','vesselId','previewDigest','sourceSha256','sourceEvidenceId','reportEvidenceId'):text(r[key],256)
        if r['caseId']!=case_id or r['previewDigest']!=h or r['vesselId']not in vessels or r['vesselId']in used_vessels or record['metadata']['vesselId']!=r['vesselId']:fail()
        used_vessels.add(r['vesselId'])
        sid=r['sourceEvidenceId'];rid=r['reportEvidenceId']
        if not isinstance(sid,str)or not isinstance(rid,str)or sid==rid or sid in used or rid in used:fail()
        used.update((sid,rid));source=evidence.get(sid);report=evidence.get(rid)
        from hashlib import sha256
        sh=sha256(raw).hexdigest();rh=sha256(rb).hexdigest()
        for item,path,hashval in ((source,sp,sh),(report,rp,rh)):
            if item is None or item['caseId']!=case_id or item['relativePath']!=path or item['sha256']!=hashval:fail()
            events=[e for e in custody if e.get('action')=='custody.register'and e.get('evidence_id')==item['evidenceId']]
            if len(events)!=1 or events[0].get('sha256')!=hashval or events[0].get('detail')!='W10.2 CSV输入原件/派生记录登记'or events[0].get('operator')!=record['operator']:fail()
        if r['sourceSha256']!=sh or record['pointSourceFormat']!=f'CSV:{sid}:row:<1-based-data-row>':fail()
        body={**record['metadata'],'contentBase64':base64.b64encode(raw).decode()}
        try:
            inputs(body);rebuilt,points=preview(body,raw,case,operator=record['operator'],role=record['role'],existing_count=0)
        except Exception:fail()
        if not rebuilt['canCommit']or rebuilt['previewDigest']!=h or canonical(rebuilt)!=canonical(record['preview'])or len(points)!=r['pointCount']:fail()
        expected=[{**p,'source':f'CSV:{sid}:row:{i}'}for i,p in enumerate(points,1)]
        path=f'derived/tracks/{r["vesselId"]}.track.json'
        if path not in files or canonical(strict_json(files[path])['points'])!=canonical(expected):fail('当前航迹与原导入记录不一致')
        events=[e for e in audit if e.get('action')=='track.import'and e.get('entity_type')=='track-import'and e.get('entity_id')==h]
        from ..audit.service import _summ
        ordered={k:r[k]for k in ('caseId','vesselId','previewDigest','sourceSha256','pointCount','sourceEvidenceId','reportEvidenceId','committedUtc')}
        if len(events)!=1 or events[0].get('after')!=_summ(ordered)or events[0].get('operator')!=record['operator']or events[0].get('role')!=record['role']:fail('航迹登记审计不一致')
        result.append({'kind':'track-intake','caseId':case_id,'key':h,'createdUtc':None,'updatedUtc':None,'sourceArtifactSha256':None,'metadata':{'vesselId':r['vesselId'],'sourceEvidenceId':sid,'reportEvidenceId':rid,'sourceSha256':sh,'reportSha256':rh,'sourceRelativePath':sp,'reportRelativePath':rp,'record':record}})
    if any(e.get('relativePath','').casefold().startswith('raw/track-imports')and e['evidenceId']not in used for e in evidence.values()):fail()
    known={x['key']for x in result}
    if any((e.get('action')=='track.import'or e.get('entity_type')=='track-import')and e.get('entity_id')not in known for e in audit):fail()
    for p,b in files.items():
        if p.startswith('derived/tracks/')and p.endswith('.json'):
            for point in strict_json(b).get('points',[]):
                value=point.get('source','')
                if value.startswith('CSV:')and not any(value.startswith('CSV:'+e['metadata']['sourceEvidenceId']+':row:')for e in result):fail()
    return result
