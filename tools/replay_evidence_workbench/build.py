"""Build a single offline workbench from the unchanged fixed synthetic clock query."""
import argparse
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import runpy
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
QUERY_SHA="1719c89677866eec4e2c1e5a8f1b24fd288072d3ab33c3053687a5c12a23f661"

def build(output):
    query=ROOT/'tools/replay_evidence_clock/query.py'
    if hashlib.sha256(query.read_bytes()).hexdigest()!=QUERY_SHA:
        raise ValueError('fixed query source mismatch')
    q=runpy.run_path(str(query));tracks,device=q['load_inputs']()
    times={0,1,20,60,60.001,80,99.999,100,121,121.001,124.25,127.499,127.5,220}
    history=[];positions=[]
    sec=lambda s:(q['stamp'](s)-q['ORIGIN']).total_seconds()
    for track in tracks:
        d=track['document'];points=[]
        for p in d['points']:
            t=sec(p['time']['alignedUtc']);times.add(t)
            points.append({'seconds':t,'position':p['position']})
            if p['position']['value']:positions.append(p['position']['value'])
        history.append({'vesselId':d['vessel']['vesselId'],'points':points,'threshold':d['sampling']['gapThresholdSeconds'],
                        'gaps':[[sec(g['startUtc']),sec(g['endUtc'])] for g in d['sampling']['missingIntervals']]})
    payload={'frames':[q['query'](tracks,device,s) for s in sorted(times)],'history':history,
             'bounds':{k:[min(p[k] for p in positions),max(p[k] for p in positions)] for k in ['latDeg','lonDeg']}}
    text=(HERE/'workbench.html').read_text()
    values={'/* STYLE */':(HERE/'style.css').read_text(),'/* SCRIPT */':(HERE/'workbench.js').read_text(),
            'PAYLOAD':json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')}
    for marker,value in values.items():
        if text.count(marker)!=1:raise ValueError('template marker mismatch')
        text=text.replace(marker,value)
    with output.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    return text

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build(args.output)
    print('Generated synthetic offline workbench; browser/3D unverified')
