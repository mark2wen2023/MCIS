"""IQ-1 isolated in-memory workflow prototype; NOT a production API or archive."""
from copy import deepcopy
import hashlib
import json

class Conflict(ValueError):
    pass

class Workflow:
    def __init__(self, case_id):
        self.case_id = case_id
        self.stage = 'Observed'
        self.revision = 1
        self.events = []
        self.receipts = {}
        self.sources = {}
        self.latest_assessment = None
        self.pending = False
        self.verifications = []
        self.verification_round = 0
        self.packet = None

    def snapshot(self):
        return deepcopy(dict(caseId=self.case_id, revision=self.revision,
            stage=self.stage, events=self.events, sources=self.sources,
            newEvidencePendingReview=self.pending, verificationRound=self.verification_round,
            currentVerificationIds=self.verifications))

    def append(self, actor, capability, request_id, expected_revision, kind, payload):
        # Prototype capabilities are trusted inputs; this is not authentication.
        # Exact AgentService check is only a test fixture boundary, not a secure
        # principal/type check. Real identity middleware is required in production.
        allowed = {'Assessment': 'assess', 'BeginVerification': 'verify',
            'Verification': 'verify', 'SubmitDiscussion': 'verify',
            'Discussion': 'discuss', 'NewEvidence': 'record', 'Reopen': 'assess'}
        if kind not in allowed or capability != allowed[kind] or actor == 'AgentService':
            raise PermissionError('not authorized')
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError('request id required')
        digest = hashlib.sha256(json.dumps([expected_revision,kind,payload],
            sort_keys=True, allow_nan=False).encode()).hexdigest()
        key = (actor, request_id)
        if key in self.receipts:
            old_digest, result = self.receipts[key]
            if old_digest != digest:
                raise Conflict('request reused with different content')
            return deepcopy(result)
        if type(expected_revision) is not int or expected_revision != self.revision:
            raise Conflict('revision conflict')
        data = deepcopy(payload)
        if not isinstance(data, dict):
            raise ValueError('object required')
        stage, pending = self.stage, self.pending
        assessment = self.latest_assessment
        verification_round = self.verification_round
        verifications, sources, packet = deepcopy(self.verifications), deepcopy(self.sources), deepcopy(self.packet)
        def required(name):
            if not isinstance(data.get(name), str) or not data[name].strip():
                raise ValueError(name + ' required')
        if kind == 'NewEvidence':
            required('sourceId'); required('version'); required('digest')
            if data.get('caseId') != self.case_id:
                raise ValueError('cross-case source')
            versions = sources.setdefault(data['sourceId'], {})
            if data['version'] in versions and versions[data['version']] != data['digest']:
                raise Conflict('immutable source version')
            versions[data['version']] = data['digest']
            pending = True
            # Does not change workflow stage or prior judgment.
        elif kind == 'Assessment':
            if stage not in ('Observed','AssessmentRecorded','Verifying','AwaitingDiscussion'):
                raise Conflict('reopen before revising a recorded discussion')
            required('text')
            if assessment is not None:
                required('changeReason')
                if data.get('supersedes') != assessment:
                    raise Conflict('assessment version conflict')
            if data.get('sources') != sources:
                raise Conflict('assessment must bind current recorded source versions')
            assessment = len(self.events)+1
            stage, pending, verifications, packet = 'AssessmentRecorded', False, [], None
        elif kind == 'BeginVerification':
            if stage != 'AssessmentRecorded':
                raise Conflict('initial assessment required')
            required('question'); required('method')
            stage = 'Verifying'
            verification_round += 1
            verifications = []
            data['verificationRound'] = verification_round
        elif kind == 'Verification':
            if stage != 'Verifying':
                raise Conflict('verification not started')
            required('activity'); required('result')
            if data.get('outcome') not in ('Supported','Contradicted','Inconclusive','UnableToVerify'):
                raise ValueError('invalid outcome')
            if data['outcome'] == 'UnableToVerify':
                required('reason')
            data['verificationRound'] = verification_round
            verifications.append(len(self.events)+1)
        elif kind == 'SubmitDiscussion':
            if stage != 'Verifying' or not verifications or pending:
                raise Conflict('verification required and evidence must be reviewed')
            required('agenda')
            packet = dict(revision=self.revision+1, sources=deepcopy(sources), assessment=assessment,
                          verificationIds=deepcopy(verifications), verificationRound=verification_round)
            stage = 'AwaitingDiscussion'
            data['packet'] = deepcopy(packet)
        elif kind == 'Discussion':
            if stage != 'AwaitingDiscussion' or pending or data.get('packetRevision') != packet['revision']:
                raise Conflict('discussion packet stale or unavailable')
            required('summary')
            if not isinstance(data.get('dissent'), list) or not isinstance(data.get('participantsRecorded'), list):
                raise ValueError('participants and dissent records required')
            if data.get('outcome') not in ('OpinionRecorded','MoreVerification','Undetermined'):
                raise ValueError('invalid outcome')
            data['recorder'] = actor
            stage = 'Verifying' if data['outcome']=='MoreVerification' else 'DiscussionRecorded'
            if data['outcome'] == 'MoreVerification':
                verification_round += 1
                verifications = []
                packet = None
                data['nextVerificationRound'] = verification_round
        elif kind == 'Reopen':
            if stage != 'DiscussionRecorded':
                raise Conflict('no recorded discussion to reopen')
            required('reason')
            stage, packet, verifications = 'AssessmentRecorded', None, []
        event = dict(sequence=len(self.events)+1, revision=self.revision+1, actor=actor,
            kind=kind, payload=data, resultingStage=stage)
        # No state mutation happens before all validation succeeds.
        self.stage, self.pending = stage, pending
        self.latest_assessment, self.verifications = assessment, verifications
        self.verification_round = verification_round
        self.sources, self.packet = sources, packet
        self.revision += 1
        self.events.append(event)
        result = deepcopy(event)
        self.receipts[key] = (digest, deepcopy(result))
        return result
