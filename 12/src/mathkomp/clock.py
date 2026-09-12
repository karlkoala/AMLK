"""Zeitquelle.

Injizierbar, weil §40 Zeitpunkte speichert (first_evidence, last_review,
next_review) und §39 die Reaktivierung an Alter von Evidenz bindet. Die
Simulation der sechs Testfaelle (§104 Sprint 12) muss diese Zeitpunkte
deterministisch setzen koennen, sonst sind die Testfaelle nicht reproduzierbar.

§62 bleibt davon unberuehrt: Bearbeitungszeit wird gespeichert, aber nicht
als Kompetenzindikator verwendet.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


class Clock:
    """Reale Zeit."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def now_iso(self) -> str:
        return self.now().isoformat(timespec="seconds")

    def plus_days_iso(self, days: int | None) -> str | None:
        if days is None:
            return None
        return (self.now() + timedelta(days=days)).isoformat(timespec="seconds")


class FixedClock(Clock):
    """Deterministische Zeit fuer Simulation und Tests."""

    def __init__(self, start: str = "2026-01-12T08:00:00+00:00") -> None:
        self._now = datetime.fromisoformat(start)

    def now(self) -> datetime:
        return self._now

    def advance(self, *, days: int = 0, minutes: int = 0, seconds: int = 0) -> None:
        self._now += timedelta(days=days, minutes=minutes, seconds=seconds)


def days_between(earlier_iso: str | None, later: datetime) -> float | None:
    """Alter einer Evidenz in Tagen. None, wenn kein Zeitpunkt vorliegt."""
    if not earlier_iso:
        return None
    earlier = datetime.fromisoformat(earlier_iso)
    return (later - earlier).total_seconds() / 86400.0
