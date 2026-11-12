"""Isolated deterministic build of an adapter over unchanged BowTie.cs."""
import fcntl, hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
HERE=pathlib.Path(__file__).resolve().parent
SDK='8.0.428'
INPUTS=['tools/mcis-nomoto/McisNomoto.csproj', 'tools/mcis-nomoto/src/Program.cs', 'unity/Assets/_Project/Scripts/Simulation/WhatIf/NomotoSimulator.cs', 'unity/Assets/_Project/Scripts/Simulation/WhatIf/WhatIfTypes.cs', 'unity/Assets/_Project/Scripts/Simulation/WhatIf/SourcedValue.cs', 'unity/Assets/_Project/Scripts/Core/Primitives/SimTime.cs', 'unity/Assets/_Project/Scripts/Domain/Common/EnuAndEnums.cs', 'unity/Assets/_Project/Scripts/Domain/Common/GeoPrimitives.cs', 'unity/Assets/_Project/Scripts/Domain/Models/TrackAndCpaModels.cs', 'unity/Assets/_Project/Scripts/Domain/Models/VesselAndAisModels.cs', 'unity/Assets/_Project/Scripts/Domain/Cpa/CpaModels.cs', 'unity/Assets/_Project/Scripts/Domain/Tracks/TrackContracts.cs', 'unity/Assets/_Project/Scripts/Domain/Geo/IGeoConverter.cs', 'unity/Assets/_Project/Scripts/Domain/Geo/GeoMath.cs', 'unity/Assets/_Project/Scripts/Simulation/Damage/OrientedBoundingBox.cs']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
 dotnet=os.environ.get('MCIS_DOTNET',str(pathlib.Path.home()/'.dotnet/dotnet'))
 out=HERE/'out';out.mkdir(exist_ok=True)
 with (out/'.build.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if subprocess.check_output([dotnet,'--version'],text=True).strip()!=SDK: raise RuntimeError('SDK mismatch')
  receipt={'contract':'mcis-nomoto-build/1','sdk':SDK,'recipeSha256':sha(pathlib.Path(__file__)),
           'inputs':{p:sha(ROOT/p) for p in INPUTS},'configuration':'Release','pathMap':'/mcis-nomoto-source'}
  manifest=out/'build-manifest.json'
  if manifest.exists():
   prior=json.loads(manifest.read_text()); artifacts=prior.pop('artifacts',{})
   if prior==receipt and artifacts and all((out/p).is_file() and sha(out/p)==h for p,h in artifacts.items()): return
  with tempfile.TemporaryDirectory(prefix='mcis-nomoto-build-') as temp:
   tree=pathlib.Path(temp);(tree/'global.json').write_text(json.dumps({'sdk':{'version':SDK,'rollForward':'disable'}}))
   for p in INPUTS:
    dest=tree/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,dest)
   if any(sha(tree/p)!=h for p,h in receipt['inputs'].items()): raise RuntimeError('Input snapshot changed')
   output=tree/'artifacts'
   subprocess.run([dotnet,'build',str(tree/'tools/mcis-nomoto/McisNomoto.csproj'),'-c','Release','-o',str(output),'-v','q',
      '/p:Deterministic=true','/p:UseAppHost=false','/p:IncludeSourceRevisionInInformationalVersion=false',f'/p:PathMap={tree}=/mcis-nomoto-source'],cwd=tree,stdout=sys.stderr,check=True)
   if any(sha(ROOT/p)!=h for p,h in receipt['inputs'].items()): raise RuntimeError('Source changed during build')
   receipt['artifacts']={p.name:sha(p) for p in output.iterdir() if p.is_file()}
   for name in receipt['artifacts']:
    staging=out/(name+'.tmp');shutil.copyfile(output/name,staging);os.replace(staging,out/name)
   staging=out/'build-manifest.json.tmp';staging.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');os.replace(staging,manifest)
if __name__=='__main__':build()
