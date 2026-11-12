"""Independent acceptance harness. Real TCP HTTP, ephemeral DB, no seed."""
import contextlib, json, os, pathlib, socket, subprocess, tempfile, time, urllib.request, urllib.error
ROOT = pathlib.Path(__file__).resolve().parents[2]
def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]
def request(base, path, body=None, role='Investigator'):
    req=urllib.request.Request(base+'/api/v1'+path, data=None if body is None else json.dumps(body).encode(), headers={'Content-Type':'application/json','X-MCIS-Role':role,'X-MCIS-Operator':'W82-independent'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r: return r.status, json.load(r)
    except urllib.error.HTTPError as e: return e.code,json.load(e)
def payload(case_id='W82-independent'):
    return dict(caseId=case_id,schemaVersion='1.0.0',title='独立验收 <script>literal</script>',accidentType='Collision',incidentTimeUtc='2026-11-12T09:15:00.000Z',caseEpochUtc='2026-11-12T09:15:00.000Z',displayTimeZoneOffsetMinutes=0,incidentLocation={'latDeg':90,'lonDeg':-180},isFictionalDemo=True,placeName='独立测试水域')
@contextlib.contextmanager
def servers(web=False):
    with tempfile.TemporaryDirectory(prefix='mcis-w82-independent-') as td:
        backend='http://127.0.0.1:'+str(port()); env={**os.environ,'MCIS_DATA_DIR':td,'MCIS_DB_URL':'sqlite:///'+td+'/mcis.db','MCIS_SEED_DEMO':'0','MCIS_PORT':backend.rsplit(':',1)[1]}
        log=open(td+'/service.log','w'); procs=[]
        try:
            procs.append(subprocess.Popen([str(ROOT/'service/.venv/bin/python'),'-m','mcis_service'],cwd=ROOT/'service',env=env,stdout=log,stderr=log))
            targets=[backend+'/api/v1/health']; frontend=None
            if web:
                frontend='http://127.0.0.1:'+str(port())
                procs.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',frontend.rsplit(':',1)[1]],cwd=ROOT/'web',env={**env,'MCIS_API':backend},stdout=log,stderr=log)); targets.append(frontend)
            for target in targets:
                for _ in range(150):
                    try:
                        with urllib.request.urlopen(target,timeout=1): break
                    except Exception: time.sleep(.1)
                else: raise RuntimeError('Startup failed: '+pathlib.Path(td+'/service.log').read_text())
            yield backend,frontend
        finally:
            for p in reversed(procs):
                p.terminate()
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.kill();p.wait()
            log.close()
