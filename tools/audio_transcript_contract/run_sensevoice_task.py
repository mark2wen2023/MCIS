"""Fixed local registered-WAV CPU worker; no automatic downloads or external inference."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import time
import wave

REVISION='3847d57b6bdf2dd8875cb1508d2af43d80a16bf7'


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--audio',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--task-id',required=True);p.add_argument('--input-sha256',required=True);a=p.parse_args()
    manifest=Path(__file__).resolve().parents[2]/'tests_acceptance/audio-sensevoice/model-files.json'
    for f in json.loads(manifest.read_text()):
        with (a.model/f['file']).open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
        if actual!=f['sha256']:raise ValueError('model identity mismatch')
    if (a.model/'requirements.txt').exists() or any(a.model.glob('*.py')):raise ValueError('no model-side installer or code accepted')
    if a.audio.stat().st_size>1048576:raise ValueError('input budget')
    audio_sha=hashlib.sha256(a.audio.read_bytes()).hexdigest()
    if audio_sha!=a.input_sha256:raise ValueError('registered input version mismatch')
    with wave.open(str(a.audio),'rb') as wav:
        frames=wav.getnframes()
        if wav.getcomptype()!='NONE' or wav.getnchannels()!=1 or wav.getsampwidth()!=2 or wav.getframerate()!=16000 or not 16000<=frames<=480000 or len(wav.readframes(frames))!=frames*2:raise ValueError('unsupported short PCM input')
    versions={k:importlib.metadata.version(k) for k in ('funasr','torch','torchaudio','numpy')}
    if versions!={'funasr':'1.2.6','torch':'2.6.0+cpu','torchaudio':'2.6.0+cpu','numpy':'1.26.4'}:raise ValueError('runtime version mismatch')
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
    import torch
    from funasr import AutoModel
    torch.set_num_threads(4)
    parameters={'device':'cpu','ncpu':4,'language':'zh','use_itn':False,'output_timestamp':True,'batch_size':1,'vad_model':None,'disable_update':True,'trust_remote_code':False}
    start=time.perf_counter();model=AutoModel(model=str(a.model),device='cpu',ncpu=4,disable_update=True,trust_remote_code=False);loaded=time.perf_counter()
    raw=model.generate(input=str(a.audio),cache={},language='zh',use_itn=False,output_timestamp=True,batch_size=1)
    end=time.perf_counter()
    weights=next(f['sha256'] for f in json.loads(manifest.read_text()) if f['file']=='model.pt')
    result={'scope':'actual-local-SenseVoiceSmall-registered-audio','taskId':a.task_id,'inputSha256':audio_sha,
            'modelRevision':REVISION,'modelWeightsSha256':weights,'versions':versions,'parameters':parameters,
            'loadSeconds':loaded-start,'transcribeSeconds':end-loaded,'raw':raw,
            'speakerStatus':'unknown','timestampStatus':'model-estimates-not-verified','factVerified':False}
    encoded=json.dumps(result,ensure_ascii=False,allow_nan=False).encode()
    if len(encoded)>262144:raise ValueError('output budget')
    with a.output.open('xb') as stream:stream.write(encoded)

if __name__=='__main__':main()
