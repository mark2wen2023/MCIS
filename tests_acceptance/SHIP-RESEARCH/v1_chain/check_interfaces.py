"""Probe the native interfaces using previously extracted synthetic drawing entities."""
import argparse
import json
from pathlib import Path
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('tree',type=Path)
    p.add_argument('samples',type=Path)
    p.add_argument('result',type=Path)
    args=p.parse_args()
    sys.path.insert(0,str(args.tree.resolve()/'service'))
    from mcis_service.agents.skills.ship_reconstruction.drawing_pipeline import extract_from_drawing
    from mcis_service.agents.skills.ship_reconstruction.sparse_section import sample_sparse_section
    rows=[]
    for case in ('full','sparse','empty_row','duplicate'):
        data=args.samples/case
        parsed=json.loads((data/'01-parsed.json').read_text())
        m=json.loads((data/'02-mapping.json').read_text())
        observed=extract_from_drawing(parsed,region=m['region'],mapping=m['mapping'])
        r=dict(case=case,native_complete=observed['candidate_complete'],rows=len(observed['rows']),
               missing=observed['diagnostics']['missing_rows'],issues=observed['issues'])
        if case=='full':
            try:
                sample_sparse_section(observed['rows'],[0,.5,1.0])
            except KeyError as exc:
                r['direct_rows_to_section']={'exception':type(exc).__name__,'field':exc.args[0]}
            else:
                raise AssertionError('direct contract changed: inspect new interface')
        rows.append(r)
    args.result.write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')


if __name__=='__main__':main()
