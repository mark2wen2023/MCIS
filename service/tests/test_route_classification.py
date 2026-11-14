"""Build-time manifest verification, not identity/authorization acceptance."""
import copy,json
from pathlib import Path
import pytest
from fastapi import FastAPI,APIRouter
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.security_inventory.routes import inspect_routes,verify,InventoryError
MANIFEST=Path(__file__).parents[2]/'contracts/route-classification.json'
def classify(app):
 return dict(profile='MCIS-ROUTE-CLASSIFICATION-1',routes=[
  dict(r,scope='case' if '{case_id}' in r['path'] else 'global',
       operation='read',rationale='Explicit synthetic test classification')
  for r in inspect_routes(app)])
def test_current_main_classified(tmp_path):
 a=create_app(Settings(data_dir=tmp_path,seed_demo=False))
 result=verify(a,json.loads(MANIFEST.read_text()))
 assert result['routes']==161 and result['declaredContext']==149
 assert not result['authenticationVerified'] and not result['enforcementPerformed']
def test_added_hidden_route_fails():
 a=FastAPI();m=classify(a)
 @a.get('/hidden',include_in_schema=False)
 def hidden():return {}
 with pytest.raises(InventoryError,match='ROUTE_SET_CHANGED'):verify(a,m)
def test_websocket_requires_classification():
 a=FastAPI();m=classify(a)
 @a.websocket('/ws')
 async def ws(websocket):pass
 with pytest.raises(InventoryError):verify(a,m)
 assert any(r['protocol']=='websocket' for r in inspect_routes(a))
 assert verify(a,classify(a))['authenticationVerified'] is False
def test_static_mount_requires_classification(tmp_path):
 a=FastAPI();m=classify(a);a.mount('/files',StaticFiles(directory=tmp_path))
 with pytest.raises(InventoryError):verify(a,m)
 assert any(r['protocol']=='mount' and r['path']=='/files' for r in inspect_routes(a))
def test_nested_router_prefix_visible():
 a=FastAPI();r=APIRouter()
 @r.get('/item')
 def endpoint():return {}
 a.include_router(r,prefix='/nested')
 assert any(x['path']=='/nested/item' for x in inspect_routes(a))
 assert verify(a,classify(a))['routes']==9
def test_omitted_classification_fails():
 a=FastAPI();m=classify(a);m['routes'].pop()
 with pytest.raises(InventoryError):verify(a,m)
def test_wrong_context_detected():
 a=FastAPI();m=classify(a);m['routes'][0]['declaredContext']=True
 with pytest.raises(InventoryError):verify(a,m)
def test_changed_endpoint_detected():
 a=FastAPI();m=classify(a);m['routes'][0]['endpoint']='other.function'
 with pytest.raises(InventoryError):verify(a,m)
@pytest.mark.parametrize('field',['scope','operation','rationale'])
def test_unclassified_field_fails(field):
 a=FastAPI();m=classify(a);del m['routes'][0][field]
 with pytest.raises(InventoryError):verify(a,m)
def test_duplicate_endpoint_cannot_hide():
 a=FastAPI()
 @a.get('/same')
 def one():return {}
 @a.get('/same')
 def two():return {}
 with pytest.raises(InventoryError,match='DUPLICATE_ROUTE'):verify(a,classify(a))
def test_new_method_fails():
 a=FastAPI();m=classify(a)
 @a.post('/docs')
 def unexpected():return {}
 with pytest.raises(InventoryError):verify(a,m)
def test_bypass_no_context_is_visible():
 a=FastAPI()
 @a.get('/cases/{case_id}/raw')
 def raw(case_id:str):return {}
 rows=inspect_routes(a);row=next(r for r in rows if r['path'].endswith('/raw'))
 assert not row['declaredContext']
 m=classify(a)
 assert verify(a,m)['authenticationVerified'] is False
