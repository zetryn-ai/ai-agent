"""Reference strategies built on the zetryn framework.

This is the proving ground: concrete memecoin agents (scanner, later sniper) and
sample data. In production these typically live in the bot repo; here they
demonstrate and test the framework against the ``trading`` contract.
"""

from .agents.scanner import build_scanner
from .agents.sniper import build_sniper
from .providers import SAMPLE_TOKENS, SampleProvider

__all__ = [
    "SAMPLE_TOKENS",
    "SampleProvider",
    "build_scanner",
    "build_sniper",
]
