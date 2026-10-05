"""Legacy manual-probe entry point, not an automated test.

Importing/running this still loads Laya and prints a prediction, as before.
Prefer python -m scripts.choice_probe for manual use.
"""
from scripts.choice_probe import *  # Preserve the original import-time manual probe.
