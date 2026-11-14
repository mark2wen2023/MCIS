"""Only initial writer reservation can prove this policy request has not committed."""
import sqlite3
from sqlalchemy.exc import OperationalError
from ..common.context import problem
from ..reports.access import begin


def reserve_policy_write(session):
    # Call before any policy/audit writes. Never catch the later commit phase here.
    try:
        begin(session)
    except OperationalError as exc:
        original = exc.orig
        code = getattr(original, 'sqlite_errorcode', None)
        busy = (session.get_bind().dialect.name == 'sqlite'
                and not exc.connection_invalidated
                and isinstance(original, sqlite3.OperationalError)
                and isinstance(code, int) and not isinstance(code, bool)
                and (code & 0xff) in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED))
        if not busy:
            raise
        # A rollback failure must escape, never produce a not_committed guarantee.
        session.rollback()
        raise problem(503, 'POLICY_WRITE_BUSY',
                      '策略未提交：数据库写入繁忙，请重新读取当前策略后重试',
                      {'commitState': 'not_committed', 'retryable': True}) from exc
