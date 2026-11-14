"""Isolated DB; actual uvicorn/Vite/W2 in one process tree. No deployment, no mock responses."""
import os,sys,socket,threading,time,tempfile,subprocess,urllib.request
from pathlib import Path
import uvicorn
from mcis_service.main import create_app
from mcis_service.config import Settings
ROOT=Path(__file__).resolve().parents[2]
WEB=ROOT/'web'
core=os.environ.get('MCIS_ACCEPTANCE_CORE')
if not core: raise SystemExit('MCIS_ACCEPTANCE_CORE actual compiled W2 wrapper required')
with tempfile.TemporaryDirectory(prefix='mcis-network-') as tmp:
    st=Settings();st.data_dir=Path(tmp);st.db_url=f'sqlite:///{tmp}/test.db';st.seed_demo=True;st.core_cmd=core
    app=create_app(st)
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    vite=None
    bundle=WEB/'tests/.tmp-registered-network.mjs'
    try:
        end=time.monotonic()+15
        while not server.started and time.monotonic()<end:time.sleep(.05)
        assert server.started
        with socket.socket() as probe:
            probe.bind(('127.0.0.1',0));web_port=probe.getsockname()[1]
        web_url=f'http://127.0.0.1:{web_port}'
        env={**os.environ,'MCIS_API':f'http://127.0.0.1:{port}','MCIS_ACCEPTANCE_WEB_URL':web_url}
        vite=subprocess.Popen([str(WEB/'node_modules/.bin/vite'),'--host','127.0.0.1','--port',str(web_port),'--strictPort'],cwd=WEB,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        end=time.monotonic()+20
        while True:
            if vite.poll() is not None:raise RuntimeError(vite.stderr.read().decode())
            try:
                with opener.open(web_url,timeout=1) as r:assert r.status==200
                break
            except OSError:
                if time.monotonic()>end:raise
                time.sleep(.1)
        if vite.poll() is not None:raise RuntimeError('Vite exited before test')
        subprocess.run([str(WEB/'node_modules/.bin/esbuild'),str(WEB/'tests/registered-network.ts'),'--bundle','--platform=node','--format=esm',f'--outfile={bundle}','--log-level=warning'],check=True)
        subprocess.run(['node',str(bundle)],check=True,timeout=60,env=env)
    finally:
        if vite:
            vite.terminate()
            try:vite.wait(timeout=10)
            except subprocess.TimeoutExpired:vite.kill();vite.wait()
        server.should_exit=True;thread.join(10);sock.close();bundle.unlink(missing_ok=True)
        assert not thread.is_alive()
