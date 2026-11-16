"""v3 draft: exact PCM frame/rate timebase, retained recognizer output, no execution proof."""
import copy
from .contract import exact, need, integer, digest, canonical
from .machine_contract import validate as validate_v2
PROFILE = 'MCIS-AUDIO-MACHINE-DRAFT-3'


def validate(document):
    exact(document, 'profile version source transcript receipt recognizerResult recognizerResultSha256 artifactSha256')
    need(document['profile'] == PROFILE and type(document['version']) is int and document['version'] == 3)
    s = document['source']
    exact(s, 'caseId evidenceId registeredSha256 currentSha256 stateDigest durationMs trackIndex frameCount sampleRateHz')
    integer(s['sampleRateHz'], 8000, 48000)
    integer(s['frameCount'], s['sampleRateHz'], s['sampleRateHz'] * 60)
    need(s['durationMs'] == (s['frameCount'] * 1000 + s['sampleRateHz'] - 1) // s['sampleRateHz'])
    raw = document['recognizerResult']
    need(type(raw) is dict and raw.get('inputSha256') == s['currentSha256'])
    need(raw.get('modelWeightsSha256') == document['receipt']['modelWeightsSha256'])
    need(document['recognizerResultSha256'] == digest(raw))
    need(document['artifactSha256'] == digest({k:v for k,v in document.items() if k != 'artifactSha256'}))
    reduced = copy.deepcopy({k:v for k,v in document.items() if k not in ('recognizerResult', 'recognizerResultSha256')})
    reduced.update(profile='MCIS-AUDIO-MACHINE-DRAFT-2', version=2)
    for k in ('frameCount', 'sampleRateHz'): del reduced['source'][k]
    reduced['artifactSha256'] = digest({k:v for k,v in reduced.items() if k != 'artifactSha256'})
    validate_v2(reduced)
    for segment in document['transcript']['segments']:
        need(segment['endMs'] * s['sampleRateHz'] <= s['frameCount'] * 1000)
    need(len(canonical(document)) <= 262144)
    return copy.deepcopy(document)


def inspect(document):
    validate(document)
    return {'kind':'machine_draft', 'origin':document['receipt']['origin'], 'reviewStatus':'pending',
            'executionVerified':False, 'sourceBytesChecked':False, 'authorizationVerified':False,
            'admissionAllowed':False, 'humanTranscript':False, 'durationMsMeaning':'ceiling-display-bound',
            'exactDurationMeaning':'frameCount/sampleRateHz seconds', 'timestamps':'model-estimates-or-unknown'}
