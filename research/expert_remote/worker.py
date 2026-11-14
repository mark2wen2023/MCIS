"""Fixed one-request worker. Credential arrives over stdin, never argv/environment/Pi."""
import asyncio
import json
import sys
from research.expert_remote import transport
from research.expert_meeting.machine import canonical, strict


def main():
    try:
        raw=sys.stdin.buffer.read(transport.MAX_BYTES+16385)
        if len(raw)>transport.MAX_BYTES+16384: raise ValueError()
        config=strict(raw)
        if set(config) not in ({'messages','tools','key','deadline'},{'messages','tools','key','deadline','managedBinding'}):raise ValueError()
        mocked=sys.argv[1:]==['--mock']
        if sys.argv[1:] not in ([],['--mock']):raise ValueError()
        if mocked and 'managedBinding' in config:raise ValueError()
        if mocked:
            import httpx
            from research.expert_group.engine import _fixture, _packet, load_packet
            original=httpx.AsyncClient
            def reply(request):
                messages=json.loads(request.content)['messages'];step=sum(m['role']=='assistant' for m in messages)+1
                candidate=None
                for m in messages:
                    if m['role']=='tool':candidate=json.loads(m['content']).get('candidateId',candidate)
                message=_fixture(step,_packet(load_packet()),candidate)
                return httpx.Response(200,json={'id':'synthetic-mock-request','model':'MOCK-NOT-DEEPSEEK',
                    'choices':[{'finish_reason':'tool_calls' if message.get('tool_calls') else 'stop','message':message}]})
            transport.httpx.AsyncClient=lambda **kw:original(transport=httpx.MockTransport(reply),**kw)
        result=asyncio.run(transport.request(config['messages'],config['tools'],key=config['key'],deadline=config['deadline'],managed_binding=config.get('managedBinding')))
        output={'ok':True,'result':result,'transportMocked':mocked}
    except transport.TransportError as exc:
        output={'ok':False,'code':exc.code,'dispatched':exc.dispatched}
    except BaseException:
        output={'ok':False,'code':'worker_rejected','dispatched':True}
    raw=canonical(output)
    if len(raw)>transport.MAX_BYTES:raw=canonical({'ok':False,'code':'worker_output_limit','dispatched':True})
    sys.stdout.buffer.write(raw);sys.stdout.buffer.flush()


if __name__=='__main__':main()
