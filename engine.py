"""Compatibility alias for engines.laya_engine; shares the same module and singleton state."""
import sys
from engines import laya_engine as _implementation

sys.modules[__name__] = _implementation
