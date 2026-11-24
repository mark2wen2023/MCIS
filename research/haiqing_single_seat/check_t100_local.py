"""Local controls: T124 existing pure path + malformed T100 only; no T100 positive."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
def module(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main(root):
    path=Path(__file__).with_name('seat_note.py')
    old=path.read_bytes().split(b'# T100 is a separate test-only typed entry.')[0].rstrip()+b'\n'
    # Original source ends with one newline. Verify old entry's exact bytes.
    assert hashlib.sha1(b'blob '+str(len(old)).encode()+b'\0'+old).hexdigest()=='4d678d13361e5c29442252321f299aec842742fc'
    seat=module('seat',path)
    fixed=module('fixed',root/'e0cbccc83b13598c7ff118798ec7c56e472d413b/tests_acceptance/registered-trajectory-pair/seat_receiver/fixed_objects.py')
    project,host,docs=fixed.verified_modules({k:(root/ref/name).read_bytes() for k,(ref,name,_) in fixed.FILES.items()})
    pins=[dict(caseId=seat.CASE,evidenceId='SYN-E-'+s,requestDigest=d*64,sourceSha256=hashlib.sha256((root/fixed.FILES[k][0]/fixed.FILES[k][1]).read_bytes()).hexdigest()) for s,d,k in [('A','a','a'),('B','b','b')]]
    frame=dict(caseId=seat.CASE,alignedUtc=seat.UTC,vessels=[project._point_from_committed_original(dict(document=d,pin=p),project._stamp(seat.UTC)) for d,p in zip(docs,pins)])
    packet,refs=seat.prepare(frame,trusted_pins=pins)
    args={'reviews':[dict(itemId=i['itemId'],label='insufficient',quote=i['sourceText'],rationale=seat.CLAIM,uncertainty=seat.LIMIT) for i in packet['items']]}
    out=seat.handoff(host._validate,args,frame=frame,trusted_pins=pins)
    assert out['references']==refs and refs['item_002'] is None
    assert out['saved'] is False and out['factActivated'] is False
    count=0
    for pending,c,p in [(None,seat.T100_CONSUMER,seat.T100_PRODUCER),({},seat.T100_CONSUMER,seat.T100_PRODUCER),({},'wrong',seat.T100_PRODUCER)]:
        try:seat.bind_t100_test_receipt(pending,consumer_commit=c,producer_commit=p)
        except seat.ScopeError:count+=1
        else:raise AssertionError('invalid binding accepted')
    print(json.dumps({'oldEntryBytesUnchanged':True,'T124PureHandoff':1,'T100MalformedRejected':count,'T100RealPositive':'NOT_RUN'}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dependencies',type=Path,required=True);main(p.parse_args().dependencies)
