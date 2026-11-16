"""Read-only research consistency for supplied PDF/PNG and retained line-OCR JSON.
No rendering lineage, OCR execution, original authenticity or restore permission.
"""
import io
import os
import re
import shutil
import subprocess
from PIL import Image
from .contract import validate as validate_index, need, parse, digest
from .image_line_contract import parse as parse_lines


def png_size(raw):
    try:
        with Image.open(io.BytesIO(raw)) as image:
            need(image.format=='PNG' and getattr(image,'n_frames',1)==1, 'single PNG required')
            width,height=image.size
            need(0<width<=10000 and 0<height<=10000 and width*height<=20000000, 'image dimensions budget')
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            return image.size
    except (OSError,SyntaxError) as exc:
        raise ValueError('PNG decode failed') from exc


def pdf_pages(raw):
    need(raw.startswith(b'%PDF-'), 'PDF format')
    executable=shutil.which('pdfinfo')
    need(executable is not None, 'pdfinfo unavailable; not verified')
    # Standard installed utility, stdin only. No shell, paths from the package or network.
    try:
        result=subprocess.run([executable,'-'],input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              timeout=10,check=False,env={'PATH':os.defpath,'LC_ALL':'C'})
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise ValueError('PDF inspection unavailable') from exc
    need(result.returncode==0 and not result.stderr.strip(), 'PDF inspection incomplete')
    output=result.stdout.decode('utf-8',errors='strict')
    pages=re.findall(r'^Pages:\s+(\d+)\s*$',output,re.M)
    need(len(pages)==1 and 1<=int(pages[0])<=2000, 'PDF page count')
    encrypted=re.findall(r'^Encrypted:\s+(\S+)',output,re.M)
    need(encrypted==['no'], 'unsupported PDF inspection profile')
    return int(pages[0])


def check_image_members(index,payloads):
    validate_index(index,payloads)
    need(index['sources'] and all(s['kind'] in ('pdf','page-image') for s in index['sources']), 'image/PDF profile only')
    sources={s['id']:s for s in index['sources']}
    counts={sid:pdf_pages(payloads[src['originalMember']]) for sid,src in sources.items() if src['kind']=='pdf'}
    for src in sources.values():
        if src['kind']=='page-image':
            loc=src['location']
            need(png_size(payloads[src['originalMember']])==(loc['width'],loc['height']), 'declared image size')
            need(loc['pdfPage1Based']<=counts[loc['pdfSourceId']], 'declared PDF page outside document')
    for run in index['runs']:
        src=sources[run['sourceId']];loc=src['location']
        machine=parse_lines(payloads[run['machineMember']])
        source=machine['source']
        need(source['width']==loc['width'] and source['height']==loc['height'] and
             source['mapping_basis']=='manual_source_manifest' and source['printed_page']==loc['printedPage'], 'source declaration')
        need(machine['recognizer']==parse(payloads[run['recognizerMember']]), 'recognizer declaration')
        raw=parse(payloads[run['rawMember']])
        need(type(raw) is dict and not raw.get('table_res_list'), 'line OCR only')
        arrays=[raw.get(k) for k in ('rec_texts','rec_scores','rec_boxes','rec_polys')]
        need(all(type(a) is list for a in arrays) and len({len(a) for a in arrays})==1, 'OCR arrays')
        need('page_index' in raw and raw['page_index']==machine['raw_page_index'], 'raw page index declaration')
        expected=[dict(line_index=n,text=t,is_blank=t=='',model_score=score,bbox=box,polygon=poly,
                       needs_review=True,confirmed=False) for n,(t,score,box,poly) in enumerate(zip(*arrays))]
        need(machine['text_lines']==expected, 'candidate differs from retained OCR rows')
        initial=parse(payloads[run['initialMember']])
        need(initial.get('pageMappingVerified') is False and initial.get('originalAuthenticityVerified') is False, 'unverified source markers')
        for rev in run['revisions'][1:]:
            doc=parse(payloads[rev['member']])
            need(type(doc.get('text')) is str and len(doc['text'])<=20000 and
                 doc.get('decision') in ('pending','transcription-checked','unreadable'), 'human review declaration')
    return {'restore_ready':False,'export_allowed':False,'source_bytes_match':True,
            'declared_pdf_pages_in_bounds':True,'page_mapping_verified':False,
            'ocr_execution_verified':False,'authenticity_verified':False,'authorization_verified':False,
            'scope':'supplied-PDF-PNG-line-OCR-consistency-only','pdfPageCounts':counts}
