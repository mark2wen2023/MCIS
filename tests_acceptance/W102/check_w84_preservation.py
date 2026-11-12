"""Independent exact preservation check against W8.4 v2 frozen digests."""
from pathlib import Path
import hashlib,json,re,tempfile
import yaml
from mcis_service.config import Settings
from mcis_service.main import create_app
ROOT=Path(__file__).resolve().parents[2]
results=[]
def digest(b):return hashlib.sha256(b).hexdigest()
def check(name,ok):
 results.append({'name':name,'passed':bool(ok)});assert ok,name
expected={}
for line in (ROOT/'logs/w84-backend-hashes-frozen-v2.txt').read_text().splitlines():
 h,p=line.split('  ',1);expected[p]=h
 if p not in ('contracts/openapi.yaml','service/mcis_service/main.py'):check('W8.4 nonshared backend '+p,digest((ROOT/p).read_bytes())==h)
for line in (ROOT/'logs/w84-ui-hashes-frozen-v2.txt').read_text().splitlines():
 h,p=line.split('  ',1);check('W8.4 UI '+p,digest((ROOT/p).read_bytes())==h)
main=(ROOT/'service/mcis_service/main.py').read_text()
stripped=main.replace('from .tracks_import.router import router as tracks_import_router\n','').replace('    app.include_router(tracks_import_router)  # W10.2 explicit CSV first-track input\n','')
check('main stripped W10 two lines exact W8.4 frozen hash',digest(stripped.encode())==expected['service/mcis_service/main.py'])
api=(ROOT/'contracts/openapi.yaml').read_text()
stripped=re.sub(r'^    TrackImportInput:\n.*?(?=^    Case:)', '',api,flags=re.M|re.S)
stripped=re.sub(r'^  /api/v1/cases/\{caseId\}/track-imports:preview:\n.*?(?=^  /api/v1/knowledge/cards:)', '',stripped,flags=re.M|re.S)
check('openapi stripped four schemas five paths exact W8.4 frozen hash',digest(stripped.encode())==expected['contracts/openapi.yaml'])
spec=yaml.safe_load(api)
check('contract metadata GET PATCH retained',{'get','patch'}<=set(spec['paths']['/api/v1/cases/{caseId}/metadata']))
with tempfile.TemporaryDirectory(prefix='w102-independent-schema-') as d:
 app=create_app(Settings(data_dir=Path(d),seed_demo=False))
 check('runtime metadata GET PATCH retained',{'get','patch'}<=set(app.openapi()['paths']['/api/v1/cases/{case_id}/metadata']))
print(json.dumps({'passed':len(results),'failed':0,'checks':results},indent=2))
