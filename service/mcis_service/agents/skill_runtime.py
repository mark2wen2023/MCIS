"""Explicit in-process registry for trusted, offline MCIS skill callers.

Discovery is public metadata only. Invocation is not a case permission check:
the enclosing service must authenticate the caller and authorize source evidence
before constructing reviewed arguments. Never expose this dispatcher directly
as an unrestricted model tool or HTTP execution endpoint.
"""
from copy import deepcopy
from types import MappingProxyType
from .skills.ship_reconstruction.research_orchestrator import run_research

_SHIP_METADATA = MappingProxyType({
    'id': 'ship-reconstruction',
    'agent': 'ships',
    'name': '船舶三维研究重建',
    'execution': 'trusted_local_python',
    'requires_reviewed_input': True,
    'research_only': True,
    'lofting_authorized': False,
    'case_execution_available': False,
})
_HANDLERS = MappingProxyType({('ships','ship-reconstruction'): run_research})


def list_skills(agent):
    """Return detached metadata; no case data, files or handlers."""
    return [deepcopy(dict(_SHIP_METADATA))] if agent == 'ships' else []


def execute_local_skill(agent, skill_id, *, reviewed_arguments):
    """Only for already-authorized in-process callers; no network or file paths."""
    if not isinstance(agent,str) or not isinstance(skill_id,str):
        raise ValueError('invalid agent or skill identifier')
    handler = _HANDLERS.get((agent,skill_id))
    if handler is None:
        raise ValueError('unknown or unregistered skill')
    if not isinstance(reviewed_arguments,dict):
        raise ValueError('reviewed arguments required')
    result = handler(**reviewed_arguments)
    if result.get('research_only') is not True or result.get('lofting_authorized') is not False:
        raise ValueError('unexpected research authorization result')
    return result
