"""Convert retained local SenseVoice output into v3 pending drafts; no ASR or network here."""
import argparse
import copy
import json
import re
from pathlib import Path
from .contract import digest
from .machine_contract import output_digest
from .sample_machine_contract import PROFILE, validate


def timestamp_inspection(row, source):
    pairs = row.get('timestamp')
    if pairs is None:
        return {'status':'missing', 'usableForLocation':False}
    valid = isinstance(pairs,list) and bool(pairs)
    previous = 0
    if valid:
        for pair in pairs:
            if not (isinstance(pair,list) and len(pair)==2 and all(type(v) is int for v in pair)
                    and 0<=pair[0]<pair[1] and pair[0]>=previous
                    and pair[1]*source['sampleRateHz']<=source['frameCount']*1000):
                valid=False
                break
            previous=pair[1]
    words=row.get('words')
    paired=isinstance(words,list) and isinstance(pairs,list) and len(words)==len(pairs) and all(isinstance(w,str) and w for w in words)
    return {'status':'bounds-valid' if valid else 'invalid-bounds-or-shape',
            'explicitWordPairing':paired, 'usableForLocation':False,
            'policy':'retain raw pairs; this slice does not promote token alignment to locations'}


def convert(result, source):
    if result.get('scope') not in ('actual-local-SenseVoiceSmall-public-noncase-sample','actual-local-SenseVoiceSmall-registered-audio'):raise ValueError('unsupported record scope')
    if result['inputSha256']!=source['currentSha256']:raise ValueError('different source bytes')
    rows=result['raw']
    if not isinstance(rows,list) or not 1<=len(rows)<=256:raise ValueError('empty or excessive recognition')
    unknown=[];checks=[]
    for i,row in enumerate(rows):
        if not isinstance(row,dict) or not isinstance(row.get('text'),str):raise ValueError('invalid recognition')
        text=re.sub(r'<\|[^<>]*\|>','',row['text']).strip()
        if not text:raise ValueError('no recognized speech; do not invent transcript')
        unknown.append({'id':f'sv-{i+1}','text':text,'speaker':{'status':'unknown','id':None},'reason':'alignment_pending' if 'timestamp' in row else 'time_unknown'})
        checks.append(timestamp_inspection(row,source))
    transcript={'revision':1,'parentArtifactSha256':None,'method':'machine_asr_draft','reviewStatus':'pending',
                'timeBasis':'original_audio_ms','segments':[],'unlocatedSegments':unknown}
    receipt={'executionId':'sv-'+digest(result)[:32],'provider':'local-SenseVoiceSmall',
             'model':'FunAudioLLM/SenseVoiceSmall@'+result['modelRevision'],'modelWeightsSha256':result['modelWeightsSha256'],
             'runtimeVersion':'funasr/'+result['versions']['funasr']+';torch/'+result['versions']['torch'],
             'toolVersion':'mcis-sensevoice-converter/1','parametersSha256':digest(result['parameters']),
             'inputSha256':result['inputSha256'],'trackIndex':source['trackIndex'],'outputSha256':output_digest(transcript),
             'outcome':'completed','origin':'claimed_local_execution'}
    doc={'profile':PROFILE,'version':3,'source':copy.deepcopy(source),'transcript':transcript,'receipt':receipt,
         'recognizerResult':copy.deepcopy(result),'recognizerResultSha256':digest(result)}
    doc['artifactSha256']=digest(doc)
    return {'draft':validate(doc),'inspection':{'timestamps':checks,'executionVerifiedByConverter':False,
            'emotionTags':'retained-only-not-facts','speaker':'unknown','humanReviewed':False}}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('result',type=Path);p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    converted=convert(json.loads(a.result.read_text()),json.loads(a.source.read_text()))
    a.output.mkdir(parents=True,exist_ok=False)
    for name,data in converted.items():(a.output/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
