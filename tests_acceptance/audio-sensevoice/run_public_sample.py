"""Opt-in local public-sample integration; consumes saved REAL model output, no ASR call.
Usage: PYTHONPATH=.:service python .../run_public_sample.py WAV RESULT_JSON OUTPUT_DIR
No sample/media/database is added to the repository. Not a browser test.
"""
import argparse,base64,json,tempfile,hashlib
from pathlib import Path
from fastapi.testclient import TestClient
from mcis_service.audio_review.app import create_audio_review_app
from mcis_service.cases.models import CaseRow
from mcis_service.db import put_doc
from tests.conftest import make_settings,H
from tools.audio_transcript_contract.sensevoice_candidate import convert


def run(audio_path,result_path,output):
    audio=audio_path.read_bytes();recognizer=json.loads(result_path.read_text())
    assert hashlib.sha256(audio).hexdigest()==recognizer['inputSha256']
    output.mkdir(parents=True,exist_ok=False)
    cid='SYNTHETIC-PUBLIC-SENSEVOICE';base='/api/v1/cases/'+cid
    with tempfile.TemporaryDirectory(prefix='mcis-sensevoice-public-') as folder:
        settings=make_settings(Path(folder),False);app=create_audio_review_app(settings)
        with app.state.db.session() as s:
            put_doc(s,CaseRow,cid,cid,{'caseId':cid,'schemaVersion':'1.0.0','title':'Synthetic case with public FunASR demo, not an accident',
                'isFictionalDemo':True,'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z',
                'incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0})
        with TestClient(app) as c:
            def register(raw,name):
                body={'profile':'mcis-evidence-intake-v1','fileName':name,'title':name,
                    'source':'Public modelscope/FunASR c1e3018bf0b16ac10d40fe7cf902cafd624ee4dd runtime/funasr_api/asr_example.wav',
                    'extractedBy':'developer public-sample integration','extractedUtc':'2026-11-16T00:00:00Z','category':'Other',
                    'confidentiality':'Restricted','note':'Public noncase sample; synthetic case; not independent human listening',
                    'contentBase64':base64.b64encode(raw).decode()}
                p=c.post(base+'/evidence-intakes:preview',json=body);assert p.status_code==200,p.text
                r=c.post(base+'/evidence-intakes:commit',json={**body,'requestDigest':p.json()['requestDigest'],'confirmed':True});assert r.status_code==200,r.text
                return r.json()['requestDigest']
            receipt=register(audio,'public-asr-example.wav')
            response=c.get(base+'/audio-reviews/source/'+receipt);assert response.status_code==200,response.text
            context=response.json();assert context['source'] is None
            converted=convert(recognizer,context['sampleSource'])
            draft_receipt=register(json.dumps(converted['draft'],ensure_ascii=False).encode(),'sensevoice-v3-draft.json')
            r=c.post(base+'/audio-reviews',json={'audioReceipt':receipt,'draftReceipt':draft_receipt,'acknowledgeArchiveBlocked':True});assert r.status_code==201,r.text
            initial=r.json();url=base+'/audio-reviews/'+initial['runId']
            r=c.post(url+'/revisions',json={'expectedRevision':0,'segmentId':'sv-1','text':recognizer['referenceText'],
                'hearingStatus':'pending','startMs':None,'endMs':None,'reason':'开发者对照上游参考文字；未实际听校，不标记文字已核对或事实确认'})
            assert r.status_code==200,r.text
            saved=r.json();assert saved['initial']==initial['initial']
            assert saved['humanRevisions'][0]['timeStatus']=='unknown' and saved['humanRevisions'][0]['hearingStatus']=='pending'
            downloaded=c.post(base+'/evidence-intakes/'+receipt+':download',json={'purpose':'public noncase source byte equality check'})
            assert downloaded.status_code==200 and downloaded.content==audio
            exported=c.get(base+'/export',headers=H('LeadInvestigator'));assert exported.status_code==409
        with TestClient(create_audio_review_app(settings)) as c:
            restored=c.get(url);assert restored.status_code==200 and restored.json()==saved
        results={'scope':'developer-real-TestClient-public-audio-and-real-saved-model-output','source':context,
                 'conversionInspection':converted['inspection'],'saved':saved,'originalBytesUnchanged':True,
                 'restartReadEqual':True,'archiveStatus':409,'browserTested':False,'humanListened':False}
        (output/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print('PASS: original bytes, v3 admission, pending human revision, restart, archive409; no browser')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('audio',type=Path);p.add_argument('recognizer_result',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.audio,a.recognizer_result,a.output)
