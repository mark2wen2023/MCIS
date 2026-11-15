"""Offline durable reservation candidate; no execution, secrets, network or provider IO."""
import sqlite3
import uuid
from contextlib import contextmanager
from research.expert_group.packet import PACKET_SHA256

ROLES=('regulations','navigation','investigation','vessel')
PROFILE='mcis.public-four-expert-reservations.v1'
PER_TURN=2
TOTAL=16


class BudgetError(ValueError):
    pass


def check(ok,code):
    if not ok:raise BudgetError(code)


def ident(value):
    try:check(isinstance(value,str) and str(uuid.UUID(value))==value,'id')
    except (ValueError,TypeError,AttributeError):raise BudgetError('id') from None


class Ledger:
    def __init__(self,path):
        self.path=path
        with self._tx() as db:
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            check(not tables or tables=={'meetings','attempts'},'foreign_database')
            if tables:check(db.execute('PRAGMA user_version').fetchone()[0]==1,'ledger_version')
            db.execute('CREATE TABLE IF NOT EXISTS meetings (id TEXT PRIMARY KEY, packet TEXT NOT NULL, profile TEXT NOT NULL, stopped INTEGER NOT NULL DEFAULT 0)')
            db.execute('CREATE TABLE IF NOT EXISTS attempts (meeting TEXT NOT NULL, id TEXT NOT NULL, role TEXT NOT NULL, round INTEGER NOT NULL, ordinal INTEGER NOT NULL, outcome TEXT NOT NULL, PRIMARY KEY(meeting,id), UNIQUE(meeting,ordinal), FOREIGN KEY(meeting) REFERENCES meetings(id))')
            db.execute('PRAGMA user_version=1')

    @contextmanager
    def _tx(self):
        db=sqlite3.connect(self.path,timeout=5)
        db.row_factory=sqlite3.Row
        try:
            db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback();raise
        finally:db.close()

    def create(self,meeting_id,*,packet_sha256):
        ident(meeting_id);check(packet_sha256==PACKET_SHA256,'public_packet_pin')
        with self._tx() as db:
            row=db.execute('SELECT * FROM meetings WHERE id=?',(meeting_id,)).fetchone()
            if row:check(row['packet']==packet_sha256 and row['profile']==PROFILE,'meeting_binding')
            else:db.execute('INSERT INTO meetings(id,packet,profile) VALUES(?,?,?)',(meeting_id,packet_sha256,PROFILE))
        return self.snapshot(meeting_id)

    @staticmethod
    def _meeting(db,meeting):
        row=db.execute('SELECT * FROM meetings WHERE id=?',(meeting,)).fetchone()
        check(row is not None and row['profile']==PROFILE and row['packet']==PACKET_SHA256,'meeting_binding')
        return row

    def reserve(self,meeting_id,attempt_id,*,role,round_number):
        ident(meeting_id);ident(attempt_id)
        check(role in ROLES and type(role) is str,'role')
        check(type(round_number) is int and round_number in (1,2),'round')
        with self._tx() as db:
            meeting=self._meeting(db,meeting_id)
            old=db.execute('SELECT * FROM attempts WHERE meeting=? AND id=?',(meeting_id,attempt_id)).fetchone()
            if old:
                check(old['role']==role and old['round']==round_number,'changed_duplicate')
                # Metadata lookup only, NEVER a second dispatch permit.
                return self._view(old,True)
            check(not meeting['stopped'],'stopped')
            rows=db.execute('SELECT * FROM attempts WHERE meeting=? ORDER BY ordinal',(meeting_id,)).fetchall()
            check(not any(r['outcome']=='reserved' for r in rows),'unresolved_attempt')
            check(len(rows)<TOTAL,'meeting_budget')
            same=[r for r in rows if r['role']==role and r['round']==round_number]
            check(len(same)<PER_TURN,'turn_budget')
            if round_number==2:
                check(all(any(r['role']==prior and r['round']==1 and r['outcome']=='received_unverified' for r in rows) for prior in ROLES),'first_round_incomplete')
            check(not any(r['round']>round_number for r in rows),'round_regression')
            ordinal=len(rows)+1
            db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)',(meeting_id,attempt_id,role,round_number,ordinal,'reserved'))
            row=db.execute('SELECT * FROM attempts WHERE meeting=? AND id=?',(meeting_id,attempt_id)).fetchone()
            value=self._view(row,False)
        # Only returned after the SQLite commit. An exception is NOT a safe retry signal.
        return value

    @staticmethod
    def _view(row,replay):
        return {'attemptId':row['id'],'role':row['role'],'round':row['round'],'ordinal':row['ordinal'],
                'outcome':row['outcome'],'replay':replay,'executionAuthorized':False,'requestDispatched':False}

    def settle(self,meeting_id,attempt_id,*,outcome):
        ident(meeting_id);ident(attempt_id)
        check(outcome in ('received_unverified','not_dispatched','unknown'),'outcome')
        with self._tx() as db:
            meeting=self._meeting(db,meeting_id)
            row=db.execute('SELECT * FROM attempts WHERE meeting=? AND id=?',(meeting_id,attempt_id)).fetchone()
            check(row is not None,'attempt_missing')
            if row['outcome']!='reserved':
                check(row['outcome']==outcome,'changed_outcome');return self._view(row,True)
            check(not meeting['stopped'],'stopped')
            db.execute('UPDATE attempts SET outcome=? WHERE meeting=? AND id=?',(outcome,meeting_id,attempt_id))
            if outcome!='received_unverified':db.execute('UPDATE meetings SET stopped=1 WHERE id=?',(meeting_id,))
        return self.snapshot(meeting_id)

    def stop(self,meeting_id):
        ident(meeting_id)
        with self._tx() as db:
            self._meeting(db,meeting_id)
            db.execute('UPDATE meetings SET stopped=1 WHERE id=?',(meeting_id,))
            db.execute("UPDATE attempts SET outcome='unknown' WHERE meeting=? AND outcome='reserved'",(meeting_id,))
        return self.snapshot(meeting_id)

    def snapshot(self,meeting_id):
        ident(meeting_id)
        with self._tx() as db:
            meeting=self._meeting(db,meeting_id)
            rows=db.execute('SELECT * FROM attempts WHERE meeting=? ORDER BY ordinal',(meeting_id,)).fetchall()
            return {'schema':PROFILE,'meetingId':meeting_id,'packetSha256':meeting['packet'],
                    'roles':list(ROLES),'stopped':bool(meeting['stopped']),
                    'reservedAttempts':len(rows),'remainingAttempts':TOTAL-len(rows),
                    'attempts':[self._view(r,True) for r in rows],
                    'executionAuthorized':False,'modelExecuted':False,'costKnown':False,
                    'hardCancellationImplemented':False}
