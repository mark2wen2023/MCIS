"""Synthetic direct CLI regression. This is implementation self-test, not independent acceptance."""
import copy, hashlib, json, os, pathlib, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2]
CLI=ROOT/'tools/mcis-ecfc/mcis-ecfc.sh'
count=0
last_output_bytes=0

def run(value, success=True, raw=False):
 global count,last_output_bytes
 payload=value if raw else json.dumps(value,ensure_ascii=False,allow_nan=False).encode()
 proc=subprocess.run([str(CLI)],input=payload,capture_output=True,timeout=60)
 last_output_bytes=len(proc.stdout)
 assert last_output_bytes<=1048576
 response=json.loads(proc.stdout)
 assert proc.returncode==(0 if success else 4),(proc.returncode,proc.stderr,response)
 assert response['ok'] is success,response
 count+=1
 return response.get('result',response)

def node(i,kind='Event',time=None,lane=0):
 return dict(id=i,kind=kind,text='Synthetic vessel turns',timeSeconds=time,lane=lane,isPrimaryIncident=False,evidenceIds=[])
def request(nodes=None,edges=None):
 return dict(action='validate',draft=dict(scope='Synthetic chart',nodes=nodes or [],edges=edges or []))

sources=json.loads((ROOT/'tools/mcis-ecfc/out/build-manifest.json').read_text())['inputs'] if (ROOT/'tools/mcis-ecfc/out/build-manifest.json').exists() else {}
original={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources if p.startswith('unity/')}
empty=run(request());assert any(i['code']=='ECFC-E06' and i['isError'] for i in empty['issues'])
a=node('a',time=-1);b=node('b',time=1);b['isPrimaryIncident']=True;c=node('c','Condition',lane=1)
r=request([a,b,c],[dict(id='ab',from_='a')])
r['draft']['edges']=[{'id':'ab','from':'a','to':'b'},{'id':'cb','from':'c','to':'b'}]
out=run(r);assert out['edges']==[{'id':'ab','from':'a','to':'b','kind':'Sequence','bold':True},{'id':'cb','from':'c','to':'b','kind':'Influence','bold':False}];assert all(n['isPresumptive'] for n in out['nodes'])
assert out['nodes'][2]['timeSeconds'] is None
for t in (-315576000,315576000,0):
 q=request([node('t',time=t)]);assert run(q)['nodes'][0]['timeSeconds']==t
for t in (-315576001,315576001,'0',True):
 run(request([node('t',time=t)]),False)
for lane in (-5,5):run(request([node('t',lane=lane)]))
for lane in (-6,6,0.5,True):run(request([node('t',lane=lane)]),False)
for field,value in [('kind','Unknown'),('text',' '),('text','x'*1001),('id','a/b'),('id','x'*65),('isPrimaryIncident',1),('evidenceIds',['EV-001','EV-001']),('evidenceIds',['missing'])]:
 n=node('x');n[field]=value;run(request([n]),False)
run(request([node('x'),node('x')]),False)
for edges in [[{'id':'e','from':'x','to':'x'}],[{'id':'e','from':'x','to':'missing'}],[{'id':'e','from':'x','to':'y'},{'id':'f','from':'y','to':'x'}],[{'id':'e','from':'x','to':'y'},{'id':'f','from':'x','to':'y'}],[{'id':'e','from':'x','to':'y'},{'id':'e','from':'y','to':'z'}]]:
 run(request([node('x'),node('y'),node('z')],edges),False)
run(request([node('x'),node('y','Condition')],[{'id':'e','from':'x','to':'y'}]),False)
run(request([node('x','Condition'),node('y','Condition')],[{'id':'e','from':'x','to':'y'}]))
for key in ['scope','nodes','edges']:
 q=request();del q['draft'][key];run(q,False)
q=request();q['draft']['extra']=True;run(q,False)
q=request([node('x')]);q['draft']['nodes'][0]['isPresumptive']=False;run(q,False)
q=request([node('x')]);q['draft']['nodes'][0]['text']='😀'*1000;run(q)
q['draft']['nodes'][0]['text']='😀'*1001;run(q,False)
run(request([node('x'+str(i)) for i in range(40)]));run(request([node('x'+str(i)) for i in range(41)]),False)
for raw in [b'\xff',b'{}',b'{"action":"validate","action":"validate","draft":{"scope":"x","nodes":[],"edges":[]}}',b'{"action":"validate","draft":{"scope":"\\ud800","nodes":[],"edges":[]}}',b'{"\\ud800":0}',b'{"action":"validate","draft":{"scope":"x","nodes":[{"id":"a","kind":"Event","text":"x","timeSeconds":1e999,"lane":0,"isPrimaryIncident":false,"evidenceIds":[]}],"edges":[]}}',b' '*131073]:run(raw,False,True)
# D2: valid UTF-8 input can expand past the old HTTP 256KiB stdout cap.
q=request([node('emoji'+str(i)) for i in range(25)])
for n in q['draft']['nodes']:n['text']='😀'*1000
assert len(json.dumps(q,ensure_ascii=False).encode())<131072
run(q);assert 256*1024<last_output_bytes<1048576
print('D2 25x1000 emoji output bytes:',last_output_bytes)
# Max professional diagnostic count: 40 off-main presumptive incident events.
q=request([node('worst'+str(i),lane=1) for i in range(40)])
for n in q['draft']['nodes']:n['text']='x'*1000;n['isPrimaryIncident']=True
out=run(q);assert len(out['issues'])==201
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in original.items())
print(f'{count} synthetic CLI cases passed; {len(original)} original core hashes unchanged')
