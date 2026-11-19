"""Check a prepared isolated demo; --serve explicitly starts loopback only.
No inference, role injection or authorization guarantee. No automatic retry.
"""
import argparse
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
from mcis_service.config import Settings, SERVICE_ROOT, PROJECT_ROOT
from mcis_service.media_review_demo import create_media_review_demo
from tools.media_review_demo.constants import CID, PUBLIC

HOST='127.0.0.1'
PORT=8766
KEYS={'status','dataDir','dbFile','caseId','imageOrigin','audioOrigin','modelExecuted',
      'browserVerified','archiveSupported','imageRunId','audioRunId','receipts','sha256',
      'pages','publicAudioPinnedHashes'}


def need(ok, reason):
    if not ok: raise ValueError(reason)


def unique(pairs):
    out={}
    for k,v in pairs:
        need(k not in out,'duplicate manifest field');out[k]=v
    return out


def check_manifest(manifest, root):
    root=Path(root).absolute();manifest=Path(manifest).absolute()
    need(root==root.resolve() and root.is_dir() and root.name.startswith('mcis-media-demo-'),'explicit isolated root required')
    need(root!=SERVICE_ROOT/'data' and manifest==root/'demo-manifest.json' and
         not manifest.is_symlink(),'manifest location')
    with manifest.open('rb') as stream: raw=stream.read(65537)
    need(len(raw)<=65536,'manifest size')
    doc=json.loads(raw.decode('utf-8'),object_pairs_hook=unique)
    need(type(doc) is dict and set(doc)==KEYS,'complete preparation manifest required')
    need(doc['status']=='prepared' and doc['caseId']==CID,'preparation incomplete or different case')
    need(all(doc[k] is False for k in ('modelExecuted','browserVerified','archiveSupported')),'demo scope')
    need(doc['dataDir']==str(root) and doc['dbFile']==str(root/'demo.db'),'database location mismatch')
    need(doc['pages']==['/image-review-lab','/audio-review-lab'],'pages')
    need(doc['imageOrigin']=='generated-schematic-and-fabricated-OCR-not-recognized','image origin')
    public=doc['audioOrigin']=='public-sample-with-saved-local-output'
    need(public or doc['audioOrigin']=='generated-tone-and-fabricated-draft','audio origin')
    need(doc['publicAudioPinnedHashes']==(PUBLIC if public else None),'public provenance declaration')
    members={'pdf','image','raw','candidate','audio','audio-draft'}
    if public: members|={'audio-license','asr-raw'}
    for key in ('receipts','sha256'):
        need(type(doc[key]) is dict and set(doc[key])==members,'complete source mapping')
        need(all(type(v) is str and re.fullmatch('[a-f0-9]{64}',v) for v in doc[key].values()),'digest format')
    need(type(doc['imageRunId']) is str and re.fullmatch('OCR-[a-f0-9]{32}',doc['imageRunId']),'image run')
    need(type(doc['audioRunId']) is str and re.fullmatch('AR-[a-f0-9]{32}',doc['audioRunId']),'audio run')
    db=root/'demo.db'
    need(db.is_file() and not db.is_symlink(),'existing demo database required')
    # Metadata-only check. No source-byte read or bypass of product authorization.
    with closing(sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)) as conn:
        conn.execute('BEGIN')
        cases=conn.execute('SELECT case_id,doc FROM cases LIMIT 2').fetchall()
        need(len(cases)==1 and cases[0][0]==CID,'demo must contain only its prepared case')
        case=json.loads(cases[0][1]);need(case.get('isFictionalDemo') is True,'synthetic case marker')
        def initial(table,run):
            rows=conn.execute(f'SELECT doc FROM {table} WHERE case_id=? AND run_id=? AND revision=0 LIMIT 2',(CID,run)).fetchall()
            need(len(rows)==1,'prepared run association missing')
            return json.loads(rows[0][0])
        image=initial('image_ocr_review_records',doc['imageRunId'])
        audio=initial('audio_review_revisions',doc['audioRunId'])
        need(image['bindings']=={k:doc['receipts'][k] for k in ('pdf','image','raw','candidate')},'image receipts mismatch')
        need(all(image['sourceVersions'][k]['sha256']==doc['sha256'][k] for k in image['bindings']),'image version mismatch')
        need(audio['audioReceipt']==doc['receipts']['audio'] and audio['draftReceipt']==doc['receipts']['audio-draft'],'audio receipts mismatch')
        need(audio['draftBytesSha256']==doc['sha256']['audio-draft'] and
             audio['machineDraft']['source']['currentSha256']==doc['sha256']['audio'],'audio version mismatch')
    return doc


def settings_for(doc):
    return Settings(data_dir=Path(doc['dataDir']),db_url='sqlite:///'+doc['dbFile'],seed_demo=False,
                    host=HOST,port=PORT,core_cmd=str(PROJECT_ROOT/'tools/mcis-core/mcis-core.sh'),core_timeout_s=60)


def checked_app(manifest, root):
    doc=check_manifest(manifest,root)
    app=create_media_review_demo(settings_for(doc))
    need(app.state.image_ocr_runtime is None and app.state.audio_asr_runtime is None,'model runtime must remain disabled')
    return app,doc


def summary(doc):
    return {'caseId':doc['caseId'],'imageRunId':doc['imageRunId'],'audioRunId':doc['audioRunId'],
            'pages':[f'http://{HOST}:{PORT}'+p for p in doc['pages']],
            'notice':'仅核对已有结果；模型关闭。授权仍由原接口检查，页面授权与浏览器未验。',
            'sourceBytesVerified':False,'browserVerified':False,'archiveSupported':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--manifest',required=True,type=Path)
    parser.add_argument('--serve',action='store_true')
    args=parser.parse_args()
    if not args.serve:
        print(json.dumps(summary(check_manifest(args.manifest,args.root)),ensure_ascii=False,indent=2));return
    app,doc=checked_app(args.manifest,args.root)
    print(json.dumps(summary(doc),ensure_ascii=False,indent=2))
    import uvicorn
    uvicorn.run(app,host=HOST,port=PORT,reload=False,workers=1)


if __name__=='__main__':main()
