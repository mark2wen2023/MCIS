"""Synthetic isolated Linux server-process RSS measurement over loopback TCP.
No product modifications. One fresh server per scenario; small reproducible samples, no SLA.
"""
import argparse,base64,hashlib,http.client,json,os,random,resource,socket,subprocess,sys,tempfile,threading,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
MIB=1024*1024
p=argparse.ArgumentParser();p.add_argument('--child',action='store_true');p.add_argument('--root');p.add_argument('--mode',choices=['get','export','post'],default='get');p.add_argument('--mib',type=int,default=16);p.add_argument('--files',type=int,default=1);p.add_argument('--clients',type=int,default=1);a=p.parse_args()
assert 1<=a.mib<=32 and 1<=a.files<=4 and 1<=a.clients<=4
CID='AGGREGATE-SYNTHETIC';URL='/api/v1/cases/'+CID

def rss(pid):
    for line in Path(f'/proc/{pid}/status').read_text().splitlines():
        if line.startswith('VmRSS:'):return int(line.split()[1])*1024

if a.child:
    import uvicorn
    from mcis_service.main import create_app
    from mcis_service.db import put_doc
    from mcis_service.cases.models import CaseRow
    from mcis_service.evidence.models import EvidenceRow,CustodyEventRow
    from mcis_service.audit.models import AuditEventRow
    from sqlalchemy import event
    from mcis_service.evidence import recorded_content
    from tests.conftest import make_settings
    app=create_app(make_settings(Path(a.root),False));block=random.Random(9421).randbytes(MIB)
    case={'caseId':CID,'schemaVersion':'1.0.0','title':'Synthetic aggregate study','isFictionalDemo':True,'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0}
    with app.state.db.session() as s:
        put_doc(s,CaseRow,CID,CID,case)
        if a.mode!='post':
            for i in range(a.files):
                eid=f'EV-{i+1:03d}';rel=f'evidence/{eid}.bin';path=app.state.settings.blob_dir/CID/rel
                path.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256()
                with path.open('wb') as f:
                    for _ in range(a.mib):f.write(block);h.update(block)
                put_doc(s,EvidenceRow,CID,eid,{'caseId':CID,'evidenceId':eid,'title':'Synthetic','source':'Synthetic fixture','extractedBy':'Synthetic harness','extractedUtc':'2026-01-01T00:00:00Z','relativePath':rel,'sha256':h.hexdigest(),'category':'Other','confidentiality':'Normal','note':''})
    del block
    metrics={'requests_started':0,'requests_finished':0,'body_received_bytes':0,'active_reads':0,'max_active_reads':0,'body_send_inflight':0,'max_body_send_inflight':0,'active_requests':0,'max_active_requests':0}
    guard=threading.Lock();original=recorded_content.read_content
    def tracked(path):
        with guard:
            metrics['active_reads']+=1;metrics['max_active_reads']=max(metrics['max_active_reads'],metrics['active_reads'])
        try:return original(path)
        finally:
            with guard:metrics['active_reads']-=1
    recorded_content.read_content=tracked
    db_errors=[]
    @event.listens_for(app.state.db.engine,'handle_error')
    def capture(context):
        db_errors.append({'type':type(context.original_exception).__name__,'message':str(context.original_exception)[:240]})
    server=None
    @app.get('/_synthetic_study/status')
    def status():
        buffers=[c.transport.get_write_buffer_size() for c in server.server_state.connections if getattr(c,'transport',None)]
        with app.state.db.session() as session:
            counts={m.__tablename__:session.query(m).count() for m in (EvidenceRow,CustodyEventRow,AuditEventRow)}
        blobs=[str(p.relative_to(app.state.settings.blob_dir)) for p in app.state.settings.blob_dir.rglob('*') if p.is_file()]
        return {'db_errors':list(db_errors),'counts':counts,'synthetic_blob_paths':blobs,**metrics,'pid':os.getpid(),'rss':rss(os.getpid()),'rss_peak':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'transport_write_buffer_bytes':sum(buffers),'transport_nonempty':sum(x>0 for x in buffers)}
    class Observed:
        def __init__(self,app):self.app=app
        async def __call__(self,scope,receive,send):
            if scope['type']!='http' or scope['path'].startswith('/_synthetic_study/'):
                return await self.app(scope,receive,send)
            metrics['requests_started']+=1;metrics['active_requests']+=1;metrics['max_active_requests']=max(metrics['max_active_requests'],metrics['active_requests'])
            async def recv():
                msg=await receive();metrics['body_received_bytes']+=len(msg.get('body',b''));return msg
            async def emit(msg):
                n=len(msg.get('body',b''));metrics['body_send_inflight']+=n;metrics['max_body_send_inflight']=max(metrics['max_body_send_inflight'],metrics['body_send_inflight'])
                try:await send(msg)
                finally:metrics['body_send_inflight']-=n
            try:await self.app(scope,recv,emit)
            finally:metrics['requests_finished']+=1;metrics['active_requests']-=1
    sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(128)
    server=uvicorn.Server(uvicorn.Config(Observed(app),host='127.0.0.1',port=sock.getsockname()[1],log_level='error',access_log=False))
    print(json.dumps({'port':sock.getsockname()[1],'pid':os.getpid()}),flush=True)
    server.run(sockets=[sock]);sys.exit(0)

with tempfile.TemporaryDirectory(prefix='mcis-aggregate-') as temp:
    cmd=[sys.executable,__file__,'--child','--root',temp,'--mode',a.mode,'--mib',str(a.mib),'--files',str(a.files)]
    with (Path(temp)/'stderr').open('w+') as err:
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=err,text=True)
        ready=json.loads(proc.stdout.readline());port=ready['port'];pid=ready['pid']
        def status():
            c=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
            try:c.request('GET','/_synthetic_study/status');r=c.getresponse();assert r.status==200;return json.loads(r.read())
            finally:c.close()
        try:
            for _ in range(100):
                try:initial=status();break
                except (OSError,http.client.HTTPException):time.sleep(.02)
            else:raise AssertionError('server unavailable')
            release=threading.Event();headers_seen=[threading.Event() for _ in range(a.clients)]
            def request(i):
                c=http.client.HTTPConnection('127.0.0.1',port,timeout=20);start=time.monotonic()
                try:
                    if a.mode=='post':
                        raw=(b'\x00\xffsynthetic-'+bytes([i]))*((a.mib*MIB)//13+1);raw=raw[:a.mib*MIB]
                        body=json.dumps({'title':'Synthetic upload','source':'Synthetic fixture','extractedBy':'Synthetic harness','extractedUtc':'2026-01-01T00:00:00Z','relativePath':f'evidence/upload-{i}.bin','contentBase64':base64.b64encode(raw).decode()}).encode()
                        c.request('POST',URL+'/evidence',body,{'Content-Type':'application/json','X-MCIS-Role':'Investigator'});sent=len(body)
                    else:
                        c.request('GET',URL+('/export' if a.mode=='export' else '/evidence/EV-001/content'),headers={'X-MCIS-Role':'Investigator'});sent=0
                    response=c.getresponse();headers_seen[i].set();assert release.wait(20)
                    length=0;digest=hashlib.sha256();failure=b''
                    while chunk:=response.read(256*1024):
                        length+=len(chunk);digest.update(chunk)
                        if response.status>=400:failure+=chunk[:max(0,2048-len(failure))]
                    return {'failure_body':failure.decode('utf-8','replace'),'status':response.status,'bytes':length,'received_sha256':digest.hexdigest(),'request_bytes':sent,'elapsed_s':round(time.monotonic()-start,4)}
                finally:c.close()
            peak_sample=initial['rss'];stop=threading.Event()
            def sample():
                global_unused=None
                while not stop.wait(.005):
                    try:samples.append(rss(pid))
                    except FileNotFoundError:break
            samples=[];sampler=threading.Thread(target=sample);sampler.start();start=time.monotonic()
            try:
                with ThreadPoolExecutor(a.clients) as pool:
                    futures=[pool.submit(request,i) for i in range(a.clients)]
                    try:
                        assert all(e.wait(20) for e in headers_seen),'headers timeout'
                        time.sleep(.25);held=status()
                    finally:release.set()
                    responses=[f.result(timeout=30) for f in futures]
                final=status()
            finally:release.set();stop.set();sampler.join()
            print(json.dumps({'mode':a.mode,'mib':a.mib,'files':a.files,'clients':a.clients,'initial':initial,'held':held,'final':final,'sampled_rss_peak':max(samples,default=initial['rss']),'responses':responses,'elapsed_s':round(time.monotonic()-start,4),'synthetic':True},sort_keys=True))
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
