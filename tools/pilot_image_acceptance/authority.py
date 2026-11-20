"""Internal creation permit for a trusted isolated host. No HTTP/login authority.

The host supplies verified SERVER configuration, never request fields. This
module validates scope/expiry; it cannot authenticate the configuration's issuer.
"""
from dataclasses import dataclass
import math
import time
from .fixtures import cases, encoded, sha
from .prepare import checked, bind_existing_case_creator


@dataclass(frozen=True)
class CreationConfig:
    subject: str
    role: str
    expires_at: float  # Monotonic process deadline, supplied explicitly.
    grants: frozenset  # (case_id, 'case.create', exact fabricated body SHA256)


class CreationAuthority:
    def __init__(self, config, *, clock=time.monotonic):
        checked(type(config) is CreationConfig, 'Verified server creation config required')
        checked(isinstance(config.subject,str) and config.subject.strip()==config.subject
                and 0<len(config.subject)<=200 and all(ord(c)>=32 and ord(c)!=127 for c in config.subject), 'Invalid server subject')
        checked(config.role in ('Investigator','LeadInvestigator'), 'Explicit creation role required')
        expected=frozenset((d['caseId'],'case.create',sha(encoded(d))) for d in cases())
        checked(type(config.grants) is frozenset and config.grants==expected, 'Exact two fabricated creation grants required')
        checked(type(config.expires_at) in (int,float) and math.isfinite(config.expires_at), 'Invalid creation deadline')
        now=clock()
        checked(type(now) in (int,float) and math.isfinite(now) and 0 < config.expires_at-now <= 600,
                'Creation permit must expire within ten minutes')
        self._config=config;self._clock=clock;self._claimed=False;self._bound=False

    def claim(self):
        checked(not self._claimed, 'Creation scope already consumed')
        self._claimed=True  # Consume before any resource/handler, including failure.
        self.check_live()
        return self._config

    def check_live(self):
        now=self._clock()
        checked(type(now) in (int,float) and math.isfinite(now) and now<self._config.expires_at,
                'Creation authority expired or unavailable')


class CreationAdapter:
    """Internal one-scope adapter, constructed by host_adapter.owned_creation_scope."""
    def __init__(self, authority, app, context_type, request_type):
        checked(type(authority) is CreationAuthority and authority._claimed and not authority._bound,
                'Claimed unused creation scope required')
        authority._bound=True
        self._authority=authority;self._app=app;self._open=True;self._pending={d['caseId']:encoded(d) for d in cases()}
        self._active=None;self._context_type=context_type;self._request_type=request_type
        self._create=bind_existing_case_creator(context_for_creation=self._context)

    async def _context(self,case_id,operation):
        checked(self._open and self._active==case_id and operation=='case.create', 'Creation outside active fixed request')
        self._authority.check_live();config=self._authority._config
        # Real server Request/Ctx, no browser role/operator headers or default role.
        request=self._request_type({'type':'http','method':'POST','path':'/_internal/synthetic-preparation',
                                    'headers':[], 'app':self._app})
        return self._context_type(role=config.role,operator=config.subject,request=request)

    async def create_case(self,body):
        checked(self._open and self._active is None, 'Creation scope closed or busy')
        self._authority.check_live()
        checked(isinstance(body,dict) and self._pending.get(body.get('caseId'))==encoded(body), 'Unpermitted case body or consumed case')
        # Snapshot prevents caller mutation between authorization and handler.
        import json
        snapshot=json.loads(self._pending.pop(body['caseId']))
        self._active=body['caseId']
        try:
            return await self._create(snapshot)
        except BaseException:
            self.close()  # An unknown create must not be retried in this scope.
            raise
        finally:
            self._active=None

    def close(self):
        self._open=False;self._pending.clear()
