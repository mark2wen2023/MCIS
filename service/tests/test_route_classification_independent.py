"""Independent route-inventory checks, not authentication verification."""
import copy
from types import SimpleNamespace
import pytest
from fastapi import FastAPI, APIRouter, Depends
from starlette.routing import Mount, Route, WebSocketRoute
from mcis_service.common.context import CtxDep, get_ctx
from mcis_service.security_inventory.routes import inspect_routes,verify,InventoryError
from tests.test_route_classification import classify


def test_multiple_nested_prefixes_and_own_router_prefix():
    a=FastAPI();outer=APIRouter(prefix='/outer');inner=APIRouter(prefix='/inner')
    @inner.get('/item')
    def endpoint():return {}
    outer.include_router(inner,prefix='/middle')
    a.include_router(outer,prefix='/api')
    paths=[r['path'] for r in inspect_routes(a)]
    assert '/api/outer/middle/inner/item' in paths
    assert verify(a,classify(a))['routes']==9


def test_mounted_application_nested_routes_are_not_omitted():
    a=FastAPI();sub=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    @sub.get('/secret',include_in_schema=False)
    def endpoint():return {}
    @sub.websocket('/socket')
    async def ws(socket):pass
    a.mount('/nested',sub)
    rows=inspect_routes(a)
    assert any(r['path']=='/nested' and r['protocol']=='mount' for r in rows)
    assert any(r['path']=='/nested/secret' for r in rows)
    assert any(r['path']=='/nested/socket' and r['protocol']=='websocket' for r in rows)
    manifest=classify(a)
    manifest['routes']=[r for r in manifest['routes'] if r['path']!='/nested/secret']
    with pytest.raises(InventoryError,match='ROUTE_SET_CHANGED'):verify(a,manifest)


def test_new_child_route_under_existing_mount_is_detected():
    a=FastAPI();sub=FastAPI();a.mount('/sub',sub);m=classify(a)
    @sub.get('/new',include_in_schema=False)
    def added():return {}
    with pytest.raises(InventoryError,match='ROUTE_SET_CHANGED'):verify(a,m)


def test_duplicate_manifest_entry_rejected():
    a=FastAPI();m=classify(a);m['routes'].append(copy.deepcopy(m['routes'][0]))
    with pytest.raises(InventoryError,match='DUPLICATE_ROUTE'):verify(a,m)


def test_real_context_dependency_removal_detected():
    a=FastAPI()
    @a.get('/ctx')
    def endpoint(ctx=CtxDep):return {}
    m=classify(a)
    assert next(r for r in m['routes'] if r['path']=='/ctx')['declaredContext']
    r=next(r for r in a.routes if getattr(r,'path',None)=='/ctx')
    r.dependant.dependencies=[]
    with pytest.raises(InventoryError,match='ROUTE_IMPLEMENTATION_OR_CONTEXT_CHANGED'):verify(a,m)


def test_included_dependencies_require_review_not_silent_ignore():
    a=FastAPI();r=APIRouter()
    @r.get('/item')
    def endpoint():return {}
    a.include_router(r,dependencies=[Depends(get_ctx)])
    with pytest.raises(InventoryError,match='INCLUDED_DEPENDENCIES_REQUIRE_REVIEW'):inspect_routes(a)


def test_unsupported_route_type_fail_closed():
    a=FastAPI();a.routes.append(object())
    with pytest.raises(InventoryError,match='UNSUPPORTED_ROUTE_TYPE'):inspect_routes(a)


def test_cyclic_tree_fails_closed():
    a=FastAPI()
    a.routes.append(SimpleNamespace(original_router=a.router,include_context=SimpleNamespace(prefix='',dependencies=())))
    with pytest.raises(InventoryError,match='CYCLIC_ROUTE_TREE'):inspect_routes(a)


def test_empty_manifest_cannot_certify_nonempty_app():
    a=FastAPI()
    with pytest.raises(InventoryError,match='ROUTE_SET_CHANGED'):
        verify(a,{'profile':'MCIS-ROUTE-CLASSIFICATION-1','routes':[]})


def test_endpoint_behavior_or_dependency_override_not_certified():
    a=FastAPI()
    @a.get('/ctx')
    def endpoint(ctx=CtxDep):return {}
    m=classify(a)
    a.dependency_overrides[get_ctx]=lambda:None
    r=verify(a,m)
    assert not r['authenticationVerified'] and not r['enforcementPerformed']
    # This inventory is structural, not a validator of middleware/override safety.
