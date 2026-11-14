"""One-shot, explicit DeepSeek check with fixed fictional input only.

No case/file/stdin input, listener, account access, storage, or fixture fallback.
This is not the production protected-extraction host or a full case acceptance.
"""
import argparse
import json
from . import deepseek_client, extraction
from .extraction_review_fixture import document

BASE = {'input': 'fixed-fictional-interview', 'providerMode': 'remote-deepseek',
        'modelIdentityVerified': False, 'saved': False, 'factVerified': False,
        'fixtureFallback': False, 'completeCaseValidation': False,
        'protectedHostIntegrated': False}


def run_probe(*, send_fictional=False):
    if send_fictional is not True:
        return {**BASE, 'status': 'not_requested', 'requestAttempted': False}
    try:
        cfg = deepseek_client.config_from_environment()
    except Exception:
        return {**BASE, 'status': 'invalid_configuration', 'requestAttempted': False}
    if cfg is None:
        return {**BASE, 'status': 'not_connected', 'requestAttempted': False}
    attempted = False
    try:
        record = document()
        messages = extraction.prompt(record, {})
        attempted = True
        content = deepseek_client.complete(cfg, messages)
        payload = extraction.parse_output(content, record)
        statements, citations = extraction.checked_statements(payload, record, {})
        return {**BASE, 'status': 'validated_response', 'requestAttempted': True,
                'configuredModel': cfg.model, 'proposalCount': len(statements),
                'citationCount': len(citations),
                'citationMeaning': 'exact_quote_match_only_not_fact_verification',
                'outputMeaning': 'unreviewed-proposals-not-expert-accuracy'}
    except Exception:
        # No exception strings, response bodies, prompt, credentials or output.
        return {**BASE, 'status': 'unconfirmed', 'requestAttempted': None if attempted else False}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError()


def main(argv=None):
    parser = Parser(description='Explicit fixed fictional DeepSeek probe only.')
    parser.add_argument('--send-fictional', action='store_true')
    try:
        args = parser.parse_args(argv)
        result = run_probe(send_fictional=args.send_fictional)
    except Exception:
        result = {**BASE, 'status': 'invalid_configuration', 'requestAttempted': False}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['status'] in ('not_requested', 'not_connected', 'validated_response') else 2


if __name__ == '__main__':
    raise SystemExit(main())
