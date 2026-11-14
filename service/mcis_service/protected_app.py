"""Closed production-entry placeholder, NOT an authenticated business service.

Does not wrap or mount the legacy app, initialize storage, or enable business routes.
The legacy CLI remains unchanged and is development-only. Nothing here secures it.
"""
import json

_BODY = json.dumps({'code': 'AUTH_NOT_CONFIGURED',
                    'message': '可信身份与案件授权尚未配置，业务入口保持关闭。'},
                   ensure_ascii=True, separators=(',', ':')).encode('ascii')


class ClosedProtectedApp:
    async def __call__(self, scope, receive, send):
        kind = scope['type']
        if kind == 'lifespan':
            while True:
                event = await receive()
                if event['type'] == 'lifespan.startup':
                    await send({'type': 'lifespan.startup.complete'})
                elif event['type'] == 'lifespan.shutdown':
                    await send({'type': 'lifespan.shutdown.complete'})
                    return
        elif kind == 'http':
            # Never consume/parse credentials or bodies before the boundary exists.
            await send({'type': 'http.response.start', 'status': 503, 'headers': [
                (b'content-type', b'application/json'),
                (b'cache-control', b'no-store'),
                (b'pragma', b'no-cache'),
                (b'x-content-type-options', b'nosniff'),
                (b'content-length', str(len(_BODY)).encode('ascii'))]})
            await send({'type': 'http.response.body',
                        'body': b'' if scope.get('method') == 'HEAD' else _BODY})
        elif kind == 'websocket':
            await send({'type': 'websocket.close', 'code': 1008})
        else:
            raise RuntimeError('unsupported ASGI protocol')


def create_protected_app():
    """Always closed. No config toggle, auth resolver, or legacy fallback exists."""
    return ClosedProtectedApp()
