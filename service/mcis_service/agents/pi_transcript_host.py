"""Bounded read-only Pi tools. Trusted callable only; no network, routes or writes."""
import copy
import re
import time
from . import host_extraction as h, extraction as e
from ..common.context import problem

MAX_TOOLS = 8
MAX_MODELS = 4
MAX_SECONDS = 120

class TranscriptHost:
    def __init__(self, db, settings, token, case_id, record_id, expected_binding_digest):
        if type(expected_binding_digest) is not str or not re.fullmatch(r'[0-9a-f]{64}', expected_binding_digest):
            raise problem(422, 'PI_BINDING_INVALID', '需要来源绑定')
        self._args = (db, settings, token, case_id, record_id)
        self._binding = expected_binding_digest
        self._started = time.monotonic()
        self._closed = False
        self._model_pending = False
        self._models = 0
        self._tools = 0
        self._check()

    def close(self):
        self._closed = True

    def _check(self):
        if self._closed or time.monotonic() - self._started >= MAX_SECONDS:
            self.close()
            raise problem(409, 'PI_RUN_CLOSED', '运行已关闭或超时')
        try:
            binding, record, policy, scope = h._snapshot(*self._args)
            if binding != self._binding:
                raise problem(409, 'PI_SOURCE_CHANGED', '来源或权限已变化')
        except Exception:
            self.close()
            raise
        return record, policy, scope

    def begin_model(self):
        self._check()
        if self._model_pending or self._models >= MAX_MODELS:
            self.close()
            raise problem(409, 'PI_MODEL_BUDGET', '模型调用次数或状态无效')
        self._models += 1
        self._model_pending = True
        return {'modelCall': self._models}

    def end_model(self):
        self._check()
        if not self._model_pending:
            self.close()
            raise problem(409, 'PI_MODEL_STATE', '没有待完成模型调用')
        self._model_pending = False

    def _proposal(self, content, record, policy):
        if type(content) is not str or len(content.encode('utf-8')) > 65536:
            raise ValueError()
        payload = e.parse_output(content, record)
        statements, citations = e.checked_statements(payload, record, policy)
        return {'status': 'PendingReview', 'proposals': statements, 'citations': citations,
                'saved': False, 'factVerified': False, 'persistentAudit': False,
                'bindingDigest': self._binding,
                'citationMeaning': 'exact_quote_match_only_not_fact_verification'}

    def call(self, name, args):
        record, policy, _ = self._check()
        if self._model_pending or self._tools >= MAX_TOOLS:
            self.close()
            raise problem(409, 'PI_TOOL_BUDGET', '工具调用次数或状态无效')
        self._tools += 1
        if type(name) is not str or type(args) is not dict:
            raise problem(422, 'PI_TOOL_INVALID', '工具输入无效')
        try:
            redacted = e.redacted_input(record, policy)
            if name == 'read_transcript_excerpt':
                if set(args) != {'round', 'field', 'start', 'length'}:
                    raise ValueError()
                rnd, field, start, length = (args[k] for k in ('round', 'field', 'start', 'length'))
                if (type(rnd) is not int or rnd < 1 or type(field) is not str or field not in ('Question', 'Answer')
                        or type(start) is not int or start < 0 or type(length) is not int or not 1 <= length <= 4000):
                    raise ValueError()
                turns = [t for t in redacted['turns'] if t['round'] == rnd]
                if len(turns) != 1 or start > len(turns[0][field.lower()]):
                    raise ValueError()
                result = {'round': rnd, 'field': field, 'start': start,
                          'text': turns[0][field.lower()][start:start + length],
                          'coordinates': 'redacted_unicode_code_points'}
            elif name == 'find_transcript_passages':
                if set(args) != {'query'} or type(args['query']) is not str or not args['query'].strip() or len(args['query']) > 200:
                    raise ValueError()
                query, matches = args['query'], []
                for turn in redacted['turns']:
                    for field in ('question', 'answer'):
                        start = 0
                        while len(matches) < 20:
                            found = turn[field].find(query, start)
                            if found < 0:
                                break
                            matches.append({'round': turn['round'], 'field': field.title(), 'start': found, 'text': query})
                            start = found + len(query)
                result = {'matches': matches, 'limit': 20, 'coordinates': 'redacted_unicode_code_points'}
            elif name == 'validate_extraction_proposal':
                if set(args) != {'content'}:
                    raise ValueError()
                try:
                    result = self._proposal(args['content'], record, policy)
                except Exception:
                    result = {'status': 'invalid', 'saved': False, 'factVerified': False,
                              'error': 'Proposal must match schema and quote the selected original exactly.'}
            else:
                raise ValueError()
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
            raise problem(422, 'PI_TOOL_INVALID', '工具输入无效') from None
        self._check()
        return copy.deepcopy(result)

    def dispatch(self, envelope):
        """Strict trusted-process protocol; no identity/configuration inputs."""
        self._check()
        if type(envelope) is not dict or type(envelope.get('op')) is not str:
            raise problem(422, 'PI_PROTOCOL_INVALID', '运行协议无效')
        op = envelope['op']
        if op in ('model_start', 'model_end') and set(envelope) == {'op'}:
            if op == 'model_start':
                return self.begin_model()
            self.end_model()
            return {'ok': True}
        if op == 'tool' and set(envelope) == {'op', 'name', 'args'}:
            return self.call(envelope['name'], envelope['args'])
        if op == 'final' and set(envelope) == {'op', 'payload'}:
            return self.finish(envelope['payload'])
        raise problem(422, 'PI_PROTOCOL_INVALID', '运行协议无效')

    def finish(self, content):
        record, policy, scope = self._check()
        if self._model_pending:
            self.close()
            raise problem(409, 'PI_MODEL_STATE', '模型调用尚未完成')
        try:
            result = self._proposal(content, record, policy)
            self._check()
            return {**result, 'sourceScope': scope, 'modelCalls': self._models,
                    'toolCalls': self._tools}
        finally:
            self.close()
