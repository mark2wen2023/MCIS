"""Isolated deterministic build of an adapter over unchanged Hfacs.cs."""
import fcntl, hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
HERE=pathlib.Path(__file__).resolve().parent
SDK='8.0.428'
INPUTS=['tools/mcis-hfacs/McisHfacs.csproj', 'tools/mcis-hfacs/src/Program.cs', 'unity/Assets/_Project/Scripts/Core/Primitives/Result.cs', 'unity/Assets/_Project/Scripts/Domain/HumanFactors/Hfacs.cs', 'unity/Assets/_Project/Scripts/Domain/Evidence/CustodyLedger.cs', 'unity/Assets/_Project/Scripts/Domain/Evidence/CustodyEvent.cs', 'unity/Assets/_Project/Scripts/Domain/Evidence/EvidenceItem.cs', 'unity/Assets/_Project/Scripts/Domain/Evidence/InvestigationAudit.cs', 'unity/Assets/_Project/Scripts/Domain/Evidence/Sha256Hex.cs']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
 dotnet=os.environ.get('MCIS_DOTNET',str(pathlib.Path.home()/'.dotnet/dotnet'))
 out=HERE/'out';out.mkdir(exist_ok=True)
 with (out/'.build.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if subprocess.check_output([dotnet,'--version'],text=True).strip()!=SDK: raise RuntimeError('SDK mismatch')
  receipt={'contract':'mcis-hfacs-build/1','sdk':SDK,'recipeSha256':sha(pathlib.Path(__file__)),
           'inputs':{p:sha(ROOT/p) for p in INPUTS},'configuration':'Release','pathMap':'/mcis-hfacs-source'}
  manifest=out/'build-manifest.json'
  if manifest.exists():
   prior=json.loads(manifest.read_text()); artifacts=prior.pop('artifacts',{})
   if prior==receipt and artifacts and all((out/p).is_file() and sha(out/p)==h for p,h in artifacts.items()): return
  with tempfile.TemporaryDirectory(prefix='mcis-hfacs-build-') as temp:
   tree=pathlib.Path(temp);(tree/'global.json').write_text(json.dumps({'sdk':{'version':SDK,'rollForward':'disable'}}))
   for p in INPUTS:
    dest=tree/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,dest)
   if any(sha(tree/p)!=h for p,h in receipt['inputs'].items()): raise RuntimeError('Input snapshot changed')
   output=tree/'artifacts'
   subprocess.run([dotnet,'build',str(tree/'tools/mcis-hfacs/McisHfacs.csproj'),'-c','Release','-o',str(output),'-v','q',
      '/p:Deterministic=true','/p:UseAppHost=false','/p:IncludeSourceRevisionInInformationalVersion=false',f'/p:PathMap={tree}=/mcis-hfacs-source'],cwd=tree,stdout=sys.stderr,check=True)
   if any(sha(ROOT/p)!=h for p,h in receipt['inputs'].items()): raise RuntimeError('Source changed during build')
   receipt['artifacts']={p.name:sha(p) for p in output.iterdir() if p.is_file()}
   for name in receipt['artifacts']:
    staging=out/(name+'.tmp');shutil.copyfile(output/name,staging);os.replace(staging,out/name)
   staging=out/'build-manifest.json.tmp';staging.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');os.replace(staging,manifest)
if __name__=='__main__':build()
