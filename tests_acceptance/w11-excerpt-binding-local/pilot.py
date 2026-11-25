"""Single-case test-only internal read adapter, never an API/router."""
from hashlib import sha256
from sqlalchemy import select, text
from fastapi import HTTPException
from mcis_service.cases.models import CaseRow
from mcis_service.db import WRITE_LOCK, get_doc
from mcis_service.ecfc_drafts import router as ec
from mcis_service.ecfc_drafts.models import EcfcAuditRow, EcfcWorksheetRow
from mcis_service.evidence_intake.router import _read_original_for_access

CASE = "SYN-XREPO-001"
SOURCE_SHA = "418be9609b46a00062c41fb49073911986098e9a61e010f4311aa86946ecd3ea"
UTC = "2026-02-01T12:01:49.000Z"
EDGE = ("E01", "C01", "N01")

class Unavailable(Exception):
    pass

def refuse():
    raise Unavailable("Synthetic local association unavailable")

def read_excerpt(ctx, case_id, revision, digest, edge):
    """Only a successful committed Access releases bytes as a single verified span."""
    if case_id != CASE or type(revision) is not int or edge != EDGE:
        return None
    try:
        with WRITE_LOCK, ctx.db.session() as s:
            if s.get_bind().dialect.name != "sqlite":
                refuse()
            ec.begin(s,write=True)
            ec.snapshot(s,ctx,case_id,[])
            case=get_doc(s,CaseRow,case_id,case_id)
            if case["isFictionalDemo"] is not True:
                refuse()
            row=s.get(EcfcWorksheetRow,case_id)
            if row is None:
                refuse()
            graph=ec.validate_document(row.doc,case_id)
            latest=s.scalars(select(EcfcAuditRow).where(EcfcAuditRow.case_id==case_id)
                             .order_by(EcfcAuditRow.revision.desc()).limit(1)).first()
            if latest is None or ec.validate_event(latest.doc,case_id,latest.revision)["after"]!=graph:
                refuse()
            if (graph["revision"],graph["digest"])!=(revision,digest):
                refuse()
            pin=s.execute(text("SELECT * FROM pilot_single_source WHERE singleton=1")).mappings().first()
            if (pin is None or pin["revoked"]!=0 or (pin["case_id"],pin["revision"],pin["graph_digest"])!=(case_id,revision,digest)
                or (pin["edge_id"],pin["from_id"],pin["to_id"])!=edge):
                refuse()
            if not any((e["id"],e["from"],e["to"])==edge for e in graph["draft"]["edges"]):
                refuse()
            if not any(n["id"] in edge[1:] and pin["evidence_id"] in n["evidenceIds"] for n in graph["draft"]["nodes"]):
                refuse()
            if ec.check_document_sources(s,ctx,case_id,graph)!="unchanged":
                refuse()
            if (pin["source_sha"],pin["start_byte"],pin["end_byte"])!=(SOURCE_SHA,97,121):
                refuse()
            receipt, raw=_read_original_for_access(ctx,s,case_id,pin["intake_digest"],"Synthetic bound ECFC edge source only")
            if (receipt["caseId"],receipt["evidenceId"],receipt["sourceSha256"])!=(case_id,pin["evidence_id"],SOURCE_SHA) or sha256(raw).hexdigest()!=SOURCE_SHA:
                refuse()
            span=raw[pin["start_byte"]:pin["end_byte"]].decode("utf-8",errors="strict")
            if span!=UTC:
                refuse()
            result={"excerpt":span,"sourceRecordedUtc":span,"seekAvailable":False,
                    "status":"Draft","strength":"ToBeVerified"}
        return result
    except (Unavailable, ec.PreviewError, HTTPException, UnicodeError):
        return None
