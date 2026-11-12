"""Current saved-point CPA: exact-time pairing, no interpolation or persistence."""
from __future__ import annotations
import hashlib
import json
import math
import re
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from sqlalchemy import select, text
from ..cases import service as cases
from ..cases.models import TrackPointRow, VesselRow
from ..common.context import Ctx, CtxDep, problem
from ..db import get_doc
from ..redaction.gateway import require
from ..colreg.router import _core

PROFILE = 'MCIS-CURRENT-CPA-1'
LIMIT = 5000

class NoStore(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        async def handler(request: Request):
            try:
                response = await original(request)
            except HTTPException as exc:
                response = JSONResponse(status_code=exc.status_code, content=exc.detail)
            except RequestValidationError:
                response = JSONResponse(status_code=422,content={'code':'ANALYSIS_TIME_WINDOW','message':'请求参数不合法。'})
            except Exception:
                response = JSONResponse(status_code=500,content={'code':'ANALYSIS_READ_FAILED','message':'计算或读取失败，未返回部分结果。'})
            response.headers['Cache-Control'] = 'no-store'
            return response
        return handler

router = APIRouter(prefix='/api/v1', tags=['analysis'], route_class=NoStore)

def reject(code='ANALYSIS_INVALID_INPUT', message='已存输入不满足计算合同，未生成部分结果。', status=422):
    raise problem(status, code, message)

def number(v):
    if type(v) not in (int, float):return False
    try:return math.isfinite(v)
    except OverflowError:return False

def utc(v):
    if not isinstance(v, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z', v): reject()
    try: return datetime.fromisoformat(v.replace('Z', '+00:00'))
    except ValueError: reject()

def geo(p):
    if not isinstance(p, dict) or not number(p.get('latDeg')) or abs(p['latDeg']) > 90 or not number(p.get('lonDeg')) or abs(p['lonDeg']) > 180: reject()
    return {'latDeg':p['latDeg'], 'lonDeg':p['lonDeg']}

def local(p, origin):
    # Spherical domain screening only; all CPA coordinates/numbers come from C#.
    a,b = math.radians(p['latDeg']), math.radians(origin['latDeg'])
    dlon = math.radians(p['lonDeg'] - origin['lonDeg'])
    h = math.sin((a-b)/2)**2 + math.cos(a)*math.cos(b)*math.sin(dlon/2)**2
    if 6371000*2*math.asin(math.sqrt(min(1,max(0,h)))) > 100000: reject('ANALYSIS_LOCAL_DOMAIN', '点位超出本轮局部计算域（距案件原点100km）。这不是安全阈值。')

def read_snapshot(ctx, case_id, own, target, start, end):
    with ctx.db.session() as s:
        if s.bind.dialect.name != 'sqlite': reject('ANALYSIS_DATABASE_UNSUPPORTED', '本轮只支持SQLite一致性读取。',503)
        s.execute(text('BEGIN'))  # real SQLite read snapshot; no writer reservation
        case = cases.load_case(s, case_id)
        level=require(ctx,s,case_id,'ais_sim')
        if level not in ('ReadOnly','ReadWrite'):reject('FORBIDDEN','当前权限不允许读取完整航迹输入。',403)
        if case.get('caseId') != case_id or not isinstance(case.get('title'),str) or type(case.get('isFictionalDemo')) is not bool: reject()
        epoch = utc(case.get('caseEpochUtc')); origin = geo(case.get('incidentLocation'))
        if abs(origin['latDeg'])>85: reject('ANALYSIS_LOCAL_DOMAIN','本轮不支持纬度绝对值大于85°的局部原点。')
        ships=[]; tracks=[]
        for vid in (own,target):
            v=get_doc(s,VesselRow,case_id,vid)
            if not v: reject('ANALYSIS_VESSEL_NOT_FOUND','请选择本案已登记的两艘不同船舶。')
            if v.get('caseId')!=case_id or v.get('vesselId')!=vid or not isinstance(v.get('name'),str): reject()
            ships.append({'vesselId':vid,'name':v['name']})
            q=select(TrackPointRow).where(TrackPointRow.case_id==case_id,TrackPointRow.vessel_id==vid)
            if start is not None:q=q.where(TrackPointRow.time_sec>=start)
            if end is not None:q=q.where(TrackPointRow.time_sec<=end)
            rows=list(s.scalars(q.order_by(TrackPointRow.time_sec,TrackPointRow.id).limit(LIMIT+1)))
            if len(rows)>LIMIT:reject('ANALYSIS_POINT_LIMIT','每船最多读取5000点，请缩小时间窗；未截断计算。')
            pts=[];previous=None
            for row in rows:
                p=row.doc
                if not isinstance(p,dict) or p.get('vesselId')!=vid or not number(p.get('timeSec')) or abs(p['timeSec'])>1e12 or p['timeSec']!=row.time_sec:reject()
                t=p['timeSec']
                if previous is not None and t<=previous:reject('ANALYSIS_DUPLICATE_TIME','同船时间不唯一，不能任意选择其中一点。')
                previous=t
                if abs((utc(p.get('utc'))-epoch).total_seconds()-t)>1e-6:reject('ANALYSIS_TIME_MISMATCH','已存UTC与案件纪元/相对秒不一致，未进行自动时间修正。')
                if set(p)-{'vesselId','timeSec','utc','latDeg','lonDeg','sogKn','cogDeg','hdgDeg','rotDegPerMin','provenance','source'}:reject()
                if p.get('hdgDeg') is not None and (not number(p['hdgDeg']) or not 0<=p['hdgDeg']<=360):reject()
                if p.get('rotDegPerMin') is not None and not number(p['rotDegPerMin']):reject()
                geo(p);local(p,origin)
                if not number(p.get('sogKn')) or p['sogKn']<0 or not number(p.get('cogDeg')) or not 0<=p['cogDeg']<=360:reject()
                if 'provenance' in p and p['provenance'] not in ('Measured','Interpolated','ManualDrawn','Simulated'):reject()
                if 'source' in p and (not isinstance(p['source'],str) or len(p['source'])>4096):reject()
                # Entire stored point participates in the digest, including optional fields.
                pts.append(dict(p))
            tracks.append(pts)
        snapshot={'caseId':case_id,'title':case['title'],'isFictionalDemo':case['isFictionalDemo'],'caseEpochUtc':case['caseEpochUtc'],
                  'origin':origin,'vessels':ships,'window':{'fromSec':start,'toSec':end},'tracks':tracks}
        try:raw=json.dumps(snapshot,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        except (ValueError,TypeError):reject()
        return snapshot,hashlib.sha256(raw).hexdigest()

def pair_points(snapshot):
    own,target=snapshot['tracks']; by_time={p['timeSec']:p for p in target}
    pairs=[]; inputs=[]
    def state(p):return {'vesselId':p['vesselId'],'latDeg':p['latDeg'],'lonDeg':p['lonDeg'],'speedKn':p['sogKn'],'courseDeg':p['cogDeg']}
    for p in own:
        q=by_time.get(p['timeSec'])
        if q is None:continue
        if utc(p['utc'])!=utc(q['utc']):reject('ANALYSIS_TIME_MISMATCH','配对点UTC不一致。')
        pairs.append({'pairId':str(len(pairs)),'timeSec':p['timeSec'],'own':state(p),'target':state(q)})
        inputs.append({'timeSec':p['timeSec'],'utc':p['utc'],'own':p,'target':q})
    return pairs,inputs

def checked_results(env,pairs,inputs):
    def bad():reject('ANALYSIS_CORE_OUTPUT','计算核心返回与输入不一致或无效的结果。',502)
    if not isinstance(env,dict) or env.get('ok') is not True or env.get('command')!='cpa' or not isinstance(env.get('coreVersion'),str) or not env['coreVersion']:bad()
    result=env.get('result');results=result.get('results') if isinstance(result,dict) else None
    if not isinstance(results,list) or len(results)!=len(pairs):bad()
    out=[]
    for p,i,r in zip(pairs,inputs,results):
        if not isinstance(r,dict) or not {'tcpaMin','timeSec'}<=set(r) or not number(r.get('timeSec')) or r.get('pairId')!=p['pairId'] or r.get('timeSec')!=p['timeSec'] or r.get('ownVesselId')!=p['own']['vesselId'] or r.get('targetVesselId')!=p['target']['vesselId']:bad()
        for k in ('currentDistanceNm','dcpaNm'):
            if not number(r.get(k)) or r[k]<0:bad()
        if type(r.get('isDegenerate')) is not bool or type(r.get('isDiverging')) is not bool:bad()
        tcpa=r.get('tcpaMin')
        velocities=[(v['speedKn']*math.sin(math.radians(v['courseDeg'])),v['speedKn']*math.cos(math.radians(v['courseDeg']))) for v in (p['own'],p['target'])]
        relative_mps=math.hypot(velocities[1][0]-velocities[0][0],velocities[1][1]-velocities[0][1])*1852/3600
        # Verify the flag outside the domain's 1e-6 m/s numerical boundary band.
        # This is not a second CPA implementation; C# remains the numeric authority.
        if abs(relative_mps-.01)>1e-6 and r['isDegenerate']!=(relative_mps<.01):bad()
        if r['dcpaNm']>r['currentDistanceNm']+1e-6:bad()
        if r['isDegenerate']:
            if tcpa is not None or r['isDiverging'] or abs(r['dcpaNm']-r['currentDistanceNm'])>1e-6:bad()
        elif not number(tcpa) or (tcpa != 0 and r['isDiverging']!=(tcpa<0)):bad()
        out.append({**i,**{k:r[k] for k in ('currentDistanceNm','dcpaNm','tcpaMin','isDegenerate','isDiverging')}})
    return out

@router.get('/cases/{case_id}/analysis/current')
def current(case_id:str,ownVesselId:str='',targetVesselId:str='',fromSec:float|None=None,toSec:float|None=None,ctx:Ctx=CtxDep):
    if not ownVesselId or not targetVesselId or ownVesselId==targetVesselId or max(len(ownVesselId),len(targetVesselId))>64:reject('ANALYSIS_VESSEL_SELECTION','请明确选择本案两艘不同船舶。')
    if any(v is not None and (not number(v) or abs(v)>1e12) for v in (fromSec,toSec)) or (fromSec is not None and toSec is not None and fromSec>toSec):reject('ANALYSIS_TIME_WINDOW','时间窗必须有限且起点不晚于终点。')
    snapshot,digest=read_snapshot(ctx,case_id,ownVesselId,targetVesselId,fromSec,toSec)
    pairs,inputs=pair_points(snapshot)
    env=_core(ctx,'cpa',{'origin':snapshot['origin'],'pairs':pairs}) if pairs else None
    rows=checked_results(env,pairs,inputs) if pairs else []
    try:
        _,after=read_snapshot(ctx,case_id,ownVesselId,targetVesselId,fromSec,toSec)
    except HTTPException as exc:
        if exc.status_code in (404,422):reject('ANALYSIS_INPUT_CHANGED','计算期间已存输入变更或已不可用于计算，请重新读取。',409)
        raise
    if after!=digest:reject('ANALYSIS_INPUT_CHANGED','计算期间已存输入发生变化，请重新计算。',409)
    own,target=snapshot.pop('tracks')
    return {'profile':PROFILE,**snapshot,'inputDigest':digest,'coreVersion':env['coreVersion'] if env else None,
            'counts':{'own':len(own),'target':len(target),'matched':len(rows),'unmatchedOwn':len(own)-len(rows),'unmatchedTarget':len(target)-len(rows)},'rows':rows}
