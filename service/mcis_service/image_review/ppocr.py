"""Explicit offline adapter for PP-OCR line results. Does not execute a model."""
import copy
import json
from .contract import parse
from ..evidence_intake.parser import sha


def convert(raw, source, recognizer):
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out: raise ValueError('duplicate field')
            out[k]=v
        return out
    if len(raw)>2*1024*1024: raise ValueError('raw budget')
    d=json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('number')))
    if source['raw_sha256']!=sha(raw): raise ValueError('raw version mismatch')
    arrays=[d[k] for k in ('rec_texts','rec_scores','rec_boxes','rec_polys')]
    if not all(isinstance(a,list) for a in arrays) or len({len(a) for a in arrays})!=1: raise ValueError('OCR arrays disagree')
    if len(arrays[0])>1000: raise ValueError('line budget')
    if d.get('table_res_list'): raise ValueError('table output unsupported')
    lines=[{'line_index':i,'text':t,'is_blank':t=='','model_score':score,'bbox':box,'polygon':poly,
            'needs_review':True,'confirmed':False} for i,(t,score,box,poly) in enumerate(zip(*arrays))]
    candidate={'schema':'mcis.offline-ocr-candidate/v0.1','production_import_supported':False,
               'status':'pending_human_review','needs_review':True,'confirmed':False,
               'source':copy.deepcopy(source),'recognizer':copy.deepcopy(recognizer),
               'raw_page_index':d['page_index'],'page_index_inferred':False,
               'coordinate_space':'rendered_page_pixels_xy_top_left',
               'limitations':['Imported local model output; not an established fact.',
                              'PDF page/render mapping is supplied, not automatically verified.'],
               'text_lines':lines,'tables':[]}
    encoded=json.dumps(candidate,ensure_ascii=False,allow_nan=False).encode('utf-8')
    return parse(encoded)


def main():
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();manifest=json.loads(args.manifest.read_text())
    candidate=convert(args.raw.read_bytes(),manifest['source'],manifest['recognizer'])
    encoded=json.dumps(candidate,ensure_ascii=False,indent=2,allow_nan=False)
    with args.output.open('x',encoding='utf-8') as f:f.write(encoded)


if __name__=='__main__':main()
