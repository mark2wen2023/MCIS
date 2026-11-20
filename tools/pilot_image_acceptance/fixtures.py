"""Deterministic fabricated bytes only; no I/O, application, recognizer or clock."""
import base64
import hashlib
import json
import struct
import zlib

CASE_IDS = ('SYN-PILOT-A', 'SYN-PILOT-B')
STAMP = '2026-01-01T00:00:00Z'  # Declared synthetic scenario time, not execution time.


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def cases():
    return [{'caseId':cid,'schemaVersion':'1.0.0','title':'纯合成图片试用 '+cid,
             'accidentType':'SyntheticExercise','incidentTimeUtc':STAMP,'caseEpochUtc':STAMP,
             'displayTimeZoneOffsetMinutes':0,'incidentLocation':{'lonDeg':0.0,'latDeg':0.0},
             'isFictionalDemo':True,'summaryNotes':'手造占位坐标与时刻；不是实际事故或证据。'} for cid in CASE_IDS]


def materials():
    # One-page PDF containing a rectangle only, not a real report.
    stream=b'0 0 1 rg 0 0 8 8 re f\n'
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',
             b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
             b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 8 8] /Contents 4 0 R >>',
             b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'endstream']
    pdf=b'%PDF-1.4\n'; offsets=[]
    for i,obj in enumerate(objects,1):
        offsets.append(len(pdf));pdf+=str(i).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
    xref=len(pdf);pdf+=b'xref\n0 5\n0000000000 65535 f \n'
    pdf+=b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets)
    pdf+=b'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF\n'
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    pixels=(b'\x00'+b'\x00\x00\xff'*8)*8
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',8,8,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b'')
    raw=encoded({'synthetic':True,'recognizerExecuted':False,'text':'SYNTHETIC LINE','note':'Hand-authored; not OCR output from an engine.'})
    candidate={'schema':'mcis.offline-ocr-candidate/v0.1','production_import_supported':False,
        'status':'pending_human_review','needs_review':True,'confirmed':False,
        'source':{'pdf_sha256':sha(pdf),'image_sha256':sha(png),'raw_sha256':sha(raw),
                  'pdf_page_1based':1,'width':8,'height':8,'printed_page':'',
                  'mapping_basis':'Hand-authored synthetic pairing; no rendering or OCR lineage verified.'},
        'recognizer':{**{key:'synthetic-not-executed' for key in ('paddlepaddle','paddleocr','paddlex','pipeline','device')},'models':['none-executed-synthetic']},
        'raw_page_index':None,'page_index_inferred':False,'coordinate_space':'rendered_page_pixels_xy_top_left',
        'limitations':['All bytes and text fabricated. Rectangle contains no text; transcription is a test declaration.'],
        'text_lines':[{'line_index':0,'text':'SYNTHETIC LINE','is_blank':False,'model_score':0.0,
                       'bbox':[0,0,8,8],'polygon':[[0,0],[8,0],[8,8],[0,8]],'needs_review':True,'confirmed':False}],
        'tables':[]}
    return {'pdf':('synthetic.pdf',pdf),'image':('synthetic.png',png),
            'raw':('synthetic-raw.json',raw),'candidate':('synthetic-candidate.json',encoded(candidate))}


def intake_bodies():
    return {kind:{'profile':'mcis-evidence-intake-v1','fileName':name,
                  'contentBase64':base64.b64encode(raw).decode('ascii'),
                  'title':'纯手造试用 '+kind,'source':'Independent fabricated bytes, no source case or model.',
                  'extractedBy':'Synthetic fixture author (declaration, not authenticated identity)',
                  'extractedUtc':STAMP,'category':'Photo' if kind=='image' else 'Document',
                  'confidentiality':'Restricted','note':'Synthetic-only declaration; timestamps and text are fabricated.'}
            for kind,(name,raw) in materials().items()}
