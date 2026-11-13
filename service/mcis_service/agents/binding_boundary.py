"""Reserve local-only timeline binding authority; no receipts are issued yet.

Only the named root/payload field and package namespace are protected. This is
not recursive content filtering, signature verification, or evidence approval.
"""
from ..common.context import problem

FIELD = 'timelineSourceBinding'
NAMESPACE = 'timeline-bindings'


def reject_client_binding(draft):
    payload = draft.get('payload') if isinstance(draft, dict) else None
    if isinstance(draft, dict) and (FIELD in draft or isinstance(payload, dict) and FIELD in payload):
        raise problem(422, 'TIMELINE_BINDING_LOCAL_ONLY',
                      '时间线来源绑定凭据只能由本地服务签发；当前不接受提交或恢复为活跃凭据')


def reject_package_binding_paths(files):
    if any(name.casefold() == NAMESPACE or name.casefold().startswith(NAMESPACE + '/') for name in files):
        raise problem(422, 'TIMELINE_BINDING_IMPORT_UNSUPPORTED',
                      '当前版本不支持时间线绑定凭据的历史恢复；请保留原包，不会将其激活')
