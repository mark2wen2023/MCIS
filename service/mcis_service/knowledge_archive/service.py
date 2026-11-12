import copy
from sqlalchemy import select,func,cast,LargeBinary,inspect
from ..knowledge.models import KnowledgeCardRow as Card,KnowledgeAuditRow as Event
from ..common.timeutil import iso,now_utc
from .models import Archive,Epoch,Snapshot
from .validation import encode,validate,sha,ZERO,fail

def envelope(s):
    # Bound rows and a lower bound on UTF8 bytes before loading any full bodies.
    from .validation import MAX
    for model in (Card,Event,Epoch,Snapshot):
        if {c['name']for c in inspect(s.connection()).get_columns(model.__tablename__)}!={c.name for c in model.__table__.columns}:fail()
    for model,cap in ((Card,1024),(Event,4096),(Snapshot,4096)):
        if s.scalar(select(func.count()).select_from(model))>cap:fail(413,'KNOWLEDGE_ARCHIVE_BUDGET')
    size=0
    # SQLite json() removes representation whitespace; dividing JSON bytes by six
    # permits even every scalar to be stored as \uXXXX rather than UTF8.
    # Text columns below are retained verbatim, so their UTF8 length is a lower bound.
    for col in (Card.doc,Snapshot.before_doc,Snapshot.after_doc):
        size+=s.scalar(select(func.coalesce(func.sum(func.length(cast(func.json(col),LargeBinary))),0)))//6
    for col in (Card.search_text,Card.tags_text,Event.line):
        size+=s.scalar(select(func.coalesce(func.sum(func.length(cast(col,LargeBinary))),0)))
    if size>MAX:fail(413,'KNOWLEDGE_ARCHIVE_BUDGET')
    cards=s.scalars(select(Card).order_by(Card.id)).all();events=s.scalars(select(Event).order_by(Event.seq)).all()
    epochs=s.scalars(select(Epoch)).all();snaps=s.scalars(select(Snapshot).order_by(Snapshot.seq)).all()
    if len(epochs)>1 or(epochs and epochs[0].key!=1)or(not epochs and snaps):fail(409,'KNOWLEDGE_ARCHIVE_INTEGRITY')
    coverage={'mode':'legacy-only','firstSeq':None,'priorHeadSha256':sha(events[-1].line.encode())if events else ZERO}
    if epochs:coverage={'mode':'from-sequence','firstSeq':epochs[0].first_seq,'priorHeadSha256':epochs[0].prior_head_sha256}
    return {'format':'MCIS-KNOWLEDGE-ARCHIVE','version':1,'exportedUtc':iso(now_utc()),
            'cards':[{'order':i,'cardId':r.card_id,'status':r.status,'kind':r.kind,'searchText':r.search_text,'tagsText':r.tags_text,'doc':r.doc}for i,r in enumerate(cards,1)],
            'audit':[{'seq':r.seq,'line':r.line}for r in events],
            'auditSnapshots':{'coverage':coverage,'items':[{'seq':r.seq,'auditLineSha256':r.audit_line_sha256,'cardId':r.card_id,'beforeDoc':r.before_doc,'afterDoc':r.after_doc}for r in snaps]}}

def prepare_write(s):
    # No online archive capacity limit and no full-body serialization under write lock.
    # Full historical semantic/hash validation belongs to export.
    s.flush()
    count,minimum,maximum=s.execute(select(func.count(Event.seq),func.min(Event.seq),func.max(Event.seq))).one()
    if count and(minimum!=1 or maximum!=count):fail(409,'KNOWLEDGE_ARCHIVE_INTEGRITY')
    last=s.get(Event,count) if count else None
    epochs=s.scalars(select(Epoch)).all()
    scount,smin,smax=s.execute(select(func.count(Snapshot.seq),func.min(Snapshot.seq),func.max(Snapshot.seq))).one()
    if len(epochs)>1 or(epochs and epochs[0].key!=1):fail(409,'KNOWLEDGE_ARCHIVE_INTEGRITY')
    if not epochs:
        if scount:fail(409,'KNOWLEDGE_ARCHIVE_INTEGRITY')
        s.add(Epoch(key=1,first_seq=count+1,prior_head_sha256=sha(last.line.encode())if last else ZERO))
    else:
        e=epochs[0]
        prior=s.get(Event,e.first_seq-1)if e.first_seq>1 else None
        if e.first_seq<1 or e.first_seq>count or e.prior_head_sha256!=(sha(prior.line.encode())if prior else ZERO)or scount!=count-e.first_seq+1 or smin!=e.first_seq or smax!=count:fail(409,'KNOWLEDGE_ARCHIVE_INTEGRITY')
        tail=s.get(Snapshot,count)
        if tail.audit_line_sha256!=sha(last.line.encode()):fail(409,'KNOWLEDGE_ARCHIVE_INTEGRITY')

def capture(s,event,before,after):
    # Existing online writer already validates content. Archive-specific actor/size
    # limits must never prevent a legitimate withdrawal of an older online card.
    from .validation import strict
    prior=s.scalar(select(Snapshot).where(Snapshot.card_id==after['cardId']).order_by(Snapshot.seq.desc()).limit(1))
    if prior is not None and prior.after_doc!=before:fail(409,'KNOWLEDGE_ARCHIVE_INTEGRITY')
    parsed=strict(event.line.encode())
    if parsed['cardId']!=after['cardId']or(parsed['action']=='knowledge.create'and before is not None):fail(409,'KNOWLEDGE_ARCHIVE_INTEGRITY')
    s.add(Snapshot(seq=event.seq,audit_line_sha256=sha(event.line.encode()),card_id=after['cardId'],before_doc=copy.deepcopy(before),after_doc=copy.deepcopy(after)))
    s.flush()

def stored(row):
    try:
        d,summary=validate(bytes(row.raw_bytes))
        if summary['archiveSha256']!=row.archive_sha256 or summary['byteLength']!=row.byte_length or summary['cardCount']!=row.card_count or summary['auditCount']!=row.audit_count or summary['auditHeadSha256']!=row.audit_head_sha256 or row.imported_role!='LeadInvestigator':fail()
        from .validation import utc,string
        utc(row.imported_utc);string(row.imported_by,160)
        return d,{'summary':summary,'importedUtc':row.imported_utc,'importedBy':row.imported_by,'importedRole':row.imported_role}
    except Exception:fail(409,'KNOWLEDGE_ARCHIVE_INTEGRITY')
