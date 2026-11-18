"""Prepare a fresh isolated review demo via existing APIs; never start models/server.
Default: generated schematic PDF/PNG + tone and fabricated drafts.
Optional public audio: exact pinned FunASR sample/license and saved local output.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import wave
import zlib
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from reportlab.pdfgen.canvas import Canvas
from mcis_service.config import Settings
from mcis_service.media_review_demo import create_media_review_demo
from mcis_service.image_review.ppocr import convert as convert_ocr
from tools.audio_transcript_contract.machine_contract import PROFILE, output_digest
from tools.audio_transcript_contract.contract import digest
from tools.audio_transcript_contract.sensevoice_candidate import convert as convert_asr

PUBLIC={
    'audio': 'a1bd32dc78493c123f9625a66deee562aed2895f53fbc39f2cca3be7e6f4f20f',
    'license': 'f382b62dcc61fc566b9215b1e3b604b539bfd96ed52ae1eeff5090f6dc176057',
    'result': '1642c59d687568c5cbf9e6dc59b0c2fc20405d48d0253206f5935f79c23d63c2'}
PUBLIC_URL='https://github.com/modelscope/FunASR/blob/c1e3018bf0b16ac10d40fe7cf902cafd624ee4dd/runtime/funasr_api/asr_example.wav'
CID='MEDIA-DEMO-SYNTHETIC'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return json.dumps(value,ensure_ascii=False,allow_nan=False).encode()


def checked_public(paths):
    if set(paths)!=set(PUBLIC):raise ValueError('public audio requires sample, license and saved result')
    out={}
    for key,path in paths.items():
        with Path(path).open('rb') as f:raw=f.read(2*1024*1024+1)
        if len(raw)>2*1024*1024 or sha(raw)!=PUBLIC[key]:raise ValueError('public '+key+' digest mismatch')
        out[key]=raw
    result=json.loads(out['result'])
    if result['inputSha256']!=PUBLIC['audio'] or result['modelRevision']!='3847d57b6bdf2dd8875cb1508d2af43d80a16bf7':raise ValueError('public result binding')
    return out


def synthetic_assets():
    # Valid schematic image, deliberately no purported report OCR or page-render proof.
    width,height=200,100
    pixels=b''.join(b'\0'+b''.join(bytes((30,90,180) if 20<=x<180 and 20<=y<80 else (255,255,255)) for x in range(width)) for y in range(height))
    def chunk(kind,raw):return struct.pack('>I',len(raw))+kind+raw+struct.pack('>I',zlib.crc32(kind+raw)&0xffffffff)
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b'')
    pdf=io.BytesIO();c=Canvas(pdf,pagesize=(400,300),invariant=1)
    c.drawString(20,270,'SYNTHETIC REVIEW DEMO - NOT AN ACCIDENT REPORT')
    c.drawString(20,245,'Schematic rectangle. Page-image linkage is a declaration.')
    c.setFillColorRGB(.12,.35,.7);c.rect(40,70,320,120,fill=1);c.save()
    audio=io.BytesIO()
    with wave.open(audio,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
        import math
        w.writeframes(b''.join(struct.pack('<h',int(1200*math.sin(2*math.pi*440*n/16000))) for n in range(16000)))
    raw=encoded({'page_index':None,'rec_texts':['SYNTHETIC rectangle description - not OCR'], 'rec_scores':[0],
                 'rec_boxes':[[20,20,180,80]],'rec_polys':[[[20,20],[180,20],[180,80],[20,80]]]})
    return {'pdf':pdf.getvalue(),'image':png,'audio':audio.getvalue(),'raw':raw}


def synthetic_draft(source):
    transcript=dict(revision=1,parentArtifactSha256=None,method='machine_asr_draft',segments=[],
        unlocatedSegments=[dict(id='demo-1',text='合成提示：原音为测试音，不含语音；这不是识别结果。',speaker={'status':'unknown','id':None},reason='time_unknown')],
        reviewStatus='pending',timeBasis='original_audio_ms')
    receipt=dict(executionId='synthetic-no-execution',provider='synthetic-fixture',model='no-model',
        modelWeightsSha256=sha(b'no-model'),runtimeVersion='not-executed',toolVersion='demo-v1',parametersSha256=sha(b'synthetic'),
        inputSha256=source['currentSha256'],trackIndex=0,outputSha256=output_digest(transcript),outcome='completed',origin='synthetic_contract_fixture')
    doc=dict(profile=PROFILE,version=2,source=source,transcript=transcript,receipt=receipt)
    doc['artifactSha256']=digest(doc);return doc


def prepare(parent, public_paths=None):
    # Validate optional inputs before creating a new directory; never accept an existing DB.
    public=checked_public(public_paths) if public_paths is not None else None
    assets=synthetic_assets()
    if public:assets['audio']=public['audio']
    root=Path(tempfile.mkdtemp(prefix='mcis-media-demo-',dir=Path(parent).resolve()))
    settings=Settings(data_dir=root,db_url=f'sqlite:///{root / "demo.db"}',seed_demo=False)
    result={'status':'preparing','dataDir':str(root),'dbFile':str(root/'demo.db'),'caseId':CID,
            'imageOrigin':'generated-schematic-and-fabricated-OCR-not-recognized',
            'audioOrigin':'public-sample-with-saved-local-output' if public else 'generated-tone-and-fabricated-draft',
            'modelExecuted':False,'browserVerified':False,'archiveSupported':False}
    def record():
        (root/'demo-manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    record()
    try:
        app=create_media_review_demo(settings)
        if app.state.image_ocr_runtime is not None or app.state.audio_asr_runtime is not None:raise ValueError('runtime unexpectedly configured')
        with TestClient(app) as client:
            def call(method,path,body=None,status=200):
                response=client.request(method,path,json=body,headers={'X-MCIS-Operator':'Synthetic demo preparer'})
                if response.status_code!=status:raise ValueError('demo API failed: '+str(response.status_code))
                return response.json()
            call('POST','/api/v1/cases',dict(caseId=CID,schemaVersion='1.0.0',title='合成图音核对演示（非事故案件）',
                accidentType='SyntheticDemo',isFictionalDemo=True,caseEpochUtc='2026-01-01T00:00:00Z',incidentTimeUtc='2026-01-01T00:00:00Z',
                incidentLocation={'lonDeg':0,'latDeg':0},displayTimeZoneOffsetMinutes=0,summaryNotes='全部案件时空为演示占位，不代表真实事故。'),201)
            base='/api/v1/cases/'+CID
            receipts={};hashes={}
            def intake(key,raw,name,source):
                body=dict(profile='mcis-evidence-intake-v1',fileName=name,title=name,source=source,extractedBy='isolated demo preparer',
                    extractedUtc=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),category='Other',confidentiality='Restricted',
                    note='演示材料，非已确认事实；不代表自动识别或人工听校。',contentBase64=base64.b64encode(raw).decode())
                preview=call('POST',base+'/evidence-intakes:preview',body)
                saved=call('POST',base+'/evidence-intakes:commit',{**body,'requestDigest':preview['requestDigest'],'confirmed':True})
                receipts[key]=saved['requestDigest'];hashes[key]=sha(raw);return saved['requestDigest']
            description='Generated by tools/media_review_demo/prepare.py; no external document or OCR execution'
            for key,name in [('pdf','synthetic-schematic.pdf'),('image','synthetic-schematic.png'),('raw','fabricated-ocr.json')]:intake(key,assets[key],name,description)
            source=dict(pdf_sha256=hashes['pdf'],image_sha256=hashes['image'],raw_sha256=hashes['raw'],pdf_page_1based=1,printed_page='',
                        mapping_basis='synthetic-declaration-not-render-verified',width=200,height=100)
            rec={k:'synthetic-not-executed' for k in ('paddlepaddle','paddleocr','paddlex','pipeline','device')};rec['models']=['none-synthetic']
            candidate=convert_ocr(assets['raw'],source,rec)
            candidate['limitations']=['Generated schematic and fabricated output; no OCR executed.','Page mapping is a declaration, not render proof.']
            intake('candidate',encoded(candidate),'fabricated-image-candidate.json',description)
            im=call('POST',base+'/image-reviews',{'bindings':{k:receipts[k] for k in ('pdf','image','raw','candidate')},'acknowledgeArchiveBlocked':True},201)
            audio_source=PUBLIC_URL+' ; pinned repository MIT license retained; saved local output, no inference this run' if public else 'Generated 440Hz tone; fabricated draft, not speech recognition'
            intake('audio',assets['audio'],'public-example.wav' if public else 'synthetic-tone.wav',audio_source)
            context=call('GET',base+'/audio-reviews/source/'+receipts['audio'])
            if public:
                intake('audio-license',public['license'],'public-sample-LICENSE.txt',PUBLIC_URL)
                intake('asr-raw',public['result'],'saved-sensevoice-output.json',audio_source)
                draft=convert_asr(json.loads(public['result']),context['sampleSource'])['draft']
            else:draft=synthetic_draft(context['source'])
            intake('audio-draft',encoded(draft),'pending-audio-draft.json',audio_source)
            au=call('POST',base+'/audio-reviews',{'audioReceipt':receipts['audio'],'draftReceipt':receipts['audio-draft'],'acknowledgeArchiveBlocked':True},201)
            # Read through ordinary APIs before announcing preparation completed.
            call('GET',base+'/image-reviews/'+im['runId']);call('GET',base+'/audio-reviews/'+au['runId'])
            result.update(status='prepared',imageRunId=im['runId'],audioRunId=au['runId'],receipts=receipts,sha256=hashes,
                          pages=['/image-review-lab','/audio-review-lab'],publicAudioPinnedHashes=PUBLIC if public else None)
        record();return result
    except Exception:
        result['status']='incomplete-do-not-retry-in-place';record();raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent',type=Path,required=True)
    parser.add_argument('--public-audio',type=Path);parser.add_argument('--public-license',type=Path);parser.add_argument('--saved-result',type=Path)
    args=parser.parse_args();paths=None
    if any((args.public_audio,args.public_license,args.saved_result)):
        if not all((args.public_audio,args.public_license,args.saved_result)):parser.error('all three public input paths required')
        paths={'audio':args.public_audio,'license':args.public_license,'result':args.saved_result}
    print(json.dumps(prepare(args.parent,paths),ensure_ascii=False,indent=2))
