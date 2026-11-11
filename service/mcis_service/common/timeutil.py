"""时间工具：与 C# SimpleJson.FormatIso / AuditJson.TruncateToSecond 一致。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

UTC = timezone.utc


def now_utc() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def iso(dt: datetime) -> str:
    """yyyy-MM-ddTHH:mm:ssZ（截断到秒）。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_ms(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    dt = dt.astimezone(UTC)
    if dt.microsecond == 0:
        return iso(dt)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def parse_iso(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def sim_to_utc(epoch_iso: str, sec: float) -> str:
    return iso_ms(parse_iso(epoch_iso) + timedelta(seconds=sec))


def utc_to_sim(epoch_iso: str, utc_iso: str) -> float:
    return (parse_iso(utc_iso) - parse_iso(epoch_iso)).total_seconds()
