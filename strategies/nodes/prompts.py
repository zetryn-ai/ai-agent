"""Prompt builder + fallback for the narrative LLM advisor node.

Prompts are kept here as assets, separate from graph logic, so they can be
iterated and A/B-tested without touching the agent wiring.
"""

from __future__ import annotations

from trading.schemas import NarrativeScore
from zetryn.core import State
from zetryn.llm import Message, system, user


def narrative_prompt(state: State) -> list[Message]:
    t = state.context.token
    m, h, s, w, a = t.market, t.holders, t.social, t.wallets, t.activity
    tw = s.twitter

    facts = [
        f"Symbol: {t.symbol}  Name: {t.name}  Source: {t.source}",
        f"Mcap: ${m.mcap:,.0f}  Liquidity: ${m.liquidity_usd:,.0f}  Vol/1h: ${m.volume_1h:,.0f}",
        f"Age: {m.age_seconds or (m.age_minutes or 0) * 60:.0f}s",
        f"Holders: {h.count}  Top10: {h.top10_pct:.0%}  Dev: {h.dev_pct:.0%}",
        f"Activity 5m: vol ${a.volume_5m_usd:,.0f}  buys {a.buys_5m}  sells {a.sells_5m}"
        f"  buy_ratio {a.buy_ratio_5m:.2f}",
        f"Wallet intel: safety_score={w.safety_score}  smart_buys={w.smart_wallet_buys}"
        f"  KOLs={w.kol_wallet_count}  snipers={w.sniper_wallet_count}"
        f"  bundlers={w.bundler_wallet_count}",
        f"Twitter @{tw.handle or '?'}: followers={tw.followers}  mentions/1h={tw.mentions_1h}"
        f"  growth={tw.mention_growth_pct:+.0f}%  velocity={tw.velocity_tpm:.1f} tpm"
        f"  sentiment={tw.sentiment or 'unknown'}  engagement={tw.engagement}",
        f"Telegram: {s.telegram.members} members, {s.telegram.alpha_calls} alpha calls",
        f"KOL wallets buying (5m): {s.kol_count_5m}",
    ]
    if t.pumpfun is not None:
        p = t.pumpfun
        facts.append(
            f"Pump.fun: curve={p.bonding_curve_pct:.0f}%  creator_buy={p.creator_sol_buy} SOL"
            f"  mayhem={p.is_mayhem_mode}"
        )

    return [
        system(
            "You are a memecoin analyst. Judge the qualitative narrative and hype of "
            "a Solana token from its metadata, on-chain activity, wallet intel and "
            "socials. Be skeptical: most memecoins are low quality. Heavily weight: "
            "smart-money buys (proven profitable wallets), Twitter mention growth, "
            "and buy/sell pressure in the last 5 minutes. Penalise: high sniper / "
            "bundler counts, sell pressure, dropping mention growth. Score 0..1 where "
            "1 is exceptional narrative."
        ),
        user("Token facts:\n" + "\n".join(facts)),
    ]


def neutral_narrative(state: State, exc: Exception) -> NarrativeScore:
    """Conservative fallback when the LLM is unavailable."""
    return NarrativeScore(
        score=0.0,
        sentiment="neutral",
        rug_signals=[],
        reasoning=f"LLM unavailable ({type(exc).__name__}); scored neutral.",
    )
