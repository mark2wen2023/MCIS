"""Strict legacy inventory entry; no export or restore authority."""
from ._inventory import _scan


def scan(connection, case_id):
    return _scan(connection, case_id, 'legacy')
