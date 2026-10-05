"""Target taxonomy exports plus compatibility exports for the old taxonomy module.

New workflow consumers should import workflows.catalog directly.
"""
from .titles import TARGET_ROLES, ROLE_PATTERNS
from .industries import INDUSTRIES, INDUSTRY_PATTERNS
from .geography import GEOGRAPHIES, GEOGRAPHY_PATTERNS
from workflows.catalog import GTM_INTENTS, OPPORA_TOOLS, WORKFLOW_BLUEPRINTS

__all__ = ["TARGET_ROLES", "ROLE_PATTERNS", "INDUSTRIES", "INDUSTRY_PATTERNS", "GEOGRAPHIES",
           "GEOGRAPHY_PATTERNS", "GTM_INTENTS", "OPPORA_TOOLS", "WORKFLOW_BLUEPRINTS"]
