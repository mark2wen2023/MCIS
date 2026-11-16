"""Opt-in actual subprocess public sample task test; no fake recognizer, no browser."""
import argparse,base64,json,tempfile,hashlib,shutil
from pathlib import Path
from fastapi.testclient import TestClient
from mcis_service.audio_review.app import create_audio_review_app
from mcis_service.audio_review.tasks import LocalRuntime
from mcis_service.cases.models import CaseRow
from mcis_service.db import put_doc
from tests.conftest import make_settings,H


def run(audio_path,python,model,output):
    audio=audio_path.read_bytes();output.mkdir(parents=True,exist_ok=False)
    cid='SYNTHETIC-PUBLIC-ASR-TASK';base='/api/v1/cases/'+cid;taskid='a'*32
    with tempfile.TemporaryDirectory(prefix='mcis-real-asr-task-') as folder:
        settings=make_settings(Path(folder),False);app=create_audio_review_app(settings,sensevoice_runtime=LocalRuntime(python,model))
        with app.state.db.session() as s:
            put_doc(s,CaseRow,cid,cid,{'caseId':cid,'schemaVersion':'1.0.0','title':'Public demo task in synthetic case','isFictionalDemo':True,
                'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0})
        with TestClient(app) as c:
            body={'profile':'mcis-evidence-intake-v1','fileName':'public-funasr-demo.wav','title':'Public FunASR demonstration',
                'source':'modelscope/FunASR c1e3018bf0b16ac10d40fe7cf902cafd624ee4dd runtime/funasr_api/asr_example.wav',
                'extractedBy':'developer trial','extractedUtc':'2026-11-16T00:00:00Z','category':'Other','confidentiality':'Restricted',
                'note':'public noncase audio, not independent human hearing','contentBase64':base64.b64encode(audio).decode()}
            p=c.post(base+'/evidence-intakes:preview',json=body);assert p.status_code==200,p.text
            r=c.post(base+'/evidence-intakes:commit',json={**body,'requestDigest':p.json()['requestDigest'],'confirmed':True});assert r.status_code==200,r.text
            receipt=r.json()['requestDigest'];request={'taskId':taskid,'audioReceipt':receipt,'confirmed':True}
            r=c.post(base+'/audio-asr-tasks',json=request)
            job=settings.data_dir/'audio-asr-jobs'/taskid
            if (job/'worker.log').exists():shutil.copy2(job/'worker.log',output/'worker.log')
            assert r.status_code==201,r.text
            task=r.json();assert task['status']=='succeeded' and task['asrExecutedByService'] is True
            status=c.get(base+'/audio-asr-tasks/'+taskid);assert status.status_code==200 and status.json()==task
            run=c.get(base+'/audio-reviews/'+task['runId']);assert run.status_code==200,run.text
            assert run.json()['asrExecutedByService'] is True
            assert run.json()['initial']['machineDraft']['transcript']['segments']==[]
            artifacts={}
            for kind in ('raw','candidate'):
                a=c.post(base+'/audio-asr-tasks/'+taskid+'/artifacts/'+kind+':download',json={'purpose':'public task result verification'})
                assert a.status_code==200 and hashlib.sha256(a.content).hexdigest()==task['artifacts'][kind]['sha256']
                artifacts[kind]=a.json();(output/(kind+'.json')).write_bytes(a.content)
            human=c.post(base+'/audio-reviews/'+task['runId']+'/revisions',json={'expectedRevision':0,'segmentId':'sv-1','text':'欢迎大家来体验达摩院推出的语音识别模型','hearingStatus':'pending','startMs':None,'endMs':None,'reason':'开发者仅对照上游参考文字，未实际听校'})
            assert human.status_code==200,human.text
            original=c.post(base+'/evidence-intakes/'+receipt+':download',json={'purpose':'original byte equality after actual local ASR'})
            assert original.status_code==200 and original.content==audio
            assert c.post(base+'/audio-asr-tasks',json=request).status_code==409
            assert c.get(base+'/export',headers=H('LeadInvestigator')).status_code==409
        with TestClient(create_audio_review_app(settings)) as restarted:
            assert restarted.get(base+'/audio-asr-tasks/'+taskid).json()['status']=='succeeded'
            assert restarted.get(base+'/audio-reviews/'+task['runId']).json()['revision']==1
        (output/'result.json').write_text(json.dumps({'task':task,'savedRun':human.json(),'originalBytesEqual':True,'restartRead':True,'duplicateStartStatus':409,'archiveStatus':409,'browserTested':False,'humanListened':False},ensure_ascii=False,indent=2))
    print('PASS actual local worker -> task -> v3 pending draft -> human pending revision -> restart; original bytes unchanged')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('audio',type=Path);p.add_argument('python',type=Path);p.add_argument('model',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.audio,a.python,a.model,a.output)
