"""Independent drift checks; all execution is offline synthetic construction."""
import copy
from fastapi import FastAPI, APIRouter
import pytest
from mcis_service.security_inventory.drift import runtime_surface, callable_shape, verify_drift, snapshot
from mcis_service.security_inventory.routes import InventoryError
from tests.test_route_drift import app_at, ROOT


def test_same_name_dependency_bytecode_replacement_detected():
    app=FastAPI()
    @app.get('/sample')
    def sample():return 'original'
    before=runtime_surface(app)
    def replacement():return 'changed'
    replacement.__module__=sample.__module__;replacement.__qualname__=sample.__qualname__
    next(r for r in app.routes if getattr(r,'path',None)=='/sample').dependant.call=replacement
    assert runtime_surface(app)!=before


def test_external_override_provider_rejected():
    app=FastAPI()
    @app.get('/sample')
    def sample():return 1
    route=next(r for r in app.routes if getattr(r,'path',None)=='/sample')
    route.dependency_overrides_provider=FastAPI()
    with pytest.raises(InventoryError,match='EXTERNAL_OVERRIDE_PROVIDER'):runtime_surface(app)


def test_new_python_minor_cannot_silently_reuse_baseline(tmp_path):
    app=app_at(tmp_path);baseline=snapshot(app,ROOT)
    baseline['runtime']['python']=[3,99]
    with pytest.raises(InventoryError,match='RUNTIME_DRIFT'):verify_drift(app,ROOT,baseline)


def test_route_order_change_detected_even_same_inventory(tmp_path):
    app=app_at(tmp_path);baseline=snapshot(app,ROOT)
    app.routes[0],app.routes[1]=app.routes[1],app.routes[0]
    with pytest.raises(InventoryError,match='RUNTIME_DRIFT'):verify_drift(app,ROOT,baseline)


def test_nonfinite_middleware_value_not_silently_hashed(tmp_path):
    app=app_at(tmp_path);app.user_middleware[0].kwargs['value']=float('nan')
    with pytest.raises(InventoryError,match='UNINSPECTABLE_VALUE'):runtime_surface(app)


def test_mutable_global_and_defaults_are_not_certified():
    namespace={'state':1,'__name__':'independent_fixture'}
    exec('def handler(value=1):\n return state + value\n',namespace)
    handler=namespace['handler']
    before=callable_shape(handler)
    namespace['state']=999;handler.__defaults__=(200,)
    assert callable_shape(handler)==before
    assert handler()==1199


def test_checkout_filename_and_line_relocation_do_not_change_shape():
    namespace={'__name__':'independent_fixture'}
    exec(compile('def handler():\n return 1\n','/one/checkout.py','exec'),namespace)
    handler=namespace['handler'];before=callable_shape(handler)
    handler.__code__=handler.__code__.replace(co_filename='/another/location.py',co_firstlineno=999)
    assert callable_shape(handler)==before


def test_success_flags_never_claim_identity_or_revocation(tmp_path):
    app=app_at(tmp_path);baseline=snapshot(app,ROOT)
    result=verify_drift(app,ROOT,baseline)
    assert result['authenticationVerified'] is False
    assert result['authorizationVerified'] is False
    assert any('revocation' in text for text in result['unverified'])
    assert any('defaults' in text for text in result['unverified'])


def test_websocket_same_name_callable_change_detected():
    app=FastAPI()
    @app.websocket('/ws')
    async def ws(websocket):return 1
    before=runtime_surface(app)
    async def changed(websocket):return 2
    changed.__module__=ws.__module__;changed.__qualname__=ws.__qualname__
    route=next(r for r in app.routes if getattr(r,'path',None)=='/ws')
    route.endpoint=changed
    assert runtime_surface(app)!=before
    route.dependency_overrides_provider=FastAPI()
    with pytest.raises(InventoryError,match='EXTERNAL_OVERRIDE_PROVIDER'):runtime_surface(app)


def test_missing_selected_source_refuses_snapshot(tmp_path):
    from mcis_service.security_inventory.drift import source_surface
    root=tmp_path/'source';root.mkdir()
    with pytest.raises(InventoryError,match='SOURCE_FILE_MISSING'):source_surface(root,FastAPI())


def test_selected_source_byte_change_detected(tmp_path):
    root=tmp_path/'source';root.mkdir()
    for name in ('main.py','config.py','common/context.py','security_inventory/routes.py','security_inventory/drift.py'):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# local fixture\n')
    app=FastAPI();baseline=snapshot(app,root)
    (root/'config.py').write_text('# changed fixture comment\n')
    with pytest.raises(InventoryError,match='SOURCE_DRIFT'):verify_drift(app,root,baseline)
