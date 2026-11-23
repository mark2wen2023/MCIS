"""Synthetic process-local host seam, NOT authentication or a product interface.
Only proposal references are untrusted. Host manifests/review selections are test
inputs; a real authorized repository and review store do not exist here.
"""
from copy import deepcopy
import hashlib
import json

class Rejected(ValueError): pass

def need(ok,code):
    if not ok: raise Rejected(code)

def exact(obj,keys):
    need(type(obj) is dict and set(obj)==set(keys.split()),'SHAPE')

class TrialHost:
    def __init__(self, *, case, originals, pins, reviews, selected, timeline, scoped):
        self.case=case
        self.originals=deepcopy(originals);self.pins=deepcopy(pins)
        self.reviews=deepcopy(reviews);self.selected=deepcopy(selected)
        self.t=timeline;self.s=scoped

    def source(self, ref):
        exact(ref,'sourceId revision locator')
        sid=ref['sourceId'];need(sid in self.pins and sid in self.originals,'SOURCE_UNAVAILABLE')
        pin=self.pins[sid];raw=self.originals[sid]
        need(type(raw) is bytes and hashlib.sha256(raw).hexdigest()==pin['sha256'],'ORIGINAL_BYTES')
        need(pin['case']==self.case and pin['revision']==ref['revision'],'SOURCE_VERSION_CASE')
        doc=json.loads(raw)
        need(doc['case']==self.case and doc['sourceId']==sid and doc['revision']==pin['revision'],'DOCUMENT_IDENTITY')
        # Narrow record-key locator only; no arbitrary file/URL reader.
        loc=ref['locator'];need(type(loc) is str and loc.startswith('/rows/') and loc.count('/')==2,'LOCATOR')
        key=loc[6:];need(key in doc['rows'],'LOCATOR')
        return self.t.Source(self.case,sid,pin['sha256'],loc),doc,doc['rows'][key]

    def event(self, ref, event_id):
        src,doc,row=self.source(ref)
        # Loss/unknown timestamps stay outside numeric comparator, not fake relative events.
        if row['start'] is None or row['end'] is None:
            need(row['start'] is None and row['end'] is None,'PARTIAL_TIME')
            return None,None,{'reason':'NO_NUMERIC_TIME','source':src.__dict__}
        e=self.t.Event(event_id,src,doc['clock'],row['text'],
                       'point' if row['start']==row['end'] else 'range',row['start'],row['end'])
        self.t.validate_events([e])
        key=(src.id,src.locator)
        if key not in self.selected:return e,None,{'reason':'NO_REVIEW','source':src.__dict__}
        chosen=self.selected[key]
        need(type(chosen) is str and chosen in self.reviews,'CALIBRATION_SELECTION')
        c=self.reviews[chosen]
        exact(c,'id version case source clock scope offset uncertainty targetBasis basis status reviewer sourceSha256 basisSha256')
        need(c['id']==chosen and type(c['version']) is str and bool(c['version']),'CALIBRATION_VERSION')
        need(c['case']==self.case and c['source']==ref and c['clock']==doc['clock'],'CALIBRATION_BINDING')
        exact(c['scope'],'start end')
        need(c['sourceSha256']==src.revision,'CALIBRATION_SOURCE_BYTES')
        basis,bd,br=self.source(c['basis'])
        need(c['basisSha256']==basis.revision,'CALIBRATION_BASIS_BYTES')
        need(br['clock']==doc['clock'] and br['targetBasis']==c['targetBasis'],'BASIS_BINDING')
        need(br['offset']==c['offset'] and br['uncertainty']==c['uncertainty'],'BASIS_VALUES')
        # A preserved aligned row must never receive an independent device correction.
        need(doc['timeState'] in ('raw','already_aligned'),'TIME_STATE')
        if doc['timeState']=='already_aligned':
            need(self.t.number(c['offset'])==0 and doc['targetBasis']==c['targetBasis'],'DOUBLE_CORRECTION')
        need(c['status'] in ('unreviewed','disputed','reviewed'),'REVIEW_STATUS')
        need(c['status']!='reviewed' or c['reviewer']=='synthetic-reviewer','REVIEW_RECORD')
        correction=self.t.Correction(self.case,doc['clock'],c['id']+'@'+c['version'],c['offset'],c['uncertainty'],(basis,),
                                      'confirmed' if c['status']=='reviewed' else 'proposed')
        selection=self.s.ScopedCorrection(correction,self.s.Scope(src,c['scope']['start'],c['scope']['end']),c['targetBasis'])
        # Always invoke original containment/basis checks, even for pending reviews.
        view=self.s.scoped_interval(e,selection)
        return e,selection,{'reason':None if c['status']=='reviewed' else c['status'].upper(),
             'source':src.__dict__,'calibration':correction.revision,'basis':basis.__dict__,
             'originalSeconds':[e.start,e.end],'displayInterval':[str(view[0]),str(view[1])],
             'aligned':view[2]}

    def compare(self, proposal):
        exact(proposal,'case left right') # No status/clock/offset/authority model fields.
        need(proposal['case']==self.case,'CASE')
        a,ca,ra=self.event(proposal['left'],'left')
        b,cb,rb=self.event(proposal['right'],'right')
        if a is None or b is None:relation='undetermined'
        else:
            self.t.validate_events([a,b]);relation=self.s.scoped_compare(a,b,ca,cb)
        return {'relation':relation,'sources':[ra,rb],'status':'pending_human_review',
                'authorityVerified':False,'modelCalled':False,'saved':False,
                'scope':'synthetic_test_host_only','identityDetermined':False,'causationDetermined':False}
