"""Opt-in, offline trajectory exchange validation; no API or database integration."""
from .validation import validate_trajectory, TrajectoryError

__all__ = ['validate_trajectory', 'TrajectoryError']
