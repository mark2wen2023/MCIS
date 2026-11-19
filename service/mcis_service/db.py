"""SQLite + SQLAlchemy 2.0。

存储模式：每个业务模块一张表，键列（case_id + 实体编号）+ 索引列 + doc（JSON，完整契约对象）。
审计表与保管链表是只追加的：SQLite 触发器拒绝 UPDATE / DELETE。
"""
from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Any, Iterator

from sqlalchemy import JSON, Column, Integer, String, Text, UniqueConstraint, create_engine, event, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .common.timeutil import iso, now_utc


class Base(DeclarativeBase):
    pass


class DocMixin:
    """通用文档行：一个契约对象一行。"""

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), nullable=False, index=True)
    key = Column(String(64), nullable=False)
    doc = Column(JSON, nullable=False)
    created_utc = Column(String(32), nullable=False, default=lambda: iso(now_utc()))
    updated_utc = Column(String(32), nullable=False, default=lambda: iso(now_utc()))


APPEND_ONLY_TABLES = ("audit_events", "custody_events")

# 全局写锁：分配 seq 与 hash 链时串行化（SQLite 单进程服务足够）。
WRITE_LOCK = threading.RLock()


class Database:
    def __init__(self, url: str):
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(url, connect_args=connect_args, future=True)
        if url.startswith("sqlite"):
            @event.listens_for(self.engine, "connect")
            def _pragma(dbapi_conn, _rec):  # pragma: no cover - 连接级设置
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA journal_mode=WAL")
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)

    def create_all(self) -> None:
        # 导入所有模块以注册表
        from . import models_registry  # noqa: F401
        Base.metadata.create_all(self.engine)
        self._install_append_only_triggers()

    def _install_append_only_triggers(self) -> None:
        with self.engine.begin() as conn:
            for t in APPEND_ONLY_TABLES:
                conn.execute(text(
                    f"CREATE TRIGGER IF NOT EXISTS {t}_no_update BEFORE UPDATE ON {t} "
                    f"BEGIN SELECT RAISE(ABORT, '{t} is append-only'); END;"))
                conn.execute(text(
                    f"CREATE TRIGGER IF NOT EXISTS {t}_no_delete BEFORE DELETE ON {t} "
                    f"BEGIN SELECT RAISE(ABORT, '{t} is append-only'); END;"))

    @contextmanager
    def session(self) -> Iterator[Session]:
        s = self.SessionLocal()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()


# ---------- 通用文档仓储 ----------

def list_docs(s: Session, model, case_id: str, order_by=None) -> list[dict[str, Any]]:
    q = select(model).where(model.case_id == case_id)
    q = q.order_by(order_by if order_by is not None else model.id)
    return [dict(r.doc) for r in s.scalars(q)]


def get_row(s: Session, model, case_id: str, key: str):
    return s.scalars(select(model).where(model.case_id == case_id, model.key == key)).first()


def get_doc(s: Session, model, case_id: str, key: str) -> dict[str, Any] | None:
    r = get_row(s, model, case_id, key)
    return dict(r.doc) if r else None


def put_doc(s: Session, model, case_id: str, key: str, doc: dict[str, Any], **cols) -> None:
    r = get_row(s, model, case_id, key)
    if r is None:
        r = model(case_id=case_id, key=key, doc=doc, **cols)
        s.add(r)
    else:
        r.doc = dict(doc)
        r.updated_utc = iso(now_utc())
        for k, v in cols.items():
            setattr(r, k, v)
    s.flush()


def table_args(name: str):
    return (UniqueConstraint("case_id", "key", name=f"uq_{name}_case_key"),)


__all__ = ["Base", "DocMixin", "Database", "WRITE_LOCK", "list_docs", "get_doc", "get_row", "put_doc", "table_args",
           "Column", "Integer", "String", "Text", "JSON"]
