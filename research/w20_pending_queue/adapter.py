"""Offline internal candidate: owns a disposable SQLite DB, never a product endpoint."""
import copy
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

from sqlalchemy import select, text
from mcis_service.db import Database, Base, get_doc, put_doc, list_docs
from mcis_service.agents.models import AgentDraftRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.audit import service as audit
from research.expert_budget.four_chair import FourChair, ROLES
from research.expert_group.packet import _digest, _validate

SYNTHETIC_UTC = '2026-02-01T12:02:04Z'
MANIFEST_SHA = 'e91d31f34678ee2af880fb9931813677b93706332a03e96a0846943ef50235dd'
LOCATOR_BLOB = '44fc5d82279db5fa3a3c748161f3122708e85668'

def require(ok, code):
    if not ok:
        raise ValueError(code)

def sha(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

class FrozenSyntheticContext:
    """Construct only from the previously published fixed synthetic package."""
    def __init__(self, package, locator_path):
        package, locator_path = Path(package), Path(locator_path)
        self.package, self.locator_path = package, locator_path
        raw = locator_path.read_bytes()
        require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==LOCATOR_BLOB, 'locator_blob')
        spec=importlib.util.spec_from_file_location('fixed_pending_locator',locator_path)
        locator=importlib.util.module_from_spec(spec);spec.loader.exec_module(locator)
        manifest=(package/'FROZEN.sha256').read_bytes()
        require(hashlib.sha256(manifest).hexdigest()==MANIFEST_SHA,'manifest')
        for row in manifest.decode().splitlines():
            digest,name=row.split('  ')
            require(hashlib.sha256((package/name).read_bytes()).hexdigest()==digest,'source_bytes')
        data=json.loads((package/'sample.json').read_text())
        registry={}
        for source in data['sources']:
            card=source['card'];locator.ROOT=package/source['directory']
            require(locator.locate(card)=='LOCATED','source_not_located')
            statement=json.loads(card['content']['source']['excerpt'])
            require(statement['caseId']==data['caseId'],'source_case')
            b=card['sourceBinding']
            registry[b['recordId']]={'sha256':b['sha256'],'line':b['line'],
                'locator':source['directory']+'/'+card['content']['source']['locator'],
                'excerpt':card['content']['source']['excerpt']}
        self.draft={'caseId':data['caseId'],'version':'synthetic-draft-v1',
                    'event':data['eventClaim'],'candidateLink':data['linkClaim']}
        self.registry=registry
        self.binding={'caseId':data['caseId'],'version':self.draft['version'],
                      'draftDigest':_digest(self.draft),'sourceSetDigest':_digest(registry)}

class TemporaryPendingQueue:
    """Single-writer research adapter. No caller DB URL, review or HTTP operation."""
    def __init__(self, context, chair, *, temp_root):
        require(type(context) is FrozenSyntheticContext and isinstance(chair,FourChair),'trusted_host_context')
        # Re-read pinned originals; do not accept caller-mutated registry fields.
        self.context=FrozenSyntheticContext(context.package,context.locator_path)
        self.chair=chair
        self._temp=tempfile.TemporaryDirectory(prefix='four-chair-pending-',dir=temp_root)
        self.path=Path(self._temp.name)/'synthetic.sqlite'
        self.db=Database('sqlite:///'+str(self.path))
        # Original tables only; do NOT call create_all() that registers all business modules.
        Base.metadata.create_all(self.db.engine,tables=[AgentDraftRow.__table__,AuditEventRow.__table__])
        # Match the original audit append-only protection; no other application tables.
        with self.db.engine.begin() as conn:
            for operation in ('UPDATE','DELETE'):
                conn.execute(text("CREATE TRIGGER audit_events_no_"+operation.lower()+
                    " BEFORE "+operation+" ON audit_events BEGIN SELECT RAISE(ABORT,'audit_events is append-only'); END;"))

    def _project(self, case_id, receipt):
        ctx=self.context
        require(case_id==ctx.binding['caseId'],'case_binding')
        require(_digest(ctx.draft)==ctx.binding['draftDigest'] and
                _digest(ctx.registry)==ctx.binding['sourceSetDigest'],'context_changed')
        # Live in-process host, not a self-declared receipt status or signature.
        current=self.chair.receipt()
        require(receipt==current,'receipt_not_current')
        require(self.chair._draft_binding==ctx.binding,'host_draft_binding')
        generation=self.chair._draft_generation
        require(type(generation) is int and generation>0,'generation')
        require(current['phase']=='ready' and current['simulationOnly'] is True and
                current['modelExecuted'] is False and current['executionAuthorized'] is False,'simulation_scope')
        ops=current['opinions']
        require(len(ops)==4 and [o['role'] for o in ops]==list(ROLES),'four_roles')
        require(len({o['attemptId'] for o in ops})==4,'attempt_identity')
        require(all(s['factVerified'] is False for s in current['summary']),'unconfirmed_only')
        opinions=[];references={}
        item_ids={i['itemId'] for i in self.chair._packet['items']}
        for op in ops:
            require(op['round']==1 and op['simulated'] is True and
                    op.get('draftBinding')==ctx.binding and
                    op.get('draftBindingGeneration')==generation,'opinion_binding')
            selected=op.get('locatedReviewSources')
            require(isinstance(selected,dict) and set(selected)==item_ids,'explicit_sources')
            for item_id,source in selected.items():
                alias=source.get('sourceId')
                require(alias in ctx.registry and source=={'sourceId':alias,**ctx.registry[alias]},'located_source_binding')
            _validate({'reviews':op['reviews']},{'items':[
                {'itemId':item_id,'sourceText':source['excerpt']} for item_id,source in selected.items()]})
            reviews=[]
            for review in op['reviews']:
                source=selected[review['itemId']];quote=review['quote'];excerpt=source['excerpt']
                # A uniquely reviewable position, never an arbitrary first match.
                require(excerpt.count(quote)==1,'ambiguous_quote')
                ref={'sourceSha256':source['sha256'],'line':source['line'],'locator':source['locator'],
                     'excerptSha256':sha(excerpt),'quoteStart':excerpt.index(quote),
                     'quoteLength':len(quote),'offsetUnit':'unicode-codepoint','quoteSha256':sha(quote)}
                ref_id=_digest(ref)
                references[ref_id]=ref
                reviews.append({'itemId':review['itemId'],'label':review['label'],
                                'referenceId':ref_id,'reviewDigest':_digest(review)})
            opinions.append({'role':op['role'],'round':op['round'],'attemptId':op['attemptId'],
                'contextDigest':op['contextDigest'],'reviews':reviews})
        identity={'meetingId':current['meetingId'],'draftBinding':ctx.binding,'generation':generation}
        key=_digest(identity)
        # Not a generic agent-draft HTTP payload. Internal, physically isolated record.
        return {'schema':'mcis.synthetic-four-chair-pending.v1','draftId':'AD-'+str(int(key[:24],16)),
                'caseId':case_id,'meetingId':current['meetingId'],'draftBinding':copy.deepcopy(ctx.binding),
                'draftGeneration':generation,'handoffDigest':_digest(current),
                'status':'PendingReview','reviewedBy':None,'reviewedUtc':None,
                'createdUtc':SYNTHETIC_UTC,'syntheticOnly':True,'factVerified':False,
                'opinions':opinions,'references':references,
                'locatedCitationPlaceCount':len({(r['sourceSha256'],r['line']) for r in references.values()}),
                'sourceCountIsWeight':False,'sourceIndependence':'NOT_ASSESSED'}

    def enqueue(self, case_id, receipt):
        doc=self._project(case_id,copy.deepcopy(receipt))
        # Reuse the ORIGINAL session commit/rollback and original audit append.
        with self.db.session() as session:
            session.execute(text('BEGIN IMMEDIATE'))
            old=get_doc(session,AgentDraftRow,case_id,doc['draftId'])
            if old is not None:
                require(old==doc,'duplicate_changed')
                events=list(session.scalars(select(AuditEventRow).where(
                    AuditEventRow.case_id==case_id,AuditEventRow.entity_id==doc['draftId'])))
                require(len(events)==1 and events[0].action=='agent.synthetic_pending','duplicate_audit')
                return {'created':False,'draftId':doc['draftId']}
            put_doc(session,AgentDraftRow,case_id,doc['draftId'],doc)
            audit.append(session,case_id=case_id,operator='synthetic-four-chair-host',role='AgentService',
                action='agent.synthetic_pending',category='Agent',command='Synthetic four-chair pending metadata only',
                after=doc['handoffDigest'],entity_type='syntheticAgentDraft',entity_id=doc['draftId'],utc=SYNTHETIC_UTC)
        return {'created':True,'draftId':doc['draftId']}

    def reopen(self, case_id):
        self.db.engine.dispose()
        other=Database('sqlite:///'+str(self.path))
        try:
            with other.session() as s:
                return {'drafts':list_docs(s,AgentDraftRow,case_id),
                        'audit':audit.list_events(s,case_id),
                        'chain':audit.verify_chain(audit.all_lines(s,case_id))}
        finally:
            other.engine.dispose()

    def close(self):
        self.db.engine.dispose()
        self._temp.cleanup()
