"""MJD conversions without astropy.time.

astropy.time may try to download fresh leap-second / IERS tables at runtime, which a
serverless function should never do. We only need two simple conversions:
  * MJD (UTC) -> ISO-8601 UTC string, millisecond precision, "Z" suffix
  * MJD -> Julian year, for proper-motion propagation (a ~1 minute UTC/TT difference
    is irrelevant at milliarcsecond-per-year rates)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

_MJD_EPOCH = datetime(1858, 11, 17, tzinfo=timezone.utc)


def mjd_to_iso(mjd: float | None) -> str | None:
    if mjd is None:
        return None
    ms = round(float(mjd) * 86_400_000)
    t = _MJD_EPOCH + timedelta(milliseconds=ms)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


def mjd_to_jyear(mjd: float) -> float:
    return 2000.0 + (float(mjd) - 51544.5) / 365.25
