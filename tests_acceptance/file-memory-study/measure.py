"""Reproducible synthetic Linux memory study. No production or model/network services.
Run from service with PYTHONPATH=.:..; each mode in a FRESH Python process.
API measurements include TestClient's in-process captured response copies, not production RSS.
"""
import argparse,base64,gc,hashlib,json,os,random,resource,tempfile,threading,time,tracemalloc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MIB=1024*1024
p=argparse.ArgumentParser();p.add_argument('mode',choices=['safe','bounded','get','export','concurrent']);p.add_argument('--mib',type=int,default=8);p.add_argument('--files',type=int,default=1);p.add_argument('--workers',type=int,default=4);a=p.parse_args()
assert 0<=a.mib<=64 and 1<=a.files<=4 and 1<=a.workers<=4

def rss():
    for line in Path('/proc/self/status').read_text().splitlines():
        if line.startswith('VmRSS:'):return int(line.split()[1])*1024

def measure(fn):
    gc.collect();before=rss();prior_peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    tracemalloc.start();start=time.monotonic();value=fn();elapsed=time.monotonic()-start
    allocated,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    return value,{'elapsed_s':round(elapsed,4),'rss_before':before,'rss_after':rss(),'rss_peak':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'rss_peak_before':prior_peak,'python_current':allocated,'python_peak':peak}

with tempfile.TemporaryDirectory(prefix='mcis-memory-synthetic-') as temp:
    root=Path(temp);block=random.Random(4821).randbytes(MIB)
    def write(path):
        path.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256()
        with path.open('wb') as f:
            for _ in range(a.mib):f.write(block);h.update(block)
        return h.hexdigest()
    result={'mode':a.mode,'file_mib':a.mib,'files':a.files,'workers':a.workers,'pid':os.getpid(),'synthetic':True}
    if a.mode in ('safe','bounded'):
        from mcis_service.common.safe_files import read_regular_no_symlinks,ReadBudgetExceeded
        path=root/'synthetic.bin';write(path)
        def read():
            try:
                raw=read_regular_no_symlinks(path,8*MIB if a.mode=='bounded' else __import__('sys').maxsize)
                return {'bytes':len(raw),'outcome':'read'}
            except ReadBudgetExceeded:return {'outcome':'ReadBudgetExceeded'}
        value,stats=measure(read);result.update(value);result.update(stats)
    else:
        from fastapi.testclient import TestClient
        from sqlalchemy import event
        from mcis_service.main import create_app
        from mcis_service.db import put_doc
        from mcis_service.cases.models import CaseRow
        from mcis_service.evidence.models import EvidenceRow
        from mcis_service.audit.models import AuditEventRow
        from mcis_service.evidence import recorded_content
        from mcis_service.redaction.policy import default_policy
        from tests.conftest import make_settings,H
        app=create_app(make_settings(root,seed=False));cid='MEMORY-SYNTHETIC';url='/api/v1/cases/'+cid
        case={'caseId':cid,'schemaVersion':'1.0.0','title':'Synthetic memory study','isFictionalDemo':True,'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0}
        with app.state.db.session() as s:
            put_doc(s,CaseRow,cid,cid,case)
            for i in range(a.files):
                eid=f'EV-{i+1:03d}';rel=f'evidence/{eid}/source.bin';digest=write(app.state.settings.blob_dir/cid/rel)
                item={'caseId':cid,'evidenceId':eid,'title':'Synthetic bytes','source':'Synthetic generated fixture, not authenticated source','extractedBy':'Synthetic harness','extractedUtc':'2026-01-01T00:00:00Z','relativePath':rel,'sha256':digest,'category':'Other','confidentiality':'Normal','note':''}
                put_doc(s,EvidenceRow,cid,eid,item)
        with TestClient(app) as client:
            endpoint=url+('/export' if a.mode=='export' else '/evidence/EV-001/content')
            def request():
                started=time.monotonic();r=client.get(endpoint,headers=H());return r,round(time.monotonic()-started,4)
            def read():
                if a.mode!='concurrent':
                    r,elapsed=request();return {'statuses':[r.status_code],'response_bytes':[len(r.content)],'request_s':[elapsed]}
                entered=threading.Event();release=threading.Event();original=recorded_content.read_content
                def held(path):
                    entered.set();assert release.wait(5);return original(path)
                recorded_content.read_content=held
                @event.listens_for(app.state.db.engine,'checkout')
                def timeout(conn,*_):conn.execute('PRAGMA busy_timeout=100')
                try:
                    with ThreadPoolExecutor(a.workers) as pool:
                        first=pool.submit(request);assert entered.wait(3)
                        pending=[first]+[pool.submit(request) for _ in range(a.workers-1)]
                        time.sleep(0.2)
                        completed_before_release=sum(x.done() for x in pending)
                        policy=default_policy();policy['matrix']['Investigator']['evidence_meta']='Deny'
                        revoke=client.put(url+'/access-policy',headers=H('LeadInvestigator'),json=policy)
                        release.set();responses=[x.result(timeout=10) for x in pending]
                    result={'completed_before_release':completed_before_release,'concurrent_policy_status':revoke.status_code,'concurrent_policy_detail':revoke.json().get('detail'), 'statuses':[r.status_code for r,_ in responses],'response_bytes':[len(r.content) for r,_ in responses],'request_s':[t for _,t in responses]}
                    committed=client.put(url+'/access-policy',headers=H('LeadInvestigator'),json=policy)
                    denied=client.get(endpoint,headers=H())
                    result.update({'later_policy_status':committed.status_code,'after_revoke_status':denied.status_code})
                    return result
                finally:release.set();recorded_content.read_content=original
            value,stats=measure(read);result.update(value);result.update(stats)
            with app.state.db.session() as s:result['audit_count']=s.query(AuditEventRow).count()
    print(json.dumps(result,sort_keys=True))
