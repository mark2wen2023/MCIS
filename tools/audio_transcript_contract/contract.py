"""Offline strict sidecar consistency only; supplied snapshots are NOT authorization."""
import hashlib,json,re
PROFILE='MCIS-AUDIO-TRANSCRIPT-1'
class Invalid(ValueError):pass
def need(ok):
 if not ok:raise Invalid('INVALID_AUDIO_SIDECAR')
def exact(d,keys):need(type(d)is dict and set(d)==set(keys.split()))
def text(s,n=200):need(type(s)is str and 0<len(s)<=n and not any(ord(c)<32 or ord(c)==127 or 0xD800<=ord(c)<=0xDFFF for c in s))
def sha(s):need(type(s)is str and re.fullmatch('[0-9a-f]{64}',s) is not None)
def integer(v,lo,hi):need(type(v)is int and lo<=v<=hi)
def canonical(d):
 try:return json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
 except (TypeError,ValueError,UnicodeError,RecursionError):raise Invalid('INVALID_AUDIO_SIDECAR') from None
def digest(d):return hashlib.sha256(canonical(d)).hexdigest()
def validate(d):
 exact(d,'profile version source transcript artifactSha256')
 need(d['profile']==PROFILE and type(d['version'])is int and d['version']==1)
 s=d['source'];exact(s,'caseId evidenceId registeredSha256 currentSha256 stateDigest durationMs trackIndex')
 for k in ('caseId','evidenceId'):text(s[k])
 for k in ('registeredSha256','currentSha256','stateDigest'):sha(s[k])
 integer(s['durationMs'],1,3600000);integer(s['trackIndex'],0,255)
 t=d['transcript'];exact(t,'revision parentArtifactSha256 method segments unlocatedSegments reviewStatus timeBasis')
 integer(t['revision'],1,1000000)
 if t['revision']==1:need(t['parentArtifactSha256'] is None)
 else:sha(t['parentArtifactSha256'])
 need(t['method']=='manual_transcription' and t['reviewStatus']=='pending' and t['timeBasis']=='original_audio_ms')
 # v1 deliberately does not claim a model ran. ASR receipts require a future version.
 need(type(t['segments'])is list and type(t['unlocatedSegments'])is list and 1<=len(t['segments'])+len(t['unlocatedSegments'])<=256)
 ids=set()
 for located,rows in ((True,t['segments']),(False,t['unlocatedSegments'])):
  for row in rows:
   exact(row,'id text speaker startMs endMs' if located else 'id text speaker reason')
   text(row['id']);need(row['id'] not in ids);ids.add(row['id']);text(row['text'],16000)
   exact(row['speaker'],'status id');need(row['speaker']=={'status':'unknown','id':None})
   if located:
    integer(row['startMs'],0,s['durationMs']);integer(row['endMs'],1,s['durationMs']);need(row['startMs']<row['endMs'])
   else:need(row['reason'] in ('time_unknown','alignment_pending'))
 sha(d['artifactSha256']);need(d['artifactSha256']==digest({k:v for k,v in d.items() if k!='artifactSha256'}))
 need(len(canonical(d))<=262144)
 return json.loads(canonical(d))
def compare(d,current):
 d=validate(d)
 out={'profile':PROFILE,'status':'unknown','admissionAllowed':False,'authorizationVerified':False,'asrExecuted':False}
 if current is None:return out
 exact(current,'caseId evidenceId currentSha256 stateDigest artifactSha256')
 for k in ('caseId','evidenceId'):text(current[k])
 for k in ('currentSha256','stateDigest','artifactSha256'):sha(current[k])
 if any(current[k]!=d['source'][k] for k in ('caseId','evidenceId')):raise Invalid('SOURCE_SCOPE_MISMATCH')
 stale=any(current[k]!=d['source'][k] for k in ('currentSha256','stateDigest')) or current['artifactSha256']!=d['artifactSha256']
 out['status']='stale' if stale else 'supplied_snapshot_matches_not_authenticated'
 return out
