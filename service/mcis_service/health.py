"""Liveness response only; not business readiness, storage or dependency validation."""
from . import __version__


def health():
    return {"status": "ok", "service": "mcis-service", "version": __version__}
