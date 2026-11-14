"""Opt-in one-shot local inference check using only a fixed fictional interview.
No environment model selection, downloads, listener, fixture-provider fallback or saved result.
"""
import argparse
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
from ..config import Settings
from ..db import Database,put_doc
from ..cases.router import create_case
from ..identity import local
from ..identity.demo import CASE,UTC
from ..interviews.models import InterviewRow
from ..common import contracts
from .extraction_review_fixture import document,RECORD
from . import host_extraction as h,model_client

BASE={'input':'fixed-fictional-interview','productionLogin':False,'modelIdentityVerified':False,
      'saved':False,'factVerified':False,'fixtureFallback':False,'completeCaseValidation':False}

def selected_config(base_url=None,model=None):
    if base_url is None and model is None:return None
    return model_client.validate_config(model_client.ModelConfig(base_url,model))

def run_probe(*,base_url=None,model=None):
    try:cfg=selected_config(base_url,model)
    except Exception:return {**BASE,'status':'invalid_configuration','endpointConfigured':False,'requestAttempted':False,'requestOutcome':'not_attempted','protectedExtractionSucceeded':False}
    if cfg is None:return {**BASE,'status':'not_connected','endpointConfigured':False,'requestAttempted':False,'requestOutcome':'not_attempted','protectedExtractionSucceeded':False}
    started=False
    try:
        with tempfile.TemporaryDirectory(prefix='mcis-local-extraction-probe-') as directory:
            root=Path(directory);settings=Settings(data_dir=root,db_url=f'sqlite:///{root/"probe.db"}',seed_demo=False,core_cmd='unused',host='127.0.0.1',port=0)
            settings.blob_dir.mkdir(parents=True);db=Database(settings.resolved_db_url)
            try:
                db.create_all()
                ctx=SimpleNamespace(db=db,settings=settings,role='LeadInvestigator',operator='fictional-probe-host')
                create_case({'caseId':CASE,'schemaVersion':'1.0.0','title':'虚构本地抽取验证',
                    'accidentType':'Collision','incidentTimeUtc':UTC,'caseEpochUtc':UTC,
                    'displayTimeZoneOffsetMinutes':480,'incidentLocation':{'latDeg':0,'lonDeg':0},'isFictionalDemo':True},ctx)
                doc=document();contracts.validate('interview',doc)
                with db.session() as s:
                    subject=local.create_subject(s);token=local.issue_session(s,subject,lifetime_seconds=300)
                    local.set_membership(s,subject,CASE,role='LeadInvestigator',can_save_unreviewed=False)
                    put_doc(s,InterviewRow,CASE,RECORD,doc)
                descriptor=h.describe(db,settings,token,CASE,RECORD)
                started=True
                result=h.run(db,settings,token,CASE,RECORD,descriptor['bindingDigest'],h.LocalProvider(cfg))
                summary={**BASE,'status':'validated_response','endpointConfigured':True,'requestAttempted':True,'requestOutcome':'validated_response',
                    'protectedExtractionSucceeded':True,'configuredModel':cfg.model,'configuredModelMeaning':'unverified-declaration',
                    'proposalCount':len(result['proposals']),'citationCount':len(result['citations']),
                    'citationChecks':'exact_quote_match_only_not_fact_verification','sourceScope':result['receipt']['sourceScope'],
                    'outputMeaning':'unreviewed-proposals-not-expert-accuracy','runChecksum':result['receipt']['runChecksum'],
                    'persistentAudit':False,'signature':False}
            finally:db.engine.dispose()
        return summary
    except Exception:
        # run() deliberately hides transport/parse/auth errors. Do not claim a
        # request did/did not reach the endpoint when no success receipt exists.
        return {**BASE,'status':'unconfirmed','endpointConfigured':True,'requestAttempted':None if started else False,
                'requestOutcome':'not_confirmed' if started else 'not_attempted','protectedExtractionSucceeded':False}

class Parser(argparse.ArgumentParser):
    def error(self,message):raise ValueError()

def main(argv=None):
    parser=Parser(description='Fixed fictional local extraction probe; no automatic connection.')
    parser.add_argument('--base-url');parser.add_argument('--model')
    try:
        args=parser.parse_args(argv);result=run_probe(base_url=args.base_url,model=args.model)
    except Exception:result={**BASE,'status':'invalid_configuration','endpointConfigured':False,'requestAttempted':False,'requestOutcome':'not_attempted','protectedExtractionSucceeded':False}
    print(json.dumps(result,ensure_ascii=False,separators=(',',':')))
    return 0 if result['status'] in ('not_connected','validated_response') else 2
if __name__=='__main__':raise SystemExit(main())
