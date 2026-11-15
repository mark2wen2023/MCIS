"""Loopback HTTP + actual JS api/controller + real temporary SQLite; synthetic only.
No browser, source files, mocked success response, permission probes or ECFC tests.
"""
import json
from pathlib import Path
import selectors
import socket
import subprocess
import threading
import time
import pytest
import uvicorn
from mcis_service.timeline.source_receipts import ConflictSourceReceipt
from .test_working_record_archive import client_at
from .test_conflict_source_receipt_submit import seed, change
from .test_consultation_archive_readiness import state

REPO = Path(__file__).resolve().parents[2]

@pytest.fixture(scope='module')
def controller_bundle(tmp_path_factory):
    target=tmp_path_factory.mktemp('controller')/'http.cjs'
    subprocess.run([str(REPO/'web/node_modules/.bin/esbuild'),
                    'tests/observation-receipt-http.integration.ts', '--bundle',
                    '--platform=node','--format=cjs',f'--outfile={target}',
                    '--log-level=warning'],cwd=REPO/'web',check=True,timeout=30)
    return target

@pytest.mark.parametrize('changed',[False,True],ids=['unchanged-save-history','a-to-b-refusal-draft'])
def test_controller_real_http(tmp_path,controller_bundle,changed):
    with client_at(tmp_path/'case',True) as client:
        seed(client)
        sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(128)
        port=sock.getsockname()[1]
        # TestClient owns lifespan; uvicorn serves the same isolated app/SQLite.
        server=uvicorn.Server(uvicorn.Config(client.app,host='127.0.0.1',
                    port=port,lifespan='off',log_level='error',access_log=False))
        thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True)
        process=None
        thread.start()
        try:
            deadline=time.monotonic()+5
            while not server.started and time.monotonic()<deadline:
                time.sleep(.01)
            assert server.started,'Loopback server did not start'
            process=subprocess.Popen(['node',str(controller_bundle),
                         f'http://127.0.0.1:{port}','changed' if changed else 'unchanged'],
                         stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout,selectors.EVENT_READ)
                assert selector.select(timeout=20),'Controller did not receive real receipt'
                assert process.stdout.readline().strip()=='RECEIPT_READY'
            if changed:
                change(client,'EV-A') # synthetic registry A->B; no original file
            before_submit=state(client)
            out,err=process.communicate(input='continue\n',timeout=20)
            assert process.returncode==0,err
            if changed:
                assert state(client)==before_submit # rejection leaves documents/audit unchanged
            result=json.loads(out)
            assert result['result']==('source-change-refused' if changed else 'saved-with-history')
            with client.app.state.db.session() as session:
                receipt=session.get(ConflictSourceReceipt,result['receiptId'])
                assert receipt is not None
                assert receipt.consumed_revision==(None if changed else 2)
        finally:
            if process is not None and process.poll() is None:
                process.kill();process.communicate(timeout=5)
            server.should_exit=True;thread.join(timeout=5);sock.close()
            assert not thread.is_alive(),'Loopback server did not stop'
