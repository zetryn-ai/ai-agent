"""Example: KOL Copy-Trade strategy end-to-end (rule mode, v0.6.0).

Simulates a bot's event loop:
  1. A KOL buy event arrives.
  2. Bot enriches the bought mint into a TokenInput (here: hand-built fixture).
  3. Bot builds KOLContext and calls build_kol_copytrade.run(...).
  4. Bot reads Decision and would execute (or not).

Uses a throwaway KnowledgePack containing one whitelisted KOL. No LLM,
no API keys — the rule-mode path is fully deterministic.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from strategies import build_kol_copytrade
from trading import KOLBuyEvent, KOLContext, KOLCopyTradeConfig, TokenInput
from trading.schemas import ContractData, HolderData, MarketData, WalletIntel
from zetryn.core import State
from zetryn.knowledge import KnowledgePack


def _seed_pack(root: pathlib.Path) -> None:
    """Bot writes a kol_whitelist.json into its KnowledgePack."""
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "kol_whitelist.json").write_text(json.dumps({
        "wallets": {
            "KOL_SMART_ALPHA": {
                "name": "smart_money_alpha",
                "hit_rate": 0.62,
                "avg_pnl_pct": 0.45,
                "trades_30d": 31,
                "exit_pattern": "scales_out_50pct",
                "tier": "S",
                "min_sol_to_copy": 0.5,
            },
            "KOL_DECENT_BETA": {
                "name": "decent_kol_beta",
                "hit_rate": 0.48,
                "avg_pnl_pct": 0.22,
                "trades_30d": 18,
                "tier": "A",
                "min_sol_to_copy": 0.3,
            },
        },
        "min_tier_to_copy": "A",
        "min_hit_rate": 0.40,
    }), encoding="utf-8")


def _enriched_token(mint: str) -> TokenInput:
    """In production this is whatever path the bot already uses for the scanner."""
    return TokenInput(
        mint=mint,
        symbol="MEME",
        name="MemeFreshLaunch",
        market=MarketData(
            mcap=120_000, liquidity_usd=15_000, volume_1h=22_000, volume_24h=80_000,
            age_seconds=180,
        ),
        holders=HolderData(count=180, top10_pct=0.22),
        contract=ContractData(lp_burned=True),
        wallets=WalletIntel(
            safety_score=82, smart_wallet_buys=4, bundler_wallet_count=1, sniper_wallet_count=3,
        ),
    )


async def _decide(graph, ctx: KOLContext, label: str) -> None:
    state = await graph.run(State(context=ctx))
    d = state.output
    print(f"\n[{label}] action={d.action.upper()} confidence={d.confidence}")
    if d.size is not None:
        print(f"  size      : {d.size}")
    if d.scores:
        print(f"  scores    : {d.scores}")
    print(f"  reasons   : {'; '.join(d.reasons)}")
    nodes = " -> ".join(t.node for t in state.trace)
    print(f"  trace     : {nodes}")


async def main() -> None:
    with tempfile.TemporaryDirectory(prefix="zetryn-kol-") as tmp:
        root = pathlib.Path(tmp)
        _seed_pack(root)
        pack = KnowledgePack.from_dir(root)
        kol_copytrade = build_kol_copytrade(pack)

        # 1) Healthy signal from a trusted S-tier KOL → BUY
        await _decide(
            kol_copytrade,
            KOLContext(
                event=KOLBuyEvent(
                    wallet="KOL_SMART_ALPHA", mint="MEME1",
                    sol_amount=2.0, detected_at_ts=1000.0, block_age_seconds=4.0,
                ),
                token=_enriched_token("MEME1"),
            ),
            "1. trusted KOL, fresh signal, clean token",
        )

        # 2) Unknown wallet → SKIP
        await _decide(
            kol_copytrade,
            KOLContext(
                event=KOLBuyEvent(
                    wallet="KOL_UNKNOWN_X", mint="MEME2",
                    sol_amount=2.0, detected_at_ts=1100.0, block_age_seconds=4.0,
                ),
                token=_enriched_token("MEME2"),
            ),
            "2. unknown wallet",
        )

        # 3) Stale signal (60s old) → SKIP
        await _decide(
            kol_copytrade,
            KOLContext(
                event=KOLBuyEvent(
                    wallet="KOL_SMART_ALPHA", mint="MEME3",
                    sol_amount=2.0, detected_at_ts=1200.0, block_age_seconds=60.0,
                ),
                token=_enriched_token("MEME3"),
            ),
            "3. signal too stale",
        )

        # 4) Trusted KOL but token is a honeypot → ABORT
        bad_token = _enriched_token("MEME4")
        bad_token.contract.is_honeypot = True
        await _decide(
            kol_copytrade,
            KOLContext(
                event=KOLBuyEvent(
                    wallet="KOL_SMART_ALPHA", mint="MEME4",
                    sol_amount=2.0, detected_at_ts=1300.0, block_age_seconds=4.0,
                ),
                token=bad_token,
            ),
            "4. honeypot token (overrides KOL signal)",
        )

        # 5) Repeat copy of same KOL inside cooldown → SKIP
        await _decide(
            kol_copytrade,
            KOLContext(
                event=KOLBuyEvent(
                    wallet="KOL_SMART_ALPHA", mint="MEME5",
                    sol_amount=2.0, detected_at_ts=1010.0, block_age_seconds=4.0,
                ),
                token=_enriched_token("MEME5"),
                last_copy_ts=1000.0,   # copied 10s ago, default cooldown 60s
            ),
            "5. cooldown active",
        )

        # 6) Deployment-level override: bot wants stricter min_kol_hit_rate
        strict = KOLCopyTradeConfig(min_kol_hit_rate=0.50)
        await _decide(
            kol_copytrade,
            KOLContext(
                event=KOLBuyEvent(
                    wallet="KOL_DECENT_BETA",  # hit_rate 0.48
                    mint="MEME6", sol_amount=1.0,
                    detected_at_ts=1400.0, block_age_seconds=4.0,
                ),
                token=_enriched_token("MEME6"),
                config=strict,
            ),
            "6. deployment override: stricter than pack floor",
        )


if __name__ == "__main__":
    asyncio.run(main())
