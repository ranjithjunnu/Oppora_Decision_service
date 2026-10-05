"""Compatibility alias for agents.gtm_agent; shares the same module and singleton state."""
import sys
from agents import gtm_agent as _implementation

sys.modules[__name__] = _implementation
