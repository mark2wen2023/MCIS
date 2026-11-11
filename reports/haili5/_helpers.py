# -*- coding: utf-8 -*-
"""Helpers for Haili5 case extraction."""
from datetime import datetime, timedelta, timezone
from typing import Optional

BJ = timezone(timedelta(hours=8))
UTC = timezone.utc

def dm_to_dd(deg: int, minutes: float) -> float:
    return round(deg + minutes / 60.0, 6)

def dms_to_dd(deg: int, minutes: int, seconds: float) -> float:
    return round(deg + minutes / 60.0 + seconds / 3600.0, 7)

def geo(lat_d, lat_m, lon_d, lon_m, lat_s=None, lon_s=None):
    if lat_s is not None:
        lat = dms_to_dd(lat_d, lat_m, lat_s)
        lat_dm = round(lat_m + lat_s / 60.0, 4)
    else:
        lat = dm_to_dd(lat_d, lat_m)
        lat_dm = lat_m
    if lon_s is not None:
        lon = dms_to_dd(lon_d, lon_m, lon_s)
        lon_dm = round(lon_m + lon_s / 60.0, 4)
    else:
        lon = dm_to_dd(lon_d, lon_m)
        lon_dm = lon_m
    return {
        "latDeg": lat,
        "lonDeg": lon,
        "latDm": f"{lat_d}°{lat_dm:g}′N",
        "lonDm": f"{lon_d}°{lon_dm:g}′E",
        "original": (
            f"{lat_d}°{lat_dm:06.3f}′N/{lon_d}°{lon_dm:06.3f}′E"
            if lat_s is None and lon_s is None
            else f"{lat_d}°{lat_m:02d}′{lat_s:.3f}″N {lon_d}°{lon_m:02d}′{lon_s:.3f}″E"
        ),
    }

def src(page, quote, pdf_page=None, figure=None, note=None):
    d = {"page": page, "quote": quote}
    if pdf_page is not None:
        d["pdfPage"] = pdf_page
    if figure:
        d["figure"] = figure
    if note:
        d["note"] = note
    return d

def bt(hour, minute, second=0, day=25, month=10, year=2025, approx=False):
    t = datetime(year, month, day, hour, minute, second, tzinfo=BJ)
    u = t.astimezone(UTC)
    out = {
        "beijing": t.isoformat(),
        "utc": u.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "approximate": approx,
    }
    return out
