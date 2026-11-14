"""Explicit Pi-only DeepSeek transport. No routes, retries or automatic selection."""
import asyncio
import copy
import json
import math
import re
import time
import httpx
from .deepseek_client import DeepSeekConfig, validate_config, ENDPOINT, MAX_REQUEST_BYTES, MAX_RESPONSE_BYTES
from ..common.context import problem

TOOL_SCHEMAS = [
    {'type':'function','function':{'name':'read_transcript_excerpt','description':'Read a bounded redacted excerpt of the current authorized transcript. Coordinates are redacted Unicode code points, not original UTF16 citation offsets.', 'parameters':{'type':'object','properties':{'round':{'type':'integer','minimum':1,'maximum':100000},'field':{'type':'string','enum':['Question','Answer']},'start':{'type':'integer','minimum':0,'maximum':24000},'length':{'type':'integer','minimum':1,'maximum':4000}},'required':['round','field','start','length'],'additionalProperties':False}}},
    {'type':'function','function':{'name':'find_transcript_passages','description':'Literal search in this current authorized redacted transcript only.', 'parameters':{'type':'object','properties':{'query':{'type':'string','minLength':1,'maxLength':200}},'required':['query'],'additionalProperties':False}}},
    {'type':'function','function':{'name':'validate_extraction_proposal','description':'Validate proposed statements JSON against source quotations. Does not save or approve facts.', 'parameters':{'type':'object','properties':{'content':{'type':'string','maxLength':65536}},'required':['content'],'additionalProperties':False}}},
]

def strict_json(value):
    def pairs(items):
        result={}
        for key, val in items:
            if key in result: raise ValueError()
            result[key]=val
        return result
    def finite_float(raw):
        result=float(raw)
        if not math.isfinite(result): raise ValueError()
        return result
    return json.loads(value, object_pairs_hook=pairs, parse_float=finite_float, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))

def validate_tool(name,args):
    if type(name) is not str or type(args) is not dict: raise ValueError()
    if name=='read_transcript_excerpt':
        if set(args)!={'round','field','start','length'}: raise ValueError()
        if type(args['round']) is not int or not 1 <= args['round'] <= 100000: raise ValueError()
        if type(args['field']) is not str or args['field'] not in ('Question','Answer'): raise ValueError()
        if type(args['start']) is not int or not 0 <= args['start'] <= 24000: raise ValueError()
        if type(args['length']) is not int or not 1 <= args['length'] <= 4000: raise ValueError()
    elif name=='find_transcript_passages':
        if set(args)!={'query'} or type(args['query']) is not str or not args['query'].strip() or len(args['query'])>200: raise ValueError()
    elif name=='validate_extraction_proposal':
        if set(args)!={'content'} or type(args['content']) is not str or len(args['content'].encode('utf-8'))>65536: raise ValueError()
    else: raise ValueError()
    return copy.deepcopy(args)

def assistant_message(msg,finish):
    if type(msg) is not dict or msg.get('role')!='assistant' or set(msg)-{'role','content','tool_calls','reasoning_content'}: raise ValueError()
    if msg.get('reasoning_content') not in (None,''): raise ValueError()
    content=msg.get('content')
    if content is not None and (type(content) is not str or len(content.encode('utf-8'))>65536): raise ValueError()
    calls=msg.get('tool_calls')
    if finish=='tool_calls':
        if type(calls) is not list or not 1<=len(calls)<=8: raise ValueError()
        seen=set(); checked=[]
        for ordinal, call in enumerate(calls):
            if (type(call) is not dict or set(call)-{'id','type','function','index'}
                    or not {'id','type','function'} <= set(call) or call['type']!='function'):
                raise ValueError()
            if 'index' in call and (type(call['index']) is not int or call['index'] != ordinal or not 0 <= call['index'] <= 7):
                raise ValueError()
            cid=call['id'];fn=call['function']
            if type(cid) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',cid) or cid in seen: raise ValueError()
            seen.add(cid)
            if type(fn) is not dict or set(fn)!={'name','arguments'} or type(fn['arguments']) is not str or len(fn['arguments'].encode('utf-8'))>65536: raise ValueError()
            validate_tool(fn['name'],strict_json(fn['arguments']))
            # Some non-stream DeepSeek tool calls include stream-style index.
            # It is positional metadata only; identity remains the unique id.
            checked.append(copy.deepcopy({key:call[key] for key in ('id','type','function')}))
        return {'role':'assistant','content':content,'tool_calls':checked}
    if finish!='stop' or calls or type(content) is not str or not content.strip(): raise ValueError()
    return {'role':'assistant','content':content}

def validate_messages(messages):
    if type(messages) is not list or not 2<=len(messages)<=32: raise ValueError()
    if any(type(m) is not dict for m in messages): raise ValueError()
    pending=set(); seen=set()
    for i,msg in enumerate(messages):
        role=msg.get('role')
        if i<2:
            if role!=('system' if i==0 else 'user') or set(msg)!={'role','content'} or type(msg['content']) is not str: raise ValueError()
        elif role=='assistant':
            if pending: raise ValueError()
            checked=assistant_message(msg,'tool_calls' if msg.get('tool_calls') else 'stop')
            for call in checked.get('tool_calls',[]):
                if call['id'] in seen: raise ValueError()
                seen.add(call['id']);pending.add(call['id'])
        elif role=='tool':
            if set(msg)!={'role','tool_call_id','content'} or type(msg['tool_call_id']) is not str or msg['tool_call_id'] not in pending or type(msg['content']) is not str: raise ValueError()
            pending.remove(msg['tool_call_id'])
        else: raise ValueError()
    if pending: raise ValueError()
    return copy.deepcopy(messages)

def complete(cfg,messages,*,deadline):
    validate_config(cfg)
    try:
        if type(deadline) not in (float,int) or not math.isfinite(deadline) or deadline<=time.monotonic(): raise ValueError()
        payload={'model':cfg.model,'messages':validate_messages(messages),'tools':copy.deepcopy(TOOL_SCHEMAS),
                 'tool_choice':'auto','stream':False,'thinking':{'type':'disabled'},'max_tokens':4096}
        body=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode('utf-8')
        if len(body)>MAX_REQUEST_BYTES: raise ValueError()
    except (ValueError,TypeError,UnicodeError,RecursionError):
        raise problem(422,'PI_DEEPSEEK_INPUT_INVALID','Pi 模型请求无效') from None
    async def request():
        remaining=deadline-time.monotonic()
        if remaining<=0: raise TimeoutError()
        # Absolute asyncio cancellation encloses connect, headers and all body
        # reads. Per-read httpx timeouts alone are NOT a total deadline.
        async with asyncio.timeout(remaining):
            async with httpx.AsyncClient(timeout=min(60.,remaining),trust_env=True,follow_redirects=False) as client:
                async with client.stream('POST',ENDPOINT,content=body,headers={'Authorization':'Bearer '+cfg.api_key,'Content-Type':'application/json'}) as response:
                    if response.status_code!=200: raise problem(502,'PI_DEEPSEEK_HTTP_ERROR','Pi 模型调用未成功')
                    chunks=[];size=0
                    async for chunk in response.aiter_bytes():
                        size+=len(chunk)
                        if size>MAX_RESPONSE_BYTES: raise ValueError()
                        chunks.append(chunk)
                    if time.monotonic()>=deadline: raise TimeoutError()
                    return strict_json(b''.join(chunks))
    try:
        value=asyncio.run(request())
        if type(value) is not dict or type(value.get('choices')) is not list or len(value['choices'])!=1: raise ValueError()
        choice=value['choices'][0]
        if type(choice) is not dict: raise ValueError()
        msg=assistant_message(choice['message'],choice['finish_reason'])
        return {'message':msg,'finish_reason':choice['finish_reason']}
    except (httpx.TimeoutException,TimeoutError):
        raise problem(504,'PI_DEEPSEEK_TIMEOUT','Pi 模型调用超时') from None
    except (ImportError,httpx.HTTPError):
        raise problem(502,'PI_DEEPSEEK_UNAVAILABLE','Pi 模型连接失败') from None
    except (ValueError,KeyError,IndexError,TypeError,UnicodeError,RecursionError):
        raise problem(502,'PI_DEEPSEEK_OUTPUT_INVALID','Pi 模型返回无效') from None
