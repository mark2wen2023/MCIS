"""Offline audio-v3 member consistency. Never opens paths, runs models or admits restore."""
import io
import re
import wave
from .contract import validate as validate_index, parse, digest, need
from tools.audio_transcript_contract.contract import digest as json_digest
from tools.audio_transcript_contract.sample_machine_contract import validate as validate_v3
from tools.audio_transcript_contract.sensevoice_candidate import convert


def pcm(raw):
    need(type(raw) is bytes and len(raw)>=12 and raw[:4]==b'RIFF' and raw[8:12]==b'WAVE', 'PCM WAV declaration')
    need(int.from_bytes(raw[4:8],'little')+8==len(raw), 'incomplete or trailing RIFF bytes')
    try:
        with wave.open(io.BytesIO(raw),'rb') as stream:
            channels,width,rate,frames=stream.getnchannels(),stream.getsampwidth(),stream.getframerate(),stream.getnframes()
            need(stream.getcomptype()=='NONE' and channels in (1,2) and width in (1,2,3,4) and
                 8000<=rate<=48000 and rate<=frames<=rate*60, 'unsupported PCM scope')
            need(len(stream.readframes(frames))==frames*channels*width and stream.readframes(1)==b'', 'PCM frame payload')
    except (wave.Error,EOFError) as exc:
        raise ValueError('invalid PCM WAV') from exc
    return dict(frameCount=frames,sampleRateHz=rate,channels=channels,sampleWidthBytes=width)


def check_audio_members(index, payloads):
    validate_index(index,payloads)
    need(index['sources'] and all(s['kind']=='audio' for s in index['sources']), 'only audio-v3 byte profile implemented')
    sources={s['id']:s for s in index['sources']}
    snapshots={}
    for sid,src in sources.items():
        raw=payloads[src['originalMember']]
        clock=pcm(raw)
        need(clock==src['location'], 'declared sampling clock differs from WAV')
        receipt=parse(payloads[src['receiptMember']])
        request=receipt.get('requestDigest')
        need(type(request) is str and re.fullmatch('[a-f0-9]{64}',request), 'missing receipt identifier')
        binding=dict(caseId=index['caseId'],evidenceId=src['evidenceId'],requestDigest=request,
                     registeredSha256=src['registeredSha256'],currentSha256=digest(raw))
        snapshots[sid]={k:v for k,v in binding.items() if k!='requestDigest'}
        snapshots[sid].update(stateDigest=json_digest(binding),trackIndex=0,
                              durationMs=(clock['frameCount']*1000+clock['sampleRateHz']-1)//clock['sampleRateHz'],
                              frameCount=clock['frameCount'],sampleRateHz=clock['sampleRateHz'])
    for run in index['runs']:
        source=snapshots[run['sourceId']]
        machine=validate_v3(parse(payloads[run['machineMember']]))
        need(machine['source']==source, 'machine source snapshot differs from bytes/registration')
        need(machine['transcript']['revision']==1 and machine['transcript']['parentArtifactSha256'] is None, 'missing earlier machine history')
        raw=parse(payloads[run['rawMember']])
        need(raw==machine['recognizerResult'], 'raw recognizer member differs from machine')
        # v3 binds a canonical-JSON digest; member transport SHA separately covers exact bytes.
        need(json_digest(raw)==machine['recognizerResultSha256'], 'recognizer canonical digest')
        metadata=parse(payloads[run['recognizerMember']])
        need(metadata=={k:raw[k] for k in ('modelRevision','modelWeightsSha256','versions','parameters')}, 'recognizer declaration differs')
        rebuilt=convert(raw,source)['draft']
        need(machine==rebuilt, 'machine draft differs from declared converter/retained result')
        initial=parse(payloads[run['initialMember']])
        clock=sources[run['sourceId']]['location']
        need(initial.get('audio')==dict(channels=clock['channels'],sampleWidthBytes=clock['sampleWidthBytes'],
                                      sampleRateHz=clock['sampleRateHz'],frames=clock['frameCount'],format='PCM_WAV'), 'initial PCM declaration')
        segment_ids={r['id'] for r in machine['transcript']['segments']+machine['transcript']['unlocatedSegments']}
        for revision in run['revisions'][1:]:
            doc=parse(payloads[revision['member']])
            need(doc.get('segmentId') in segment_ids and doc.get('audioSha256')==source['currentSha256'] and
                 doc.get('machineArtifactSha256')==machine['artifactSha256'], 'human revision source/target')
            need(type(doc.get('text')) is str and len(doc['text'])<=20000 and
                 doc.get('hearingStatus') in ('pending','transcription_checked','unintelligible'), 'human declaration')
            need(doc['hearingStatus']!='unintelligible' or doc['text']=='', 'unintelligible text')
    return {'restore_ready':False,'export_allowed':False,'execution_verified':False,'authenticity_verified':False,
            'authorization_verified':False,'scope':'supplied-audio-v3-bytes-and-declarations-only',
            'source_bytes_match':True,'sourceCount':len(sources),'runCount':len(index['runs'])}
