"""Pure assistant validator copied from 6f8f429 expert_group/engine.py.
No runner, model transport or old Meeting imports.
"""
import re
from research.expert_group.packet import GroupError, _strict, _dump

def _assistant(message):
    if not isinstance(message,dict) or message.get('role') != 'assistant': raise GroupError('provider_response_invalid')
    content = message.get('content')
    calls = message.get('tool_calls', [])
    if content is not None and (not isinstance(content,str) or len(content)>24000): raise GroupError('provider_response_invalid')
    if not isinstance(calls,list) or len(calls)>8: raise GroupError('provider_response_invalid')
    clean = {'role':'assistant','content':content}
    pending = []
    for call in calls:
        if not isinstance(call,dict) or call.get('type')!='function' or not isinstance(call.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', call['id']): raise GroupError('provider_response_invalid')
        function = call.get('function',{})
        if function.get('name') not in ('read_packet','validate_review') or not isinstance(function.get('arguments'),str) or len(function['arguments'])>64000: raise GroupError('provider_response_invalid')
        args = _strict(function['arguments'])
        pending.append({'id':call['id'],'name':function['name'],'args':args})
    if pending: clean['tool_calls']=[{'id':c['id'],'type':'function','function':{'name':c['name'],'arguments':_dump(c['args'])}} for c in pending]
    return clean, pending
