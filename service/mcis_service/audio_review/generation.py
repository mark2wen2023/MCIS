"""Isolated task generation and transactional observations, never completion proof."""
from uuid import uuid4
from sqlalchemy import Column, Integer, String, JSON, UniqueConstraint
from .app import Storage
from ..common.csjson import sha256_utf8


class Generation(Storage):
    __tablename__ = 'audio_task_generations'
    generation_id = Column(String, primary_key=True)
    case_id = Column(String, nullable=False, index=True)
    task_id = Column(String, nullable=False, unique=True)
    doc = Column(JSON, nullable=False)


class Observation(Storage):
    __tablename__ = 'audio_task_observations'
    id = Column(Integer, primary_key=True)
    case_id = Column(String, nullable=False, index=True)
    generation_id = Column(String, nullable=False)
    ordinal = Column(Integer, nullable=False)
    doc = Column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint('generation_id', 'ordinal'),)


def register(session, case_id, task_id, source, audit_row):
    row = Generation(generation_id=uuid4().hex, case_id=case_id, task_id=task_id,
                     doc={'protocol': 'audio-generation-observation/v1', 'source': source})
    session.add(row)
    record(session, row, 0, 'registration-recorded-before-dispatch', audit_row)
    return row.generation_id


def record(session, generation, ordinal, event, audit_row):
    if audit_row.case_id != generation.case_id or audit_row.command != generation.task_id:
        raise ValueError('generation audit mismatch')
    session.add(Observation(case_id=generation.case_id, generation_id=generation.generation_id,
                            ordinal=ordinal, doc={'event': event, 'auditSeq': audit_row.seq,
                            'auditLineSha256': sha256_utf8(audit_row.line),
                            'writers': 'unknown', 'manifestStatus': 'not-captured',
                            'archiveReady': False}))


def observe(session, generation_id, event, audit_row):
    row = session.get(Generation, generation_id)
    if row is None:
        raise ValueError('missing new generation; never backfill legacy')
    record(session, row, 1, event, audit_row)
