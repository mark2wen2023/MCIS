"""Offline intent inspection only. Never authority, readiness proof or execution."""
import argparse
import hashlib
import json
import re
import sys

SCHEMA='mcis.public-expert-execution-intent.v1'
PACKET_SHA='1dc5f6ccd93da013863abfd399b8e3f8682d2532e62d335eaa23cd5e18d8790e'
MAX_BYTES=4096
BLOCKERS=('browser_identity_and_authorization_unavailable',
          'trusted_platform_worker_binding_unavailable',
          'durable_budget_idempotency_and_cancel_unavailable',
          'trusted_intent_receipt_binding_unavailable',
          'real_execution_disabled')

class IntentError(ValueError):pass

def inspect(raw):
    try:
        if type(raw) is not bytes or len(raw)>MAX_BYTES:raise ValueError()
        def pairs(items):
            d={}
            for key,value in items:
                if key in d:raise ValueError()
                d[key]=value
            return d
        d=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,
                     parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
        if type(d) is not dict or set(d)!={'schema','intentId','operation','packetSha256'}:raise ValueError()
        if d['schema']!=SCHEMA or d['operation']!='prepare_public_two_round_review' or d['packetSha256']!=PACKET_SHA:raise ValueError()
        if type(d['intentId']) is not str or re.fullmatch('[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}',d['intentId']) is None:raise ValueError()
        canonical=json.dumps(d,sort_keys=True,separators=(',',':')).encode()
    except (ValueError,TypeError,UnicodeError,RecursionError):
        raise IntentError('intent_invalid') from None
    return {'schema':'mcis.public-expert-preflight.v1','intentId':d['intentId'],
            'intentSha256':hashlib.sha256(canonical).hexdigest(),'packetSha256':PACKET_SHA,
            'status':'blocked','executionAuthorized':False,'requestDispatched':False,
            'authenticityVerified':False,'isExecutionReceipt':False,'blockers':list(BLOCKERS),
            'proposedLimits':{'rounds':2,'modelAttempts':16,'toolCalls':32,'roleSeconds':120,'totalSeconds':600},
            'limitsReserved':False}

def main(argv=None):
    p=argparse.ArgumentParser(description='Offline BLOCKED preflight; never starts a model or reads credential configuration.')
    p.add_argument('--check-stdin',action='store_true',required=True)
    p.parse_args(argv)
    try:result=inspect(sys.stdin.buffer.read(MAX_BYTES+1))
    except (IntentError,OSError):
        print('{"status":"invalid","executionAuthorized":false,"requestDispatched":false}')
        return 2
    print(json.dumps(result,sort_keys=True,separators=(',',':')))
    return 2 # Valid intent still blocked, never report executable success.

if __name__=='__main__':raise SystemExit(main())
