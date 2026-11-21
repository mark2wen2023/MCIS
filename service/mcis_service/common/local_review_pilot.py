"""Explicit synthetic-only session source; no login, credentials, routes or startup.

A trusted launcher supplies ephemeral token DIGESTS and narrowly scoped grants.
Never combine this source with 4A or enable it on the ordinary application.
"""
from dataclasses import dataclass
from hashlib import sha256
import math
import re
import time
from urllib.parse import urlsplit
from .context import problem, ROLES
from .verified_case_context import CaseGrant, _OPERATIONS, _install_verified_case_context

COOKIE_NAME = '__Host-MCIS-Pilot'
# For a future trusted bootstrap response; never expose the token in HTML/URL/JS.
COOKIE_OPTIONS = {'secure': True, 'httponly': True, 'samesite': 'strict', 'path': '/'}


@dataclass(frozen=True)
class PilotSession:
    subject: str
    role: str
    expires_at: float  # Deadline on this process's monotonic clock, not wall UTC.
    grants: frozenset  # Exact (synthetic case_id, operation) pairs; no wildcard.


class PilotSessions:
    def __init__(self, entries, *, clock=time.monotonic, report_reference_subject=None):
        # Explicit internal-only synthetic pilot grant; no route mapping/default.
        if report_reference_subject is not None and (type(report_reference_subject) is not str or not report_reference_subject.strip()):
            raise ValueError("invalid report reference subject")
        self._clock = clock
        self._entries = {}
        for digest, session in entries.items():
            if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest) or type(session) is not PilotSession:
                raise ValueError('invalid pilot session configuration')
            if (not isinstance(session.subject, str) or not session.subject.strip()
                    or session.subject != session.subject.strip() or len(session.subject) > 200
                    or any(ord(c) < 32 or ord(c) == 127 for c in session.subject)
                    or session.role not in ROLES or type(session.expires_at) not in (int, float)
                    or not math.isfinite(session.expires_at) or type(session.grants) is not frozenset):
                raise ValueError('invalid pilot session configuration')
            for pair in session.grants:
                if (type(pair) is not tuple or len(pair) != 2 or not isinstance(pair[0], str)
                        or not re.fullmatch(r'SYN-[A-Za-z0-9_.-]{1,123}', pair[0])
                        or (pair[1] not in _OPERATIONS.values() and not (
                            pair == ('SYN-XREPO-001', 'report.reference.prepare')
                            and report_reference_subject is not None
                            and session.subject == report_reference_subject))):
                    raise ValueError('pilot grants require explicit synthetic case and operation')
            self._entries[digest] = session

    def revoke(self, digest):
        self._entries.pop(digest, None)

    def _active_session(self, credential):
        if not isinstance(credential, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', credential):
            return None
        session = self._entries.get(sha256(credential.encode('ascii')).hexdigest())
        now = self._clock()
        if (session is None or type(now) not in (int, float) or not math.isfinite(now)
                or now >= session.expires_at):
            return None
        return session

    def authorized_cases(self, credential):
        """Validated server permit IDs only; None is denial, empty tuple is valid."""
        session = self._active_session(credential)
        if session is None:
            return None
        return tuple(sorted(case_id for case_id, operation in session.grants if operation == 'case.read'))

    async def verify(self, credential, case_id, operation):
        # No session creation or extension on reads, and no fallback identity.
        session = self._active_session(credential)
        if session is None or (case_id, operation) not in session.grants:
            return None
        return CaseGrant(session.subject, session.role, case_id, operation)


def _cookie_reader(origin):
    parsed = urlsplit(origin)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment or origin != 'https://' + parsed.netloc):
        raise ValueError('explicit HTTPS origin without path required')

    def read(request):
        headers = request.headers
        # No forwarding-header trust or bearer fallback in pilot-cookie mode.
        if (request.scope.get('scheme') != 'https' or headers.getlist('host') != [parsed.netloc]
                or headers.getlist('sec-fetch-site') != ['same-origin']
                or headers.getlist('authorization')):
            raise problem(403, 'PILOT_SAME_ORIGIN_REQUIRED', '试用请求必须来自已配置同源页面')
        origins = headers.getlist('origin')
        if (origins and origins != [origin]) or (request.method != 'GET' and origins != [origin]):
            raise problem(403, 'PILOT_SAME_ORIGIN_REQUIRED', '试用请求必须来自已配置同源页面')
        cookies = headers.getlist('cookie')
        if len(cookies) != 1:
            raise problem(401, 'PILOT_SESSION_REQUIRED', '需要服务器试用会话')
        values = [value for part in cookies[0].split(';')
                  for key, sep, value in [part.strip().partition('=')] if key == COOKIE_NAME and sep]
        if len(values) != 1 or not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', values[0]):
            raise problem(401, 'PILOT_SESSION_REQUIRED', '需要服务器试用会话')
        return values[0]
    return read


def _install_local_review_pilot(app, *, enabled=False, sessions=None, origin=None):
    """Install only before serving on a dedicated synthetic restricted app.

    Disabled/missing config installs denial, not the legacy role-header identity.
    No routes or model/data initialization; deployment and browser bootstrap absent.
    """
    if enabled is not True or type(sessions) is not PilotSessions or not isinstance(origin, str):
        return _install_verified_case_context(app)
    return _install_verified_case_context(app, verifier=sessions.verify, credential_reader=_cookie_reader(origin))
