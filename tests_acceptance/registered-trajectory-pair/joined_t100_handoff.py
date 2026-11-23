"""Test-only return observer: execute the unchanged joined fixture once, no reads added."""
import contextlib
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys

os.environ['GIT_NO_LAZY_FETCH'] = '1'
ROOT = Path(__file__).resolve().parents[2]
BASE = '17247747272fb53623b144e199260f59d6befcbd'
PRODUCT = 'db90fdf73de7bd26ba75819f0102fc03d0789faf'
HARNESS = 'tests_acceptance/registered-trajectory-pair/four_frames_prepare_joined.py'
QUERY = 'service/mcis_service/trajectory_exchange/registered_query.py'
CASE = 'SYN-XREPO-001'
UTC = '2026-02-01T12:01:40.000Z'

def require(value):
    if not value:
        raise ValueError('HANDOFF_NOT_VERIFIED')

def git_file(ref, path):
    return subprocess.check_output(['git', 'show', ref+':'+path], cwd=ROOT, stderr=subprocess.DEVNULL)

def projection(frame):
    require(type(frame) is dict and frame.get('caseId') == CASE and frame.get('alignedUtc') == UTC)
    vessels = frame.get('vessels')
    require(type(vessels) is list and len(vessels) == 2)
    out = []
    for vessel, identity, pointer in zip(vessels, ('SYN-VESSEL-A', 'SYN-VESSEL-B'), ('/points/7', '/points/12')):
        require(vessel.get('vesselId') == identity and vessel.get('status') == 'input_point')
        require(vessel.get('locator') == {'jsonPointer': pointer} and vessel.get('courseUsedAsHeading') is False)
        pin = vessel.get('original')
        require(type(pin) is dict and set(pin) == {'caseId','evidenceId','requestDigest','sourceSha256'})
        require(pin['caseId'] == CASE and type(pin['evidenceId']) is str and 0 < len(pin['evidenceId']) <= 200)
        for key in ('requestDigest','sourceSha256'):
            require(type(pin[key]) is str and re.fullmatch('[0-9a-f]{64}',pin[key]) is not None)
        heading = vessel.get('headingDeg')
        require(type(heading) is dict and set(heading) == {'value','kind'})
        if identity == 'SYN-VESSEL-A':
            require(heading == {'value': None, 'kind':'missing'})
        else:
            require(heading['kind'] == 'recorded' and type(heading['value']) in (int,float)
                    and math.isfinite(heading['value']) and 0 <= heading['value'] <= 360)
        out.append({'vesselId':identity,'evidenceId':pin['evidenceId'],
                    'requestDigest':pin['requestDigest'],'sourceSha256':pin['sourceSha256'],
                    'jsonPointer':pointer,'observation':{'field':'headingDeg',**heading}})
    return out

def main():
    require(sys.flags.isolated and not sys.flags.optimize and sys.getprofile() is None)
    harness = ROOT/HARNESS
    require(harness.read_bytes() == git_file(BASE,HARNESS))
    require(hashlib.sha256(harness.read_bytes()).hexdigest() == 'a71813661dfdf538ce040f8e1ee83dc0499df15ddf165683eb01f6616c9535d6')
    query_bytes = git_file(PRODUCT,QUERY)
    observed = []; joined = []; errors = []
    def observe(frame, event, returned):
        if event != 'return':
            return
        try:
            if frame.f_code.co_name == '_query_registered_pair' and type(returned) is dict and returned.get('alignedUtc') == UTC:
                filename = Path(frame.f_code.co_filename)
                require(filename.as_posix().endswith('/'+QUERY) and filename.read_bytes() == query_bytes)
                observed.append(projection(returned))
            if frame.f_code.co_name == 'test_four_frames_then_prepare_same_registration':
                require(Path(frame.f_code.co_filename) == harness)
                receipt = frame.f_globals.get('result')
                require(type(receipt) is dict)
                # Capture only fixed count/status fields; no raw frame, documents or session.
                joined.append({k:receipt.get(k) for k in ('result','caseId','prepareAccessAdded','finalAccess',
                    'custodyRows','auditRows','reportRows','snapshotFixtureRows','bindingTableExists',
                    'denialsNoExtraWrites','sameRegisteredPins','http','realLogin','generatorExecuted')})
        except Exception:
            errors.append(True)
    code = None
    # Suppress the fixture's own output; only the finite handoff below is emitted.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        sys.setprofile(observe)
        try:
            runpy.run_path(str(harness), run_name='__main__')
        except SystemExit as exc:
            code = exc.code
        finally:
            sys.setprofile(None)
    require(type(code) is int and code == 0 and not errors and len(observed) == len(joined) == 1)
    require(joined[0] == {'result':'PASS','caseId':CASE,'prepareAccessAdded':1,'finalAccess':9,
        'custodyRows':11,'auditRows':12,'reportRows':0,'snapshotFixtureRows':1,'bindingTableExists':False,
        'denialsNoExtraWrites':True,'sameRegisteredPins':True,'http':False,'realLogin':False,'generatorExecuted':False})
    print(json.dumps({'kind':'synthetic-test-only-ephemeral-handoff','fixtureCommit':BASE,
        'caseId':CASE,'alignedUtc':UTC,'vessels':observed[0],
        'custodyDelta':{'queryAccess':8,'prepareAccess':1,'observerAccess':0},
        'receipt':joined[0]},ensure_ascii=False,sort_keys=True))

if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('{"kind":"synthetic-test-only-ephemeral-handoff","result":"FAILED"}')
        raise SystemExit(1)
