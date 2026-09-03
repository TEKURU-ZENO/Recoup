"""Virtual clock for deterministic simulation.

All times are UTC-aware. IST conversion is provided for salary-date logic.
The clock refuses to move backwards and rejects naive datetimes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
UTC = timezone.utc


class VirtualClock:
    """A deterministic, forward-only clock for simulation."""

    def __init__(self, start: datetime) -> None:
        self._validate_aware(start)
        self._now = start

    @staticmethod
    def _validate_aware(dt: datetime) -> None:
        if dt.tzinfo is None:
            raise ValueError(
                f"Naive datetime not allowed: {dt!r}. Use timezone-aware datetimes."
            )

    @property
    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> datetime:
        """Advance the clock by a positive timedelta."""
        if delta < timedelta(0):
            raise ValueError(
                f"Cannot advance by negative delta: {delta}. Clock is forward-only."
            )
        self._now = self._now + delta
        return self._now

    def advance_to(self, dt: datetime) -> datetime:
        """Jump to a specific time. Must be >= current time."""
        self._validate_aware(dt)
        if dt < self._now:
            raise ValueError(
                f"Cannot move backwards: {dt} < {self._now}. Clock is forward-only."
            )
        self._now = dt
        return self._now

    def to_ist(self, dt: datetime | None = None) -> datetime:
        """Convert a datetime (or current time) to IST."""
        target = dt or self._now
        self._validate_aware(target)
        return target.astimezone(IST)

    def ist_now(self) -> datetime:
        """Current time in IST."""
        return self.to_ist(self._now)
