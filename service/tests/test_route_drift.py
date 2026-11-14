"""Offline change detection, not authorization tests or real model evaluation."""
import copy
import json
from pathlib import Path
import pytest
from fastapi import FastAPI
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.common.context import get_ctx
from mcis_service.security_inventory.drift import snapshot, runtime_surface, verify_drift
from mcis_service.security_inventory.routes import InventoryError
ROOT=Path(__file__).parents[1]/'mcis_service'
BASE=Path(__file__).parents[2]/'contracts/route-drift.json'

def app_at(tmp_path):return create_app(Settings(data_dir=tmp_path,seed_demo=False))
def test_reviewed_build(tmp_path):
 result=verify_drift(app_at(tmp_path),ROOT,json.loads(BASE.read_text()))
 assert result['reviewedSurfaceUnchanged']
 assert not result['authenticationVerified'] and not result['authorizationVerified']
 assert result['unverified']
def test_override_rejected(tmp_path):
 app=app_at(tmp_path);b=snapshot(app,ROOT)
 app.dependency_overrides[get_ctx]=lambda:'forged'
 with pytest.raises(InventoryError,match='DEPENDENCY_OVERRIDES'):verify_drift(app,ROOT,b)
def test_middleware_added(tmp_path):
 app=app_at(tmp_path);b=snapshot(app,ROOT)
 @app.middleware('http')
 async def bypass(request,call_next):return await call_next(request)
 with pytest.raises(InventoryError,match='RUNTIME_DRIFT'):verify_drift(app,ROOT,b)
def test_middleware_option_changed(tmp_path):
 app=app_at(tmp_path);b=snapshot(app,ROOT)
 app.user_middleware[0].kwargs['allow_origins']=['*']
 with pytest.raises(InventoryError,match='RUNTIME_DRIFT'):verify_drift(app,ROOT,b)
def test_same_name_handler_replacement():
 app=FastAPI()
 @app.get('/resource')
 def resource():return {'access':'old'}
 before=runtime_surface(app)
 def replacement():return {'access':'new'}
 replacement.__module__=resource.__module__;replacement.__qualname__=resource.__qualname__
 next(r for r in app.routes if getattr(r,'path',None)=='/resource').endpoint=replacement
 assert runtime_surface(app)!=before
 # Patching actual compiled dependency callable is separately observed.
 route=next(r for r in app.routes if getattr(r,'path',None)=='/resource')
 route.endpoint=resource;route.dependant.call=replacement
 assert runtime_surface(app)!=before
@pytest.mark.parametrize('mutate',[
 lambda b:b['runtime'].__setitem__('python',[0,0]),
 lambda b:b['source'].__setitem__('main.py','forged'),
 lambda b:b['source'].pop('main.py'),
])
def test_manifest_drift(tmp_path,mutate):
 app=app_at(tmp_path);b=snapshot(app,ROOT);mutate(b)
 with pytest.raises(InventoryError,match='DRIFT'):verify_drift(app,ROOT,b)
def test_opaque_config_rejects(tmp_path):
 app=app_at(tmp_path);app.user_middleware[0].kwargs['opaque']=object()
 with pytest.raises(InventoryError,match='UNINSPECTABLE'):runtime_surface(app)
def test_mount_requires_review():
 app=FastAPI();app.mount('/other',FastAPI())
 with pytest.raises(InventoryError,match='MOUNT_RUNTIME'):runtime_surface(app)
def test_prebuilt_stack_requires_review(tmp_path):
 app=app_at(tmp_path);app.middleware_stack=object()
 with pytest.raises(InventoryError,match='ALREADY_BUILT'):runtime_surface(app)
def test_closure_state_is_explicit_limit():
 value={'v':1};app=FastAPI()
 @app.get('/x')
 def x():return value['v']
 before=runtime_surface(app);value['v']=2
 assert runtime_surface(app)==before  # Known limitation, not an authorization pass.
def test_bad_baseline(tmp_path):
 with pytest.raises(InventoryError,match='INVALID_DRIFT'):verify_drift(app_at(tmp_path),ROOT,{})
