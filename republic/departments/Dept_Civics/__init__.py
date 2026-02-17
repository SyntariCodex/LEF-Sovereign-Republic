"""
Dept_Civics — Governance, Constitutional Enforcement, and Ethics.

Phase 34: Created __init__.py for proper Python package imports.
"""

from .agent_civics import AgentCivics
from .agent_constitution_guard import ConstitutionGuard, AmendmentVoting

__all__ = ['AgentCivics', 'ConstitutionGuard', 'AmendmentVoting']
