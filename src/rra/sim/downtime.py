"""Bank downtime calendar for simulation.

Generates deterministic outage windows:
- Scheduled overnight maintenance: 00:00-04:00 IST daily
- Unscheduled interbank outages: seeded random windows (2-6 hours, ~2-4 per month)
"""

from __future__ import annotations

import hashlib
import struct
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


class DowntimeCalendar:
    """Deterministic bank downtime calendar.

    Generates a fixed set of outage windows from a seed, covering
    a configurable horizon from a start date.
    """

    def __init__(
        self,
        seed: int,
        start: datetime,
        horizon_days: int = 60,
    ) -> None:
        if start.tzinfo is None:
            raise ValueError("start must be timezone-aware")
        self._seed = seed
        self._start = start
        self._horizon_days = horizon_days
        # Pre-generate unscheduled outages
        self._unscheduled: list[tuple[datetime, datetime]] = (
            self._generate_unscheduled_outages()
        )

    def _seeded_float(self, key: str) -> float:
        """Deterministic float in [0, 1) from a string key."""
        digest = hashlib.sha256(f"{self._seed}|{key}".encode()).digest()
        return struct.unpack("!Q", digest[:8])[0] / (2**64)

    def _generate_unscheduled_outages(
        self,
    ) -> list[tuple[datetime, datetime]]:
        """Generate ~2-4 unscheduled outages per 30-day period."""
        outages: list[tuple[datetime, datetime]] = []
        num_months = max(1, self._horizon_days // 30)

        for month_idx in range(num_months):
            # 2-4 outages per month
            count_draw = self._seeded_float(f"outage_count_{month_idx}")
            count = 2 + int(count_draw * 3)  # 2, 3, or 4

            for outage_idx in range(count):
                # Day within the month period
                day_draw = self._seeded_float(
                    f"outage_day_{month_idx}_{outage_idx}"
                )
                day_offset = int(day_draw * 30)

                # Hour (avoid overlap with scheduled maintenance 00:00-04:00 IST)
                hour_draw = self._seeded_float(
                    f"outage_hour_{month_idx}_{outage_idx}"
                )
                # Pick from 06:00-22:00 IST range
                hour_ist = 6 + int(hour_draw * 16)

                # Duration: 2-6 hours
                dur_draw = self._seeded_float(
                    f"outage_dur_{month_idx}_{outage_idx}"
                )
                duration_hours = 2 + int(dur_draw * 5)  # 2, 3, 4, 5, or 6

                # Build the outage start in IST, then convert to UTC
                base_date = self._start + timedelta(days=month_idx * 30)
                outage_start_ist = (
                    base_date.astimezone(IST)
                    .replace(
                        hour=hour_ist,
                        minute=0,
                        second=0,
                        microsecond=0,
                    )
                    + timedelta(days=day_offset)
                )
                outage_start = outage_start_ist.astimezone(timezone.utc)
                outage_end = outage_start + timedelta(hours=duration_hours)

                outages.append((outage_start, outage_end))

        # Sort by start time
        outages.sort(key=lambda x: x[0])
        return outages

    def _is_scheduled_maintenance(self, at: datetime) -> bool:
        """Check if time falls in daily 00:00-04:00 IST maintenance."""
        ist_time = at.astimezone(IST)
        return 0 <= ist_time.hour < 4

    def is_down(self, at: datetime) -> bool:
        """Check if the bank is down at the given time.

        Returns True during:
        - Daily scheduled maintenance: 00:00-04:00 IST
        - Any unscheduled outage window
        """
        if at.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")

        # Scheduled overnight maintenance
        if self._is_scheduled_maintenance(at):
            return True

        # Unscheduled outages
        for start, end in self._unscheduled:
            if start <= at < end:
                return True

        return False

    def next_recovery_after(self, at: datetime) -> datetime:
        """Return the next time the bank is expected to be up.

        If the bank is currently up, returns the input time.
        """
        if at.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")

        if not self.is_down(at):
            return at

        # Check scheduled maintenance first
        if self._is_scheduled_maintenance(at):
            ist_time = at.astimezone(IST)
            # Recovery at 04:00 IST on the same day
            recovery = ist_time.replace(
                hour=4, minute=0, second=0, microsecond=0
            )
            if recovery <= ist_time:
                # Already past 04:00 today, next day
                recovery += timedelta(days=1)
            candidate = recovery.astimezone(timezone.utc)
        else:
            candidate = at

        # Check unscheduled outages
        for start, end in self._unscheduled:
            if start <= at < end:
                # Recovery is end of this outage
                candidate = max(candidate, end)

        # Verify the recovery time isn't also in a down window
        # (e.g., unscheduled outage ending during maintenance)
        if self.is_down(candidate):
            return self.next_recovery_after(candidate + timedelta(minutes=1))

        return candidate

    @property
    def unscheduled_outages(self) -> list[tuple[datetime, datetime]]:
        """The list of unscheduled outage windows (for inspection/testing)."""
        return list(self._unscheduled)
