import os
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
import json,time,pathlib,hashlib,importlib.metadata
import torch
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
root=pathlib.Path('/workspace/mcis-sensevoice-trial');audio=root/'sample/asr_example.wav'
torch.set_num_threads(4)
parameters={'device':'cpu','ncpu':4,'language':'zh','use_itn':False,'output_timestamp':True,'batch_size':1,'vad_model':None,'disable_update':True,'trust_remote_code':False}
t=time.perf_counter();model=AutoModel(model=str(root/'model'),device='cpu',ncpu=4,disable_update=True,trust_remote_code=False);loaded=time.perf_counter()
raw=model.generate(input=str(audio),cache={},language='zh',use_itn=False,batch_size=1,output_timestamp=True);ended=time.perf_counter()
result={'scope':'actual-local-SenseVoiceSmall-public-noncase-sample','inputSha256':hashlib.sha256(audio.read_bytes()).hexdigest(),'modelRevision':'3847d57b6bdf2dd8875cb1508d2af43d80a16bf7','modelWeightsSha256':hashlib.sha256((root/'model/model.pt').read_bytes()).hexdigest(),'parameters':parameters,'versions':{p:importlib.metadata.version(p) for p in ['funasr','torch','torchaudio','numpy']},'loadSeconds':loaded-t,'transcribeSeconds':ended-loaded,'raw':raw,'text':[rich_transcription_postprocess(r['text']) for r in raw],'timestampStatus':'unknown-unless-actually-returned-not-inferred','speakerStatus':'unknown','referenceText':'欢迎大家来体验达摩院推出的语音识别模型','referenceStatus':'upstream README expected output, not independent human listening'}
(root/'timestamp-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
