"""Bounded non-sensitive protocol only. No app, clock, files or credentials."""
import json
import re
BASELINE='0a7232c6a24adb52720d9d65438fc1b0cf537a29'
BUILD='sha256:b8750f27a2ff71d11c39ea091f0187917ea141d587a4c342de07d0932e220aca'
SCHEMA='mcis.synthetic-image-acceptance/1'
LIMIT=2048
STAGES=('preflight','https_ready','cases_zero_runs','four_receipts','first_import','save_reopen','authorized_switch','cleanup')

class Receipt:
    def __init__(self,image):
        self.value={'schema':SCHEMA,'productBaseline':BASELINE,'build':BUILD,
            'image':image if isinstance(image,str) and re.fullmatch('sha256:[0-9a-f]{64}',image) else None,
            'stages':{s:'pending' for s in STAGES},'exitCode':2,'cleanup':'unknown',
            'containerExitCode':None,'containerCleanup':'unknown','result':'not_passed'}
    def mark(self,stage):
        if stage not in STAGES[:-1] or any(self.value['stages'][s]!='passed' for s in STAGES[:STAGES.index(stage)]):
            raise ValueError('invalid stage order')
        self.value['stages'][stage]='passed'
    def cleaned(self):
        self.value['cleanup']='confirmed';self.value['stages']['cleanup']='passed'
    def finish(self,success):
        if success and all(v=='passed' for v in self.value['stages'].values()):self.value['exitCode']=0
        else:
            for s in STAGES:
                if self.value['stages'][s]=='pending':self.value['stages'][s]='failed';break
        return encode(self.value)

def encode(value):
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode('ascii')
    if len(raw)>LIMIT:raise ValueError('receipt too long')
    return raw

def parse(raw,image):
    if not isinstance(raw,bytes) or len(raw)>LIMIT or raw.count(b'\n')!=1 or not raw.endswith(b'\n'):
        raise ValueError('not one bounded record')
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise ValueError('duplicate key')
            d[k]=v
        return d
    d=json.loads(raw,object_pairs_hook=unique)
    expected=Receipt(image).value
    if not isinstance(d,dict) or set(d)!=set(expected):raise ValueError('unknown fields')
    for k in ('schema','productBaseline','build','image','containerExitCode','containerCleanup','result'):
        if d[k]!=expected[k]:raise ValueError('unconfirmed identity or envelope')
    if type(d['exitCode']) is not int or d['exitCode'] not in (0,2) or d['cleanup'] not in ('confirmed','unknown'):raise ValueError('invalid result')
    if not isinstance(d['stages'],dict) or set(d['stages'])!=set(STAGES):raise ValueError('invalid stages')
    values=[d['stages'][s] for s in STAGES[:-1]]
    if any(v not in ('pending','passed','failed') for v in values):raise ValueError('invalid stage state')
    tail=False;failed=0
    for v in values:
        if v!='passed':tail=True
        elif tail:raise ValueError('out of order')
        failed+=v=='failed'
    if failed>1 or d['stages']['cleanup'] not in ('pending','passed','failed'):raise ValueError('invalid failure')
    if (d['stages']['cleanup']=='passed')!=(d['cleanup']=='confirmed'):raise ValueError('cleanup mismatch')
    if d['exitCode']==0 and (any(v!='passed' for v in d['stages'].values()) or d['cleanup']!='confirmed'):raise ValueError('false success')
    if encode(d)!=raw:raise ValueError('noncanonical/multiple record')
    return d
