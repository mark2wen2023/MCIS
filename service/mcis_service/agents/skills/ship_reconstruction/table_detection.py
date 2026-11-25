"""Find candidate offset-table titles, not verified table boundaries."""
import math
import re
import unicodedata

def detect_titles(entities):
    candidates=[]
    for e in entities:
        if e.get('type') not in ('TEXT','MTEXT'):
            continue
        text=e.get('text')
        if not isinstance(text,str):
            continue
        normalized=re.sub(r'\s+','',unicodedata.normalize('NFKC',text)).casefold()
        if not any(k in normalized for k in ('型值表','型线坐标表','tableofoffsets','offsettable')):
            continue
        p=e.get('anchor_wcs')
        if not isinstance(p,(list,tuple)) or len(p)!=3 or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in p):
            continue
        if not e.get('layout') or not e.get('handle'):
            continue
        candidates.append({'layout':e['layout'],'handle':e['handle'],'title':text,'anchor_wcs':list(p),'review':'pending','bounds':None})
    return candidates
