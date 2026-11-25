"""Bounded MCIS-UTC CSV v1 validation. Never infer AIS codes from a numeric value."""
from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import io
import json
import math
import re
from datetime import datetime

from ..common.context import problem

PROFILE = 'mcis-utc-v1'
MAX_BYTES = 1024 * 1024
MAX_ROWS = 10000
MAX_BODY = 1536 * 1024
MAX_ISSUES = 200
REQUIRED = ['utc', 'latDeg', 'lonDeg', 'sogKn', 'sogStatus', 'cogDeg', 'cogStatus']
OPTIONAL = ['hdgDeg', 'hdgStatus']
UTC = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$')
NUMBER = re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$')
SAFE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
FIELDS = {'profile', 'vesselId', 'fileName', 'source', 'timeBasis', 'contentBase64'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc(value):
    if not isinstance(value, str) or not UTC.fullmatch(value):
        raise ValueError('UTC must include full date and Z, at most milliseconds')
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def inputs(body, *, commit=False):
    allowed = FIELDS | ({'previewDigest', 'confirmed'} if commit else set())
    if not isinstance(body, dict) or set(body) != allowed:
        raise problem(422, 'INPUT_FIELDS', '请求字段必须与 MCIS-UTC CSV v1 合同一致')
    if body['profile'] != PROFILE:
        raise problem(422, 'PROFILE', '仅支持 mcis-utc-v1，不支持原始 AIS/NMEA 或任意 CSV')
    for key, limit in [('vesselId',128), ('fileName',128), ('source',1000), ('timeBasis',1000)]:
        value = body[key]
        if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c)<32 and not (c=='\n' and key in ('source','timeBasis')) for c in value):
            raise problem(422, 'INPUT_METADATA', '船舶、文件名、来源和时间依据须为非空、有限长度文本；仅来源和时间依据允许换行')
        try: value.encode('utf-8', errors='strict')
        except UnicodeError: raise problem(422, 'INPUT_METADATA', '文本包含无效 Unicode 字符')
    if not SAFE_ID.fullmatch(body['vesselId']):
        raise problem(422, 'VESSEL_ID', '船舶编号不适用于此输入切片')
    if '/' in body['fileName'] or '\\' in body['fileName'] or not body['fileName'].lower().endswith('.csv'):
        raise problem(422, 'FILE_NAME', '只接受不含路径的 .csv 文件名')
    encoded = body['contentBase64']
    if not isinstance(encoded, str) or len(encoded)>4*((MAX_BYTES+2)//3):
        raise problem(413, 'FILE_LIMIT', '原件不得超过 1 MiB')
    try:
        encoded.encode('ascii', errors='strict')
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error, UnicodeError):
        raise problem(422, 'BASE64', '原件 Base64 编码无效')
    if not raw or len(raw)>MAX_BYTES:
        raise problem(413, 'FILE_LIMIT', '原件须为 1 字节至 1 MiB')
    if commit and (body['confirmed'] is not True or not isinstance(body['previewDigest'], str) or not re.fullmatch('[0-9a-f]{64}',body['previewDigest'])):
        raise problem(422, 'CONFIRMATION', '保存须明确确认并提供预览摘要')
    return raw


def preview(body, raw, case, *, operator, role, existing_count):
    meta = {k: body[k] for k in FIELDS if k!='contentBase64'}
    digest = sha(canonical({'metadata':meta,'sourceSha256':sha(raw),'caseId':case['caseId'],
                            'caseEpochUtc':case['caseEpochUtc'],'operator':operator,'role':role,'parserVersion':1}))
    issues = []
    total_issues = 0
    points = []
    count = 0
    previous = None
    def issue(row, field, code, message):
        nonlocal total_issues
        total_issues += 1
        if len(issues)<MAX_ISSUES:
            issues.append({'row':row,'field':field,'code':code,'message':message})
    try:
        epoch = utc(case['caseEpochUtc'])
    except ValueError:
        raise problem(422, 'CASE_EPOCH', '案件纪元不符合本切片完整 UTC Z 格式')
    try:
        text = raw.decode('utf-8-sig', errors='strict')
        if '\x00' in text:
            raise ValueError('NUL')
    except (UnicodeError, ValueError):
        raise problem(422, 'CSV_ENCODING', '原件必须为 UTF-8，可带 BOM，不可含 NUL')
    # Keep the process-wide csv field limit unchanged. This profile has a stricter local bound.
    try:
        reader = csv.reader(io.StringIO(text, newline=''), strict=True)
        headers = next(reader, [])
        if len(headers)!=len(set(headers)) or set(headers) not in (set(REQUIRED),set(REQUIRED+OPTIONAL)):
            raise problem(422, 'CSV_HEADER', '列名必须唯一且恰为规定的 7 列，或加 hdgDeg、hdgStatus 共 9 列')
        for cells in reader:
            count += 1
            if count>MAX_ROWS:
                raise problem(413, 'ROW_LIMIT', '单次最多 10000 条记录；没有保存部分结果')
            before = total_issues
            if len(cells)!=len(headers) or any(len(c)>1024 or '\n' in c or '\r' in c for c in cells):
                issue(count,'row','ROW_SHAPE','列数不符或字段过长/跨行'); continue
            row = dict(zip(headers,cells))
            def num(field):
                value = row[field]
                if not NUMBER.fullmatch(value):
                    issue(count,field,'NUMBER','需要有限十进制数，单位按合同'); return None
                n = float(value)
                if not math.isfinite(n):
                    issue(count,field,'NUMBER','数值必须有限'); return None
                return n
            t = None
            try:
                t = utc(row['utc'])
                if previous is not None and t<=previous:
                    issue(count,'utc','TIME_ORDER','时间须严格递增，不排序、不删除重复点')
                previous=t
            except ValueError:
                issue(count,'utc','UTC','需要含日期的 UTC Z 时间，最多毫秒；不推断时区或日期')
            lat, lon = num('latDeg'),num('lonDeg')
            if lat is not None and not -90<=lat<=90: issue(count,'latDeg','RANGE','纬度须在 [-90,90]；不推断 AIS 原码')
            if lon is not None and not -180<=lon<=180: issue(count,'lonDeg','RANGE','经度须在 [-180,180]；不推断 AIS 原码')
            values = {}
            for field,status_field,limit in [('sogKn','sogStatus',None),('cogDeg','cogStatus',360),('hdgDeg','hdgStatus',360)]:
                if field not in row:
                    values[field]=None; continue
                status=row[status_field]
                choices={'reported','unavailable','unknown'} | ({'lowerBound'} if field=='sogKn' else set())
                if status not in choices:
                    issue(count,status_field,'STATUS','状态必须为该字段支持的显式语义'); values[field]=None; continue
                if field=='hdgDeg' and status=='unavailable':
                    # Preserve arbitrary unavailable raw field in source, never guess/replace heading.
                    values[field]=None; continue
                if status!='reported':
                    issue(count,status_field,'NOT_EXACT_VALUE','此字段不可用、语义未知或为下限，不能作为普通数值航迹点保存')
                    values[field]=None; continue
                n=num(field);values[field]=n
                if n is not None and (n<0 or (limit is not None and n>=limit)):
                    issue(count,field,'RANGE','数值超出本字段物理范围；不自动归一化或修补')
            if total_issues==before:
                sim=(t-epoch).total_seconds()
                if abs(sim)>1e12:
                    issue(count,'utc','TIME_RANGE','相对时间超过界面支持范围');continue
                points.append({'vesselId':body['vesselId'],'timeSec':sim,'utc':row['utc'],
                               'latDeg':lat,'lonDeg':lon,'sogKn':values['sogKn'],'cogDeg':values['cogDeg'],
                               'hdgDeg':values.get('hdgDeg')})
    except csv.Error:
        raise problem(422,'CSV_SYNTAX','CSV 引号、字段长度或记录结构无效；未保存部分结果')
    if not count: issue(0,'row','EMPTY','CSV 没有数据行')
    if existing_count: issue(0,'vesselId','TRACK_EXISTS','该船已有航迹，本切片不覆盖、不追加')
    result={'profile':PROFILE,'caseId':case['caseId'],'vesselId':body['vesselId'],
            'caseEpochUtc':case['caseEpochUtc'],'previewDigest':digest,'sourceSha256':sha(raw),
            'fileName':body['fileName'],'source':body['source'],'timeBasis':body['timeBasis'],
            'timeRange':({'firstUtc':points[0]['utc'],'lastUtc':points[-1]['utc'],'fromSec':points[0]['timeSec'],'toSec':points[-1]['timeSec']} if points else None),
            'rowCount':count,'canCommit':total_issues==0,'issues':issues,'issuesTruncated':total_issues>MAX_ISSUES,
            'issuesTotal':total_issues,'samplePoints':points[:100],'existingTrackCount':existing_count,
            'warnings':['来源和时间依据为提供者声明，不等于原始 AIS 认证或时间精度证明。',
                        '不清洗、不插值、不作缺口或事故责任判定；仅保存显式 reported 数值。']}
    return result, points
