"""Run only on the existing authorized Linux producer checkout; no fetch/install."""
import argparse,contextlib,copy,hashlib,importlib.util,io,json,os,subprocess,sys
from pathlib import Path
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main(repo,python):
    seat=load('seat',Path(__file__).with_name('seat_note.py'))
    path='tests_acceptance/registered-trajectory-pair/consume_joined_t100.py'
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_OPTIONAL_LOCKS='0')
    p=subprocess.run(['git','-C',str(repo),'--no-replace-objects','show',seat.T100_CONSUMER+':'+path],capture_output=True,env=env)
    if p.returncode:raise RuntimeError('MISSING_PINNED_CONSUMER')
    raw=p.stdout
    if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!='47d5a06fe01ce3858e8b9a731fbc64fabd8aa8bf' or (repo/path).read_bytes()!=raw:
        raise RuntimeError('CONSUMER_BYTES')
    consumer=load('fixed_consumer',repo/path)
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture):
        consumer.run(repo,python) # real producer once, existing 1 positive / 11 negative
    receipt=consumer.strict(capture.getvalue())
    if receipt['producerCommit']!=seat.T100_PRODUCER or receipt['positive']!=1 or receipt['negative']!=11:
        raise RuntimeError('CONSUMER_RESULT')
    pending=receipt['output'];before=copy.deepcopy(pending)
    accept=seat.bind_t100_test_receipt(pending,consumer_commit=seat.T100_CONSUMER,producer_commit=receipt['producerCommit'])
    note=accept(pending)
    assert note['observations']==pending['observations'] and note['saved'] is False and note['factActivated'] is False
    assert note['turnConclusion'] is None and note['causation'] is None
    edits=[lambda x:x['observations'].reverse(),
           lambda x:x['observations'][0]['observation'].update(value=90,kind='recorded'),
           lambda x:x['observations'][1]['observation'].update(value=360),
           lambda x:x['observations'][0].update(requestDigest='0'*64),
           lambda x:x.update(reviewState='confirmed')]
    for edit in edits:
        bad=copy.deepcopy(pending);edit(bad)
        try:accept(bad)
        except seat.ScopeError:pass
        else:raise AssertionError('mutated handoff accepted')
    assert pending==before
    note['observations'].clear()
    assert accept(pending)['observations']==before['observations']
    print(json.dumps({'status':'PASS','producerStdoutSha256':receipt['producerStdoutSha256'],
      'producerCommit':seat.T100_PRODUCER,'consumerCommit':seat.T100_CONSUMER,
      'upstreamPositive':1,'upstreamNegative':11,'seatPositive':1,'seatNegative':5,
      'copyIsolation':True,'model':False,'saved':False},sort_keys=True))
if __name__=='__main__':
    if not sys.flags.isolated or sys.flags.optimize:raise SystemExit('Use python -I -B, no -O')
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--python',type=Path,required=True);a=p.parse_args()
    main(a.repo.resolve(),a.python.absolute()) # preserve venv symlink path
