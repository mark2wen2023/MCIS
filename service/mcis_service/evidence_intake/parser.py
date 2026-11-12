"""Bounded opaque-file intake validation. Never invent extraction time."""
import base64
import binascii
import hashlib
import json
import re
from datetime import datetime
from ..common.context import problem

PROFILE = 'mcis-evidence-intake-v1'
VERSION = '1'
PREFIX = 'MCIS-EVIDENCE-INTAKE/1 '
MAX_BYTES = 8 * 1024 * 1024
MAX_BODY = 12 * 1024 * 1024
SAFE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
DIGEST = re.compile(r'^[0-9a-f]{64}$')
UTC = re.compile(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$')
META = {'title', 'source', 'extractedBy', 'extractedUtc', 'category', 'confidentiality', 'note'}
FIELDS = META | {'profile', 'fileName', 'contentBase64'}
CATEGORIES = {'VDR','AIS','ECDIS','EngineLog','Testimony','Photo','Document','Other'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text(value, limit, *, empty=False, multiline=True):
    if not isinstance(value,str) or len(value)>limit or (not empty and not value.strip()):
        raise ValueError('text')
    if any(ord(c)<32 and not (multiline and c in '\n\t') or ord(c)==127 for c in value):
        raise ValueError('control')
    value.encode('utf-8',errors='strict')
    return value


def metadata(body):
    try:
        if body['profile'] != PROFILE: raise ValueError('profile')
        name=text(body['fileName'],128,multiline=False)
        if name in ('.','..') or any(c in name for c in '/\\:'): raise ValueError('filename')
        text(body['title'],1000);text(body['source'],1000);text(body['extractedBy'],200)
        text(body['note'],2000,empty=True)
        stamp=body['extractedUtc']
        if not isinstance(stamp,str) or not UTC.fullmatch(stamp): raise ValueError('UTC')
        if datetime.fromisoformat(stamp.replace('Z','+00:00')).year < 1000: raise ValueError('supported UTC year 1000-9999')
        if not isinstance(body['category'],str) or body['category'] not in CATEGORIES: raise ValueError('category')
        if body['confidentiality']!='Restricted': raise ValueError('restricted')
    except (ValueError,TypeError,KeyError,UnicodeError):
        raise problem(422,'INTAKE_METADATA','须提供合法文件名、原文声明、类别、Restricted及已知UTC整秒提取时间（年份1000–9999）；不得以登记时间代填')
    return {k:body[k] for k in sorted(META)}


def inputs(body, *, commit=False):
    allowed=FIELDS | ({'requestDigest','confirmed'} if commit else set())
    if not isinstance(body,dict) or set(body)!=allowed:
        raise problem(422,'INTAKE_FIELDS','请求字段必须与数字文件副本登记合同一致')
    meta=metadata(body)
    if commit and (body['confirmed'] is not True or not isinstance(body['requestDigest'],str) or not DIGEST.fullmatch(body['requestDigest'])):
        raise problem(422,'INTAKE_CONFIRM','必须明确确认并提供本次预览摘要')
    encoded=body['contentBase64']
    if not isinstance(encoded,str): raise problem(422,'INTAKE_BASE64','原件必须是严格base64字符串')
    if len(encoded)>4*((MAX_BYTES+2)//3): raise problem(413,'INTAKE_FILE_LIMIT','本切片原件工程上限为8MiB')
    try:
        raw=base64.b64decode(encoded,validate=True)
        if base64.b64encode(raw).decode('ascii')!=encoded: raise ValueError('noncanonical base64')
    except (ValueError,binascii.Error,UnicodeError):
        raise problem(422,'INTAKE_BASE64','原件必须是严格规范base64')
    if len(raw)>MAX_BYTES: raise problem(413,'INTAKE_FILE_LIMIT','本切片原件工程上限为8MiB')
    return meta,raw


def preview(body,raw,case_id,operator,role):
    meta=metadata(body)
    try: text(operator,200,multiline=False)
    except (ValueError,UnicodeError): raise problem(422,'INTAKE_OPERATOR','登记操作人须为有效有限长度文本')
    binding={'profile':PROFILE,'version':VERSION,'caseId':case_id,'operator':operator,'role':role,
             'fileName':body['fileName'],'byteLength':len(raw),'sourceSha256':sha(raw),'metadata':meta}
    return {'profile':PROFILE,'caseId':case_id,'requestDigest':sha(canonical(binding)),
            'sourceSha256':sha(raw),'fileName':body['fileName'],'byteLength':len(raw),'metadata':meta,
            'warnings':['只保全本次选入的文件副本；人工来源、提取人和时间未经真实性认证。',
                        '登记时间与提取时间分开；不解析内容、不校正设备钟差。',
                        '8MiB仅本切片工程上限；Restricted为受限存储选择，不是法律分类认定。']},binding
