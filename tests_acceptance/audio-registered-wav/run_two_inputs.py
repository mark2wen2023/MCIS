"""Opt-in real CPU tasks: public Mandarin speech plus generated silence, no external API."""
import argparse,hashlib,importlib.util,io,json,tempfile,wave
from pathlib import Path
from fastapi.testclient import TestClient
from tests.test_audio_review_candidate import local,intake,BASE
from mcis_service.audio_review.app import create_audio_review_app,Revision
from mcis_service.audio_review.tasks import LocalRuntime


def run(sample,python,model,output):
    output.mkdir(parents=True,exist_ok=False)
    prior=Path(__file__).resolve().parents[1]/'audio-sensevoice-tasks/run_public_task.py'
    spec=importlib.util.spec_from_file_location('public_task',prior);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.run(sample,python,model,output/'public-speech')
    destination=output/'synthetic-silence';destination.mkdir()
    buf=io.BytesIO()
    with wave.open(buf,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(b'\0\0'*16000)
    audio=buf.getvalue();(destination/'synthetic-silence.wav').write_bytes(audio)
    with tempfile.TemporaryDirectory(prefix='mcis-synthetic-asr-') as folder:
        g=local.__wrapped__(Path(folder));c,app,settings=next(g)
        try:
            app.state.audio_asr_runtime=LocalRuntime(python,model)
            receipt=intake(c,audio,'synthetic-generated-silence-1s.wav');body={'taskId':'b'*32,'audioReceipt':receipt,'confirmed':True}
            response=c.post(BASE+'/audio-asr-tasks',json=body)
            assert response.status_code in (201,409),response.text
            task=c.get(BASE+'/audio-asr-tasks/'+body['taskId']);assert task.status_code==200
            status=task.json()['status'];assert status in ('succeeded','failed'),task.text
            job=settings.data_dir/'audio-asr-jobs'/body['taskId']
            for name in ('raw.json','worker.log'):
                if (job/name).exists():(destination/name).write_bytes((job/name).read_bytes())
            if status=='failed':
                with app.state.db.session() as session:assert session.query(Revision).count()==0
            else:
                result=c.get(BASE+'/audio-reviews/'+task.json()['runId']);assert result.status_code==200
                assert result.json()['factVerified'] is False
                (destination/'pending-run.json').write_text(json.dumps(result.json(),ensure_ascii=False,indent=2))
            original=c.post(BASE+'/evidence-intakes/'+receipt+':download',json={'purpose':'synthetic source preservation check'})
            assert original.status_code==200 and original.content==audio
            assert c.post(BASE+'/audio-asr-tasks',json=body).status_code==409
            with TestClient(create_audio_review_app(settings)) as restarted:
                assert restarted.get(BASE+'/audio-asr-tasks/'+body['taskId']).json()['status']==status
            (destination/'result.json').write_text(json.dumps({'inputKind':'generated-silence-not-speech','inputSha256':hashlib.sha256(audio).hexdigest(),
                'sourceFrames':16000,'sourceRateHz':16000,'httpStatus':response.status_code,'response':response.json(),'task':task.json(),
                'originalBytesUnchanged':True,'repeatIdStatus':409,'workerResultPresent':(job/'raw.json').exists(),'browserTested':False},ensure_ascii=False,indent=2))
            print('SYNTHETIC SILENCE actual task status:',status)
        finally:
            try:next(g)
            except StopIteration:pass

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('sample',type=Path);p.add_argument('python',type=Path);p.add_argument('model',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.sample,a.python,a.model,a.output)
