"""Sample tokens + an in-memory provider for tests, demos, and (later) backtests.

``SAMPLE_TOKENS`` are ready-to-use ``TokenInput`` objects (push model). The
``SampleProvider`` implements the ``DataProvider`` pull protocol over the same data,
so push and pull are interchangeable.
"""

from __future__ import annotations

from trading.schemas import (
    ContractData,
    DataProvider,
    HolderData,
    MarketData,
    SocialData,
    TelegramData,
    TokenInput,
    TwitterData,
)

# A small sample set covering the main outcomes.
SAMPLE_TOKENS: dict[str, TokenInput] = {
    "GOOD": TokenInput(
        mint="GOOD",
        symbol="PEPE2",
        name="Pepe Reborn",
        market=MarketData(mcap=400_000, liquidity_usd=42_000, volume_1h=120_000, txns_1h=850),
        holders=HolderData(count=620, top10_pct=0.22, dev_pct=0.02),
        contract=ContractData(lp_burned=True),
        social=SocialData(
            twitter=TwitterData(handle="pepe2", followers=8_000, tweets_1h=35),
            telegram=TelegramData(members=2_400, alpha_calls=4),
            kol_count_5m=3,
        ),
    ),
    "RUG": TokenInput(
        mint="RUG",
        symbol="SCAM",
        name="Safe Moon Inu",
        market=MarketData(mcap=90_000, liquidity_usd=8_000, volume_1h=15_000),
        holders=HolderData(count=120, top10_pct=0.85, dev_pct=0.4),
        contract=ContractData(mint_authority_active=True, notes=["mint authority not revoked"]),
    ),
    "LOWLIQ": TokenInput(
        mint="LOWLIQ",
        symbol="DUST",
        name="Dust Coin",
        market=MarketData(mcap=20_000, liquidity_usd=900, volume_1h=400),
        holders=HolderData(count=80, top10_pct=0.3),  # passes safety, fails market
    ),
}


class SampleProvider:
    """Implements the DataProvider pull protocol over the sample set."""

    def __init__(self, tokens: dict[str, TokenInput] | None = None) -> None:
        self._tokens = tokens or SAMPLE_TOKENS

    async def fetch(self, mint: str) -> TokenInput:
        if mint not in self._tokens:
            raise KeyError(f"no sample for mint {mint!r}")
        return self._tokens[mint]


__all__ = ["SAMPLE_TOKENS", "DataProvider", "SampleProvider"]
