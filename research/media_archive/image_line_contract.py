# Research snapshot adapted from image candidate 91962113bd98778d3538f0e8e9879a014023c21f; only imports isolated.
"""Validate the bounded line-OCR handoff; no OCR execution or inferred page mapping."""
import json
import math
import re
DIGEST = re.compile(r'[a-f0-9]{64}')


def text(value, limit, *, empty=False, multiline=True):
    if not isinstance(value,str) or len(value)>limit or (not empty and not value.strip()):
        raise ValueError('text')
    if any(ord(c)<32 and not (multiline and c in '\n\t') or ord(c)==127 for c in value):
        raise ValueError('control')
    value.encode('utf-8',errors='strict')
    return value


def parse(raw):
    def unique(pairs):
        d = {}
        for k, v in pairs:
            if k in d: raise ValueError('duplicate field')
            d[k] = v
        return d
    if len(raw) > 2 * 1024 * 1024: raise ValueError('result budget')
    d = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                   parse_constant=lambda _: (_ for _ in ()).throw(ValueError('number')))
    if set(d) != {'schema', 'production_import_supported', 'status', 'needs_review', 'confirmed', 'source', 'recognizer', 'raw_page_index', 'page_index_inferred', 'coordinate_space', 'limitations', 'text_lines', 'tables'}: raise ValueError('fields')
    if d['production_import_supported'] is not False or d['page_index_inferred'] is not False: raise ValueError('offline candidate only')
    if not isinstance(d['limitations'], list) or len(d['limitations']) > 30: raise ValueError('limitations')
    for limitation in d['limitations']: text(limitation, 2000)
    if d['schema'] != 'mcis.offline-ocr-candidate/v0.1': raise ValueError('format')
    if d['confirmed'] is not False or d['needs_review'] is not True or d['status'] != 'pending_human_review':
        raise ValueError('candidate only')
    if d['tables']: raise ValueError('table review not supported in this slice')
    src = d['source']
    for k in ('pdf_sha256', 'image_sha256', 'raw_sha256'):
        if not isinstance(src[k], str) or not DIGEST.fullmatch(src[k]): raise ValueError('digest')
    for k in ('pdf_page_1based', 'width', 'height'):
        if type(src[k]) is not int or not 1 <= src[k] <= 100000: raise ValueError('page/dimensions')
    text(src['mapping_basis'], 200); text(src['printed_page'], 100, empty=True)
    if d['coordinate_space'] != 'rendered_page_pixels_xy_top_left': raise ValueError('coordinates')
    # Null is preserved: a manually declared PDF page is not a recognizer page index.
    if d['raw_page_index'] is not None and (type(d['raw_page_index']) is not int or d['raw_page_index'] < 0):
        raise ValueError('model page')
    rec = d['recognizer']
    for k in ('paddlepaddle', 'paddleocr', 'paddlex', 'pipeline', 'device'): text(rec[k], 200)
    if not isinstance(rec['models'], list) or not 1 <= len(rec['models']) <= 20: raise ValueError('models')
    for model in rec['models']: text(model, 200)
    lines = d['text_lines']
    if not isinstance(lines, list) or not 1 <= len(lines) <= 1000: raise ValueError('lines')
    def number(n): return type(n) in (int, float) and math.isfinite(n)
    for i, line in enumerate(lines):
        if type(line['line_index']) is not int or line['line_index'] != i: raise ValueError('line identity')
        if set(line) != {'line_index', 'text', 'is_blank', 'model_score', 'bbox', 'polygon', 'needs_review', 'confirmed'}: raise ValueError('line fields')
        text(line['text'], 20000, empty=True)
        if type(line['is_blank']) is not bool or line['is_blank'] != (line['text'] == ''): raise ValueError('blank flag')
        if line['confirmed'] is not False or line['needs_review'] is not True: raise ValueError('line review')
        if not number(line['model_score']) or not 0 <= line['model_score'] <= 1: raise ValueError('score')
        b = line['bbox']
        if not isinstance(b, list) or len(b) != 4 or not all(number(n) for n in b): raise ValueError('box')
        if not (0 <= b[0] <= b[2] <= src['width'] and 0 <= b[1] <= b[3] <= src['height']): raise ValueError('box bounds')
        p = line['polygon']
        if not isinstance(p, list) or not 3 <= len(p) <= 16: raise ValueError('polygon')
        for xy in p:
            if not isinstance(xy, list) or len(xy) != 2 or not all(number(n) for n in xy): raise ValueError('point')
            if not (0 <= xy[0] <= src['width'] and 0 <= xy[1] <= src['height']): raise ValueError('point bounds')
    return d
