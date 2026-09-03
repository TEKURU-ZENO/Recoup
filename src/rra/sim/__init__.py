"""Simulator — sealed ground truth oracle.

Public API:
- VirtualClock: deterministic time management
- draw_for: common random number generation
- DowntimeCalendar: bank outage windows
- probability / draw: outcome model
- generate_portfolio: synthetic batch generator
"""

from rra.sim.clock import VirtualClock
from rra.sim.downtime import DowntimeCalendar
from rra.sim.outcome_model import draw, probability
from rra.sim.portfolio import generate_portfolio
from rra.sim.rng import draw_for

__all__ = [
    "VirtualClock",
    "DowntimeCalendar",
    "draw",
    "draw_for",
    "generate_portfolio",
    "probability",
]
