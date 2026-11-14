"""Offline review gate. Does not authenticate, authorize, or run in the service."""
import hashlib
import inspect
import json
import math
import sys
import types
from pathlib import Path
from starlette.routing import Mount, Route, WebSocketRoute
from .routes import InventoryError, endpoint_name, inspect_routes


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def code_shape(code):
    # Exclude file locations/line tables: moving a checkout is not a behavior change.
    return {key: encode(getattr(code, key)) for key in (
        'co_code', 'co_consts', 'co_names', 'co_varnames', 'co_freevars',
        'co_cellvars', 'co_argcount', 'co_posonlyargcount', 'co_kwonlyargcount',
        'co_nlocals', 'co_stacksize', 'co_flags', 'co_exceptiontable')}


def encode(value):
    if value is None or type(value) in (str, int, bool): return value
    if type(value) is float and math.isfinite(value): return {'float': value.hex()}
    if type(value) is bytes: return {'bytes': value.hex()}
    if type(value) is types.CodeType: return {'code': code_shape(value)}
    if value is Ellipsis: return {'ellipsis': True}
    if type(value) in (list, tuple): return {type(value).__name__: [encode(v) for v in value]}
    if type(value) is frozenset:
        return {'frozenset': sorted([encode(v) for v in value], key=lambda v: json.dumps(v, sort_keys=True))}
    if type(value) is dict and all(type(k) is str for k in value):
        return {'dict': {k: encode(v) for k,v in value.items()}}
    if isinstance(value, types.FunctionType): return {'callable': callable_shape(value)}
    raise InventoryError('UNINSPECTABLE_VALUE_REQUIRES_REVIEW')


def callable_shape(call):
    if not isinstance(call, types.FunctionType):
        raise InventoryError('UNINSPECTABLE_CALLABLE_REQUIRES_REVIEW')
    # Closure cells/global values are not claimed verified: often include a whole app.
    return {'name': endpoint_name(call), 'code': digest(code_shape(call.__code__)),
            'closureNames': list(call.__code__.co_freevars)}


def runtime_surface(app):
    if getattr(app, 'dependency_overrides', None):
        raise InventoryError('DEPENDENCY_OVERRIDES_REQUIRE_REVIEW')
    if getattr(app, 'middleware_stack', None) is not None:
        raise InventoryError('ALREADY_BUILT_STACK_REQUIRES_REVIEW')
    inspect_routes(app)  # Retain SEC01 fail-closed unsupported-tree handling.
    middleware=[]
    for m in app.user_middleware:
        middleware.append({'class': endpoint_name(m.cls), 'args': encode(m.args), 'kwargs': encode(m.kwargs)})
    rows=[]
    def deps(dep):
        if dep is None: return None
        return {'call': callable_shape(dep.call) if dep.call else None,
                'children': [deps(d) for d in dep.dependencies]}
    def walk(routes, prefix=''):
        for r in routes:
            if hasattr(r, 'original_router'):
                provider = getattr(r.original_router, 'dependency_overrides_provider', None)
                if provider is not None and provider is not app:
                    raise InventoryError('EXTERNAL_OVERRIDE_PROVIDER_REQUIRES_REVIEW')
                walk(r.original_router.routes, prefix + getattr(r.include_context, 'prefix', ''))
                continue
            path=prefix+getattr(r, 'path', '')
            if isinstance(r, Mount):
                # Opaque/nested ASGI apps need independent verification, not a name-only hash.
                raise InventoryError('MOUNT_RUNTIME_REQUIRES_REVIEW')
            if isinstance(r, (Route, WebSocketRoute)):
                provider=getattr(r, 'dependency_overrides_provider', None)
                if provider is not None and provider is not app:
                    raise InventoryError('EXTERNAL_OVERRIDE_PROVIDER_REQUIRES_REVIEW')
                rows.append({'path':path, 'methods':sorted(getattr(r,'methods',None) or ['CONNECT']),
                             'endpoint':callable_shape(r.endpoint),
                             'dependencies':deps(getattr(r,'dependant',None))})
    walk(app.routes)
    return {'python':list(sys.version_info[:2]), 'middleware':middleware, 'routes':rows}


def source_surface(root, app):
    root=Path(root)
    if not root.is_dir() or root.is_symlink(): raise InventoryError('INVALID_SOURCE_ROOT')
    result={}
    selected={root/'main.py', root/'config.py', root/'common/context.py',
              root/'security_inventory/routes.py', root/'security_inventory/drift.py'}
    def add(call):
        try: p=Path(inspect.getfile(call))
        except (TypeError, OSError): raise InventoryError('UNINSPECTABLE_SOURCE_REQUIRES_REVIEW')
        if p.resolve().is_relative_to(root.resolve()): selected.add(p)
    def deps(dep):
        if dep is None: return
        if dep.call: add(dep.call)
        for d in dep.dependencies: deps(d)
    def walk(routes):
        for r in routes:
            if hasattr(r,'original_router'): walk(r.original_router.routes); continue
            if isinstance(r,(Route,WebSocketRoute)):
                add(r.endpoint); deps(getattr(r,'dependant',None))
    inspect_routes(app)
    walk(app.routes)
    for m in app.user_middleware: add(m.cls)
    for p in sorted(selected):
        if p.is_symlink(): raise InventoryError('SYMLINK_REQUIRES_REVIEW')
        if p.suffix != '.py' or not p.is_file(): raise InventoryError('SOURCE_FILE_MISSING')
        if p.is_file():
            result[p.resolve().relative_to(root.resolve()).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    if not result: raise InventoryError('EMPTY_SOURCE_SURFACE')
    return result


def snapshot(app, source_root):
    return {'profile':'MCIS-OFFLINE-DRIFT-1', 'source':source_surface(source_root, app),
            'runtime':runtime_surface(app)}


def verify_drift(app, source_root, baseline):
    observed=snapshot(app,source_root)
    if type(baseline) is not dict or set(baseline)!=set(observed) or baseline['profile']!=observed['profile']:
        raise InventoryError('INVALID_DRIFT_BASELINE')
    if observed['source'] != baseline['source']:
        changed=sorted(k for k in set(observed['source']) | set(baseline['source']) if observed['source'].get(k)!=baseline['source'].get(k))
        raise InventoryError('SOURCE_DRIFT_REQUIRES_REVIEW: '+', '.join(changed))
    if observed['runtime'] != baseline['runtime']: raise InventoryError('RUNTIME_DRIFT_REQUIRES_REVIEW')
    return {'reviewedSurfaceUnchanged':True, 'authenticationVerified':False,
            'authorizationVerified':False,
            'unverified':['closure/global state and function defaults', 'external middleware implementation and untracked helper modules',
                          'runtime changes after snapshot', 'external identity and revocation semantics',
                          'resource authorization and semantic classification']}
