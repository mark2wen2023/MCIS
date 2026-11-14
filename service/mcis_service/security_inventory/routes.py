"""Fail build-time checks on unclassified/changed routes; never grants access."""
from collections import Counter
from starlette.routing import Mount, Route, WebSocketRoute

class InventoryError(ValueError):
    pass

def context_dependency(dep):
    call=getattr(dep,'call',None)
    return ((getattr(call,'__module__',''),getattr(call,'__name__',''))==
            ('mcis_service.common.context','get_ctx') or
            any(context_dependency(d) for d in getattr(dep,'dependencies',())))

def endpoint_name(endpoint):
    return getattr(endpoint,'__module__',type(endpoint).__module__)+'.'+getattr(
        endpoint,'__qualname__',type(endpoint).__qualname__)

def inspect_routes(app):
    """Include hidden routes, WS, docs, mounts and lazy FastAPI includes."""
    rows=[]
    def walk(routes,prefix='',stack=()):
        if id(routes) in stack:raise InventoryError('CYCLIC_ROUTE_TREE')
        stack=(*stack,id(routes))
        for route in routes:
            if hasattr(route,'original_router'):
                extra=getattr(route.include_context,'prefix','')
                # Included-router dependencies affect effective authorization shape.
                inherited=getattr(route.include_context,'dependencies',())
                if inherited:
                    raise InventoryError('INCLUDED_DEPENDENCIES_REQUIRE_REVIEW')
                walk(route.original_router.routes,prefix+extra,stack)
                continue
            path=prefix+getattr(route,'path','')
            dep=getattr(route,'dependant',None)
            if isinstance(route,Mount):
                rows.append(dict(protocol='mount',method='*',path=path,
                    endpoint=endpoint_name(route.app),declaredContext=False))
                nested=getattr(route,'routes',None)
                if nested:walk(nested,path,stack)
            elif isinstance(route,WebSocketRoute):
                rows.append(dict(protocol='websocket',method='CONNECT',path=path,
                    endpoint=endpoint_name(route.endpoint),declaredContext=context_dependency(dep)))
            elif isinstance(route,Route):
                for method in sorted(route.methods):
                    rows.append(dict(protocol='http',method=method,path=path,
                        endpoint=endpoint_name(route.endpoint),declaredContext=context_dependency(dep)))
            else:raise InventoryError('UNSUPPORTED_ROUTE_TYPE')
    walk(app.routes)
    return sorted(rows,key=lambda r:(r['protocol'],r['path'],r['method'],r['endpoint']))

OBSERVED={'protocol','method','path','endpoint','declaredContext'}
CLASSIFIED={'scope','operation','rationale'}
def key(row):return row['protocol'],row['path'],row['method']
def verify(app,manifest):
    if type(manifest) is not dict or set(manifest)!={'profile','routes'} or manifest['profile']!='MCIS-ROUTE-CLASSIFICATION-1':
        raise InventoryError('INVALID_MANIFEST')
    declared=manifest['routes']
    if type(declared) is not list:raise InventoryError('INVALID_MANIFEST')
    for r in declared:
        if type(r) is not dict or set(r)!=OBSERVED|CLASSIFIED:
            raise InventoryError('INVALID_CLASSIFICATION_FIELDS')
        if any(type(r[k]) is not str or not r[k].strip() for k in OBSERVED-{'declaredContext'}):
            raise InventoryError('INVALID_ROUTE_FIELDS')
        if type(r['declaredContext']) is not bool:
            raise InventoryError('INVALID_CONTEXT_FLAG')
        if r['protocol'] not in ('http','websocket','mount'):
            raise InventoryError('INVALID_PROTOCOL')
        if r['scope'] not in ('case','global','meta','documentation','static','mount'):
            raise InventoryError('INVALID_SCOPE')
        if r['operation'] not in ('read','write','export','connect','mount'):
            raise InventoryError('INVALID_OPERATION')
        if type(r['rationale']) is not str or not r['rationale'].strip():
            raise InventoryError('RATIONALE_REQUIRED')
    actual=inspect_routes(app)
    for rows in (actual,declared):
        if any(n>1 for n in Counter(key(r) for r in rows).values()):
            raise InventoryError('DUPLICATE_ROUTE')
    a={key(r):r for r in actual};d={key(r):r for r in declared}
    if a.keys()!=d.keys():
        raise InventoryError('ROUTE_SET_CHANGED')
    for k,row in a.items():
        if row!={field:d[k][field] for field in OBSERVED}:
            raise InventoryError('ROUTE_IMPLEMENTATION_OR_CONTEXT_CHANGED')
    return dict(routes=len(actual),declaredContext=sum(r['declaredContext'] for r in actual),
                authenticationVerified=False,enforcementPerformed=False)
