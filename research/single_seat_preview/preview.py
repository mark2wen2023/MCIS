"""Read-only T124.250 synthetic presentation; not an AgentDraft or authorization."""
import hashlib,importlib.util,json
from pathlib import Path

def modules(source):
    pins=json.loads((Path(__file__).parent/'pins.json').read_text());loaded={}
    for p in pins:
        raw=(source/p['name']).read_bytes()
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=p['blob']:raise ValueError('fixed source mismatch')
        spec=importlib.util.spec_from_file_location(p['name'][:-3],source/p['name']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);loaded[p['name']]=m
    return loaded['seat_note.py'],loaded['packet.py']

def preview(args,*,frame,trusted_pins,source):
    seat,host=modules(source)
    # Import boundary calls the actual fixed seat, not a new label interpreter.
    try:note=seat.handoff(host._validate,args,frame=frame,trusted_pins=trusted_pins)
    except (seat.ScopeError,host.GroupError) as error:raise ValueError(str(error)) from None
    rows=[]
    for review,spec in zip(note['items'],seat.SPECS,strict=True):
        vid,eid,item,state,pointer,_=spec;reference=note['references'][item]
        rows.append({'itemId':item,'vesselId':vid,'evidenceState':state,'sufficiency':review['label'],
                     'statement':review['quote'],'limitation':review['uncertainty'],
                     'reference':None if reference is None else {'evidenceId':reference['original']['evidenceId'],'jsonPointer':reference['locator']['jsonPointer'],
                     'meaning':'host_bound_synthetic_gap_locator_not_observation_or_authority'}})
    return {'type':'synthetic_single_seat_readonly_preview/v1','caseId':note['caseId'],'alignedUtc':note['alignedUtc'],
            'humanAction':{'status':'pending','confirmed':False,'saved':False},'finding':note['text'],
            'rows':rows,'factActivated':False,'actions':[],'scope':'T124.250_only_no_queue_no_authentication'}

def render(value):
    # Output is plain text, not HTML or an interactive sign-off surface.
    lines=[value['type'],value['caseId']+' / '+value['alignedUtc'],'Human review: pending; not confirmed; not saved.',value['finding']]
    for r in value['rows']:
        ref='none (no exact observation)' if r['reference'] is None else r['reference']['evidenceId']+' '+r['reference']['jsonPointer']+' (gap only)'
        lines.extend([r['vesselId']+': '+r['evidenceState']+' / '+r['sufficiency'],r['statement'],'Reference: '+ref,r['limitation']])
    return '\n'.join(lines)+'\n'
