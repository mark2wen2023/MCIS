"""Actual localhost Uvicorn process restart and bounded 1.4 round-trip; synthetic only."""
import base64
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from contextlib import contextmanager
from tempfile import TemporaryDirectory
import time
import zipfile

CASE='SYN-W17-PROCESS'
ROOT='/api/v1/cases/'+CASE
LEAD={'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'Synthetic%20archive%20reviewer'}
DENIED={'X-MCIS-Role':'ExternalExpert','X-MCIS-Operator':'Synthetic%20denied'}
EVIDENCE='一次独立合成读取，非案件原始记录。\n'.encode()
sha=lambda b:hashlib.sha256(b).hexdigest()

def request(port,method,path,*,body=None,headers=LEAD,code=200,raw=False):
    assert path.startswith('/api/v1/')
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
    try:
        extra={'Content-Type':'application/json'} if body is not None else {}
        c.request(method,path,body=json.dumps(body,ensure_ascii=False).encode() if body is not None else None,headers={**headers,**extra})
        r=c.getresponse(); data=r.read(); hs={k.lower():v for k,v in r.getheaders()}
        assert r.status==code,(path,r.status,data[:800])
        return (data,hs) if raw else json.loads(data)
    finally:
        c.close()

@contextmanager
def server(store):
    store.mkdir(exist_ok=True)
    with socket.socket() as sock, TemporaryDirectory(prefix='w17-loopback-logs-') as t:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.listen(64)
        fd=sock.fileno()
        env={k:v for k,v in os.environ.items() if not k.startswith('MCIS_')}
        env.update(MCIS_SEED_DEMO='0',MCIS_DATA_DIR=str(store),PYTHONDONTWRITEBYTECODE='1')
        runner="import os,socket,sys,uvicorn; s=socket.socket(fileno=int(sys.argv[1])); uvicorn.Server(uvicorn.Config('mcis_service.main:create_app', factory=True, host='127.0.0.1', access_log=False, log_level='warning')).run(sockets=[s])"
        log=Path(t)/'server.log'
        with log.open('wb') as f:
            proc=subprocess.Popen([sys.executable,'-c',runner,str(fd)],env=env,pass_fds=(fd,),stdout=f,stderr=subprocess.STDOUT)
            try:
                for i in range(100):
                    if proc.poll() is not None: raise AssertionError(log.read_text())
                    try:
                        if request(port,'GET','/api/v1/health',headers={})['status']=='ok':break
                    except (OSError,http.client.HTTPException):
                        time.sleep(.05)
                else:raise AssertionError('health wait exceeded')
                yield port,proc.pid
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:proc.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        proc.kill();proc.wait(timeout=8)
                        raise AssertionError('server did not stop normally; restart gate is not verified')

def members(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert len(set(z.namelist()))==len(z.namelist())
        return {n:z.read(n)for n in z.namelist() if not n.endswith('/')}

def outer(port):
    raw,headers=request(port,'GET',ROOT+'/export',raw=True)
    assert headers['content-type']=='application/zip' and headers['cache-control']=='no-store'
    files=members(raw)
    m=json.loads(files['manifest.json']);assert m['packageVersion']=='1.4.0'
    return raw,files

def strict(port,raw):
    data={'contentBase64':base64.b64encode(raw).decode()}
    preview=request(port,'POST','/api/v1/packages/intakes:preview',body=data)
    assert preview['packageVersion']=='1.4.0' and preview['sourceSha256']==sha(raw) and preview['caseId']==CASE
    added=request(port,'POST','/api/v1/packages/intakes:commit',body=dict(data,confirmed=True,sourceSha256=sha(raw)))
    assert added['packageVersion']=='1.4.0' and added['sourceSha256']==sha(raw) and not added['replayed']

def saved_source(files,eid,rid,original_expected,parent=None):
    docs=json.loads(files['working-records/backup.v1.json'])
    assert docs['format']=='MCIS-WORKING-RECORDS' and docs['version']==1
    [history]=[h for h in docs['importHistory'] if h['kind']=='evidence-intake']
    assert history['key']==rid and history['metadata']['evidenceId']==eid
    assert history['metadata']['sourceSha256']==sha(original_expected)
    assert files[history['metadata']['relativePath']]==original_expected
    if parent is not None:
        digest=sha(parent)
        [previous]=[a for a in docs['historicalArtifacts'] if a['sha256']==digest]
        assert previous['sizeBytes']==len(parent) and files[previous['relativePath']]==parent
        assert any(x['artifactSha256']==digest for x in docs['lineage']['nodes'])
        assert any(x['kind']=='package-intake' and x['key']==digest and x['sourceArtifactSha256']==digest for x in docs['importHistory'])

def populate(port):
    body=dict(caseId=CASE,title='Pure synthetic process archive',schemaVersion='1.0.0',accidentType='Collision',
        incidentTimeUtc='2026-01-01T00:00:00Z',caseEpochUtc='2026-01-01T00:00:00Z',
        incidentLocation={'latDeg':0,'lonDeg':0},displayTimeZoneOffsetMinutes=0,isFictionalDemo=True)
    request(port,'POST','/api/v1/cases',body=body,code=201)
    fields=dict(profile='mcis-evidence-intake-v1',fileName='synthetic.txt',title='Synthetic original file',
        source='Synthetic',extractedBy='Synthetic',extractedUtc='2026-01-01T00:00:00Z',category='Document',
        confidentiality='Restricted',note='',contentBase64=base64.b64encode(EVIDENCE).decode())
    p=request(port,'POST',ROOT+'/evidence-intakes:preview',body=fields)
    rec=request(port,'POST',ROOT+'/evidence-intakes:commit',body=dict(fields,confirmed=True,requestDigest=p['requestDigest']))
    assert rec['sourceSha256']==sha(EVIDENCE)
    eid=rec['evidenceId']
    event=request(port,'POST',ROOT+'/timeline/events',code=201,body={'eventId':'TE-01','timeSec':1.2345,
        'endTimeSec':2.5,'kind':'Observation','title':'Synthetic linked timeline item','evidenceIds':[eid],'confirmed':False})
    report=request(port,'POST',ROOT+'/reports',body={'templateId':'cn-msa','lang':'en'},code=201)
    return rec,event,report

def main():
    with TemporaryDirectory(prefix='w17-process-synthetic-') as td:
        temp=Path(td)
        a,b,c=[temp/n for n in ('original','destination','second-generation')]
        with server(a) as (pa,_):
            rec,event,report=populate(pa)
            eid,rid=rec['evidenceId'],rec['requestDigest']
            history=ROOT+'/archive-history/evidence/'+eid+'/content'
            active=ROOT+'/evidence-intakes/'+rid
            report_path=ROOT+'/reports/'+report['reportId']
            provenance=ROOT+'/archive-history/provenance/report/'+report['reportId']
            raw1,f1=outer(pa);saved_source(f1,eid,rid,EVIDENCE)
        with server(b) as (pb,b_pid):
            strict(pb,raw1)
            assert request(pb,'GET',ROOT+'/timeline')['events']==[event]
        with server(b) as (pb2,b2_pid):
            assert b2_pid!=b_pid  # independent OS process, same SQLite and blobs
            before=request(pb2,'GET',ROOT+'/evidence/'+eid+'/custody')
            assert [r['kind'] for r in before]==['Register']
            assert request(pb2,'GET',history,headers=DENIED,code=403)['code']=='FORBIDDEN'
            assert request(pb2,'GET',ROOT+'/export',headers=DENIED,code=403)['code']=='FORBIDDEN'
            assert request(pb2,'GET',active,code=409)['code']=='ARCHIVE_HISTORY_ONLY'
            assert request(pb2,'GET',ROOT+'/evidence/'+eid+'/custody')==before
            old,headers=request(pb2,'GET',history,raw=True)
            assert old==EVIDENCE and headers['x-sha256']==sha(EVIDENCE) and headers['cache-control']=='no-store'
            after=request(pb2,'GET',ROOT+'/evidence/'+eid+'/custody')
            assert [r['kind'] for r in after]==['Register','Access'] and after[0]==before[0]
            assert request(pb2,'GET',report_path)==report
            p=request(pb2,'GET',provenance)['provenance']
            assert p['sourceArchiveSha256']==sha(raw1) and p['changedSinceImport'] is False
            assert p['originalDocumentSha256']==p['currentDocumentSha256']
            assert request(pb2,'GET',ROOT+'/audit:verify')['valid']
            raw2,f2=outer(pb2);saved_source(f2,eid,rid,EVIDENCE,parent=raw1)
            assert f2['timeline/records.v1.json']==f1['timeline/records.v1.json']
            assert f2['analysis/timeline.json']==f1['analysis/timeline.json']
            assert f2['audit/audit.jsonl'].startswith(f1['audit/audit.jsonl'])
            assert request(pb2,'GET',ROOT+'/evidence/'+eid+'/custody')==after
        with server(c) as (pc,_):
            strict(pc,raw2)
            assert request(pc,'GET',ROOT+'/timeline')['events']==[event]
            assert [r['kind'] for r in request(pc,'GET',ROOT+'/evidence/'+eid+'/custody')]==['Register','Access']
            old,headers=request(pc,'GET',history,raw=True)
            assert old==EVIDENCE and headers['x-sha256']==sha(EVIDENCE)
            assert request(pc,'GET',active,code=409)['code']=='ARCHIVE_HISTORY_ONLY'
            p=request(pc,'GET',provenance)['provenance']
            assert p['sourceArchiveSha256']==sha(raw2) and p['changedSinceImport'] is False
            assert request(pc,'GET',ROOT+'/audit:verify')['valid']
        print(json.dumps({'scope':'synthetic-only','processRestartOnSameDb':True,'outerVersion':'1.4.0',
              'sourceSha256':sha(EVIDENCE),'originalArchiveSha256':sha(raw1),'reexportSha256':sha(raw2),
              'sourceHistoryRetained':True,'historicalOnlyActiveReceipt':409,'deniedRole':403,'nextGenerationRestored':True},ensure_ascii=False))
if __name__=='__main__':
    main()
