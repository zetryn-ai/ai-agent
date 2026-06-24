"""Trading domain contract — the shared schemas both the framework consumers and
the bot agree on. Strategy code (nodes/agents) lives in ``strategies``; this layer
holds only data shapes and the ``DataProvider`` protocol.

Depends on nothing in ``zetryn`` and never the reverse.
"""

from .schemas import (
    ActivityData,
    AspectAnalysis,
    AuditVerdict,
    ContractData,
    DataProvider,
    Decision,
    FullAnalysis,
    HolderData,
    MarketData,
    NarrativeScore,
    PumpfunData,
    ScannerConfig,
    SniperConfig,
    SocialData,
    TelegramData,
    TokenInput,
    TokenSource,
    TradingContext,
    TwitterData,
    WalletIntel,
)

__all__ = [
    "ActivityData",
    "AspectAnalysis",
    "AuditVerdict",
    "ContractData",
    "DataProvider",
    "Decision",
    "FullAnalysis",
    "HolderData",
    "MarketData",
    "NarrativeScore",
    "PumpfunData",
    "ScannerConfig",
    "SniperConfig",
    "SocialData",
    "TelegramData",
    "TokenInput",
    "TokenSource",
    "TradingContext",
    "TwitterData",
    "WalletIntel",
]
