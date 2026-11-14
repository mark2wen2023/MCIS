"""Ephemeral terminal demo: no listeners, remote URLs, browser or real-case input."""
import argparse
import asyncio
import base64
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from starlette.requests import Request
from ..config import Settings
from ..db import Database
from ..cases.router import create_case
from ..evidence_intake.router import commit_input
from ..evidence_intake.parser import preview
from . import local
from .trial_client import InvestigatorTrialClient

CASE='CASE-TRIAL-FICTIONAL'
UTC='2026-05-18T06:15:00Z'


def json_request(body):
    encoded=json.dumps(body).encode()
    async def receive():return {'type':'http.request','body':encoded,'more_body':False}
    return Request({'type':'http','method':'POST','path':'/internal-fixture',
        'headers':[(b'content-type',b'application/json')]},receive)


async def prepare(db,settings):
    """Trusted local fixture creation via existing service functions, no old app."""
    ctx=SimpleNamespace(db=db,settings=settings,role='LeadInvestigator',operator='fictional-demo-host')
    create_case({'caseId':CASE,'schemaVersion':'1.0.0','title':'虚构隔离演示',
        'accidentType':'Collision','incidentTimeUtc':UTC,'caseEpochUtc':UTC,
        'displayTimeZoneOffsetMinutes':480,'incidentLocation':{'latDeg':0,'lonDeg':0},
        'isFictionalDemo':True},ctx)
    for index,heading in enumerate((45,50),1):
        raw=f'utc,heading\n{UTC},{heading}\n'.encode()
        body={'profile':'mcis-evidence-intake-v1','fileName':f'fictional-{index}.csv',
            'contentBase64':base64.b64encode(raw).decode(),'title':f'虚构来源{index}',
            'source':'synthetic demo','extractedBy':'fictional-demo-host','extractedUtc':UTC,
            'category':'AIS','confidentiality':'Restricted','note':'非真实事故资料'}
        result,_=preview(body,raw,CASE,ctx.operator,ctx.role)
        await commit_input(CASE,json_request({**body,'confirmed':True,'requestDigest':result['requestDigest']}),ctx)
    with db.session() as session:
        subject=local.create_subject(session)
        token=local.issue_session(session,subject,lifetime_seconds=300)
        local.set_membership(session,subject,CASE,role='LeadInvestigator',can_save_unreviewed=True)
    return token


async def run_demo(core_command,choice=None,*,interactive_input=input):
    """Only built-in fictional data. Temporary workspace removed before return."""
    with tempfile.TemporaryDirectory(prefix='mcis-isolated-demo-') as directory:
        root=Path(directory)
        settings=Settings(data_dir=root,db_url=f'sqlite:///{root/"demo.db"}',seed_demo=False,
            core_cmd=core_command,core_timeout_s=15,host='127.0.0.1',port=0)
        settings.blob_dir.mkdir(parents=True)
        db=Database(settings.resolved_db_url)
        try:
            db.create_all()
            token=await prepare(db,settings)
            async with InvestigatorTrialClient(db=db,settings=settings,session_token=token) as client:
                del token
                cases=await client.cases()
                if len(cases['items'])!=1 or cases['items'][0]['caseId']!=CASE:raise ValueError('catalog')
                catalog=await client.sources(CASE)
                ids=[item['evidenceId'] for item in catalog['items']]
                if len(ids)!=2:raise ValueError('source catalog')
                if choice is None:
                    choice=interactive_input('虚构来源：1（45°）、2（50°）、both（对比两份）；q退出：').strip()
                if choice=='q':
                    output={'fixture':'fictional','cancelled':True,'saved':False}
                else:
                    if choice not in ('1','2','both'):raise ValueError('choice')
                    selected=ids if choice=='both' else [ids[int(choice)-1]]
                    request={'sources':[{'evidenceId':eid,'csvMapping':{'timeColumn':'utc','columns':[{'column':'heading','kind':'Heading'}]}} for eid in selected]}
                    await client.select(CASE,request)
                    result=await client.execute()
                    output={'fixture':'fictional','caseId':CASE,'runId':result['runId'],
                        'saved':True,'read':True,'status':'unreviewed','selectedSourceIds':selected,
                        'sourcesImported':result['serverPreview']['result']['stats']['sourcesImported'],
                        'conflicts':[{'summary':c['summary'],'delta':c.get('delta'),'deltaUnit':c.get('deltaUnit')}
                            for c in result['serverPreview']['result']['conflicts']],
                        'observationApproval':'not_assessed','sourceRelationship':'not_verified',
                        'coreImplementationVersionStatus':'not_attested'}
        finally:db.engine.dispose()
    return {**output,'temporaryDataCleaned':True,'productionLogin':False,'networkListener':False}


def main(argv=None):
    parser=argparse.ArgumentParser(description='MCIS虚构数据隔离终端演示，不开启任何监听服务')
    parser.add_argument('--core-command',required=True,help='可信host指定的既有实际W2执行命令；不安装软件')
    parser.add_argument('--choice',choices=('1','2','both','q'))
    parser.add_argument('--json',action='store_true',help='输出无凭据的演示结果摘要')
    args=parser.parse_args(argv)
    if args.json and args.choice is None:
        parser.error('--json requires --choice')
    try:result=asyncio.run(run_demo(args.core_command,args.choice))
    except (Exception,KeyboardInterrupt):
        print('演示未完成；请检查可信核心程序或输入。未输出凭据或内部错误。')
        return 2
    if args.json:print(json.dumps(result,ensure_ascii=False))
    else:
        print('虚构隔离演示：'+('已退出，未计算。' if result.get('cancelled') else '已计算、保存并读取未审核结果。'))
        if not result.get('cancelled'):
            print(f"来源数：{result['sourcesImported']}；冲突候选：{len(result['conflicts'])}")
            for c in result['conflicts']:print(f"差异：{c['delta']} {c['deltaUnit']}")
        print('临时演示数据已清理；非真实事故，非生产登录，未审核，不证明来源互证。')
    return 0


if __name__=='__main__':raise SystemExit(main())
