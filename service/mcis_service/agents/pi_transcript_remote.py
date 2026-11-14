"""Host-owned remote Pi history. Explicit authorization; no legacy/API routes."""
import copy
import json
import re
from . import extraction as e, host_extraction as h, pi_deepseek_transport as transport
from .deepseek_client import validate_config, ENDPOINT
from .pi_transcript_host import TranscriptHost, MAX_SECONDS
from ..common.context import problem
from . import pi_extraction_skill as skill

COMPLETION_MARKER='MCIS_COMPLETE_VALIDATED_PROPOSAL'
COMPLETION_MODES=('exact','validated-reference')

def _prepare(args,cfg,completion_mode='exact'):
    if completion_mode not in COMPLETION_MODES:raise ValueError('completion mode')
    validate_config(cfg)
    binding,record,policy,scope=h._snapshot(*args)
    # Reuse existing egress size/redaction checks, not its no-tools instruction.
    source_message=e.prompt(record,policy)[1]
    manifest=skill.current_manifest()
    system=manifest['prompts'][completion_mode]
    messages=[{'role':'system','content':system},source_message]
    disclosure={'skillRef':skill.reference(manifest),'skillManifest':manifest,'destination':ENDPOINT,'provider':'DeepSeek','model':cfg.model,
                'caseId':args[3],'recordId':args[4],'bindingDigest':binding,'sourceScope':scope,
                'purpose':'bounded-read-only-Pi-transcript-analysis-pending-human-review',
                'completionMode':completion_mode,'messages':messages,'tools':copy.deepcopy(transport.TOOL_SCHEMAS),
                'laterRounds':'Actual model outputs and authorized tool results are sent back to DeepSeek.',
                'limits':{'modelCalls':4,'toolCalls':8,'seconds':120},'scopeVersion':1}
    digest=e.digest({'disclosure':disclosure,'sessionBinding':e.digest(args[2])})
    return disclosure,digest,messages

def describe_remote(db,settings,session_token,case_id,record_id,cfg,*,completion_mode='exact'):
    disclosure,digest,_=_prepare((db,settings,session_token,case_id,record_id),cfg,completion_mode)
    return {**disclosure,'approvalDigest':digest,'humanApprovalVerified':False,'requestAttempted':False}

class RemoteTranscriptHost(TranscriptHost):
    def __init__(self,db,settings,session_token,case_id,record_id,cfg,*,approved_disclosure_digest=None,completion_mode='exact'):
        args=(db,settings,session_token,case_id,record_id)
        if type(approved_disclosure_digest) is not str or not re.fullmatch('[0-9a-f]{64}',approved_disclosure_digest):
            raise problem(403,'PI_REMOTE_APPROVAL_REQUIRED','需要明确授权本次 Pi 数据发送范围')
        disclosure,digest,messages=_prepare(args,cfg,completion_mode)
        if digest!=approved_disclosure_digest:
            raise problem(409,'PI_REMOTE_SCOPE_CHANGED','Pi 授权范围已变化')
        super().__init__(*args,disclosure['bindingDigest'])
        self._skill_manifest=copy.deepcopy(disclosure['skillManifest'])
        self._completion_mode=completion_mode
        self._accepted_content=None
        self._cfg=cfg
        self._approved=digest
        self._messages=copy.deepcopy(messages)
        self._requested=False
        self._pending_calls=[]
        self._call_ids=set()
        self._terminal=None
        self._validated=None
        self._read_source=False

    def _remote_check(self):
        self._check()
        try:
            if _prepare(self._args,self._cfg,self._completion_mode)[1]!=self._approved:
                raise problem(409,'PI_REMOTE_SCOPE_CHANGED','Pi 数据发送范围已变化')
        except Exception:
            self.close()
            raise

    def _deny(self):
        self.close()
        raise problem(409,'PI_REMOTE_PROTOCOL_INVALID','Pi 运行请求不匹配当前状态')

    def dispatch(self,envelope):
        self._remote_check()
        if type(envelope) is not dict or type(envelope.get('op')) is not str:
            return self._deny()
        op=envelope['op']
        try:
            if op=='model_start' and set(envelope)=={'op'}:
                if self._pending_calls or self._terminal is not None: return self._deny()
                result=self.begin_model()
                self._requested=False
                return result
            if op=='model_request' and set(envelope)=={'op'}:
                if not self._model_pending or self._requested or self._pending_calls or self._terminal is not None:
                    return self._deny()
                self._requested=True
                self._remote_check()
                response=transport.complete(self._cfg,copy.deepcopy(self._messages),deadline=self._started+MAX_SECONDS)
                self._remote_check()
                # Revalidate even mocked/substituted transport; retain no credentials.
                if type(response) is not dict or set(response)!={'message','finish_reason'}: return self._deny()
                msg=transport.assistant_message(response['message'],response['finish_reason'])
                calls=msg.get('tool_calls',[])
                if any(call['id'] in self._call_ids for call in calls): return self._deny()
                self._call_ids.update(call['id'] for call in calls)
                self._messages.append(copy.deepcopy(msg))
                self._pending_calls=copy.deepcopy(calls)
                if not calls:self._terminal=msg['content']
                return copy.deepcopy({'configuredModel':self._cfg.model,'message':msg,'finish_reason':response['finish_reason']})
            if op=='model_end' and set(envelope)=={'op'}:
                if not self._requested:return self._deny()
                self.end_model()
                return {'ok':True}
            if op=='tool' and set(envelope)=={'op','name','args','callId'}:
                if self._model_pending or not self._pending_calls:return self._deny()
                expected=self._pending_calls[0]
                args=transport.validate_tool(envelope['name'],envelope['args'])
                if (envelope['callId']!=expected['id'] or envelope['name']!=expected['function']['name']
                        or e.digest(args)!=e.digest(transport.strict_json(expected['function']['arguments']))):
                    return self._deny()
                if envelope['name']=='validate_extraction_proposal':self._validated=None
                result=self.call(envelope['name'],args)
                self._remote_check()
                content=json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(',',':'))
                if len(content.encode('utf-8'))>65536:return self._deny()
                self._messages.append({'role':'tool','tool_call_id':expected['id'],'content':content})
                self._pending_calls.pop(0)
                if envelope['name'] in ('read_transcript_excerpt','find_transcript_passages'):
                    self._read_source=True
                if envelope['name']=='validate_extraction_proposal' and result.get('status')=='PendingReview':
                    self._validated=args['content']
                return result
            if op=='final' and set(envelope)=={'op','payload'}:
                if (self._model_pending or self._pending_calls or self._terminal is None
                        or type(envelope['payload']) is not str or envelope['payload']!=self._terminal
                        or not self._read_source or self._validated is None):
                    return self._deny()
                if self._completion_mode=='validated-reference':
                    if envelope['payload']!=COMPLETION_MARKER:return self._deny()
                    content=self._validated
                else:
                    if envelope['payload']!=self._validated:return self._deny()
                    content=envelope['payload']
                result=self.finish(content)
                self._accepted_content=content
                return {**result,'completionMode':self._completion_mode,'providerMode':'remote-deepseek','configuredModel':self._cfg.model,
                        'modelIdentityVerified':False,'humanApprovalVerified':False,
                        'inferencePerformed':True,'fixture':False}
            return self._deny()
        except Exception:
            self.close()
            raise
