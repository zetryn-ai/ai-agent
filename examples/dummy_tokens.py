"""Dummy memecoin dataset covering the full spectrum of real-world cases.

Each entry is a ``TokenInput`` plus a short human label of the scenario it models.
Used by examples to show input -> processing -> output transparently.

After the M7 enrichment the dataset also exercises the new signals:
``ActivityData`` (multi-timeframe volume / buy-sell), ``WalletIntel`` (smart money,
sniper / bundler counts, RugCheck-style safety score), ``PumpfunData`` (bonding
curve progress), and enriched Twitter mention/sentiment/velocity fields.
"""

from __future__ import annotations

from trading.schemas import (
    ActivityData,
    ContractData,
    HolderData,
    MarketData,
    PumpfunData,
    SocialData,
    TelegramData,
    TokenInput,
    TwitterData,
    WalletIntel,
)

# (label, TokenInput) — ordered from best to worst / weird edge cases.
DUMMY_TOKENS: dict[str, tuple[str, TokenInput]] = {
    "GEM": (
        "Healthy gem: deep liquidity, burned LP, distributed holders, strong socials, KOLs buying",
        TokenInput(
            mint="GEM1111111111111111111111111111111111111111",
            symbol="GEM", name="Blue Chip Meme", source="dexscreener",
            market=MarketData(
                mcap=800_000, liquidity_usd=120_000, volume_1h=400_000,
                txns_1h=2100, age_minutes=180, age_seconds=10_800, price=0.00012,
            ),
            activity=ActivityData(
                volume_1m_usd=12_000, volume_5m_usd=55_000, volume_1h_usd=400_000,
                txns_1m=60, txns_5m=280, buys_5m=180, sells_5m=100,
            ),
            holders=HolderData(count=1500, top10_pct=0.15, dev_pct=0.01),
            contract=ContractData(lp_burned=True),
            wallets=WalletIntel(
                safety_score=85, smart_wallet_buys=6, smart_wallet_count=9,
                kol_wallet_count=4, sniper_wallet_count=3, bundler_wallet_count=0,
                whale_wallet_count=2,
            ),
            social=SocialData(
                twitter=TwitterData(
                    handle="bluechipmeme", followers=25_000, tweets_1h=60,
                    mentions_1h=420, mention_growth_pct=180.0, sentiment="bullish",
                    engagement=18_000, velocity_tpm=14.0,
                ),
                telegram=TelegramData(members=8_000, alpha_calls=6), kol_count_5m=5,
                boost_amount=500, boost_total_amount=1500,
            ),
        ),
    ),
    "FRESH": (
        "Fresh launch: thin-but-ok liquidity, few holders yet, early KOL interest, no red flags",
        TokenInput(
            mint="FRESH22222222222222222222222222222222222222",
            symbol="FRSH", name="Fresh Launch", source="dexscreener",
            market=MarketData(
                mcap=60_000, liquidity_usd=18_000, volume_1h=45_000,
                txns_1h=300, age_minutes=8, age_seconds=480,
            ),
            activity=ActivityData(
                volume_1m_usd=2_500, volume_5m_usd=10_000, volume_1h_usd=45_000,
                txns_1m=18, txns_5m=70, buys_5m=45, sells_5m=25,
            ),
            holders=HolderData(count=90, top10_pct=0.35, dev_pct=0.05),
            contract=ContractData(lp_locked=True),
            wallets=WalletIntel(
                safety_score=72, smart_wallet_buys=2, smart_wallet_count=2,
                kol_wallet_count=2, sniper_wallet_count=6, bundler_wallet_count=0,
            ),
            social=SocialData(
                twitter=TwitterData(
                    handle="freshlaunch", followers=1_200, tweets_1h=15,
                    mentions_1h=40, mention_growth_pct=300.0, sentiment="bullish",
                    engagement=900, velocity_tpm=3.0,
                ),
                telegram=TelegramData(members=600, alpha_calls=2), kol_count_5m=2,
            ),
        ),
    ),
    "MID": (
        "Mediocre: passes gates but weak narrative & social — should be 'watch', not 'alert'",
        TokenInput(
            mint="MID3333333333333333333333333333333333333333",
            symbol="MID", name="Meh Coin", source="dexscreener",
            market=MarketData(
                mcap=120_000, liquidity_usd=22_000, volume_1h=30_000,
                txns_1h=200, age_minutes=240, age_seconds=14_400,
            ),
            activity=ActivityData(
                volume_1m_usd=400, volume_5m_usd=2_200, volume_1h_usd=30_000,
                txns_1m=5, txns_5m=18, buys_5m=9, sells_5m=9,
            ),
            holders=HolderData(count=300, top10_pct=0.40, dev_pct=0.03),
            contract=ContractData(lp_burned=True),
            wallets=WalletIntel(safety_score=60, smart_wallet_buys=0, kol_wallet_count=0),
            social=SocialData(
                twitter=TwitterData(
                    handle="mehcoin", followers=800, tweets_1h=3,
                    mentions_1h=8, mention_growth_pct=10.0, sentiment="neutral",
                    engagement=120, velocity_tpm=0.4,
                ),
                telegram=TelegramData(members=400, alpha_calls=0), kol_count_5m=0,
            ),
        ),
    ),
    "MINT_RUG": (
        "Rug type 1: mint authority still active (dev can print supply)",
        TokenInput(
            mint="MINT4444444444444444444444444444444444444444",
            symbol="MINT", name="Infinite Mint", source="dexscreener",
            market=MarketData(mcap=50_000, liquidity_usd=15_000, volume_1h=40_000),
            holders=HolderData(count=200, top10_pct=0.45),
            contract=ContractData(mint_authority_active=True, notes=["mint authority not revoked"]),
            wallets=WalletIntel(safety_score=15),
        ),
    ),
    "FREEZE_RUG": (
        "Rug type 2: freeze authority active (dev can freeze your tokens)",
        TokenInput(
            mint="FRZ55555555555555555555555555555555555555555",
            symbol="FRZ", name="Freeze Trap", source="dexscreener",
            market=MarketData(mcap=70_000, liquidity_usd=20_000, volume_1h=50_000),
            holders=HolderData(count=250, top10_pct=0.40),
            contract=ContractData(freeze_authority_active=True, notes=["freeze authority active"]),
            wallets=WalletIntel(safety_score=20),
        ),
    ),
    "HONEYPOT": (
        "Rug type 3: honeypot (you can buy but never sell)",
        TokenInput(
            mint="HONEY666666666666666666666666666666666666666",
            symbol="HNY", name="Honey Pot", source="dexscreener",
            market=MarketData(mcap=90_000, liquidity_usd=30_000, volume_1h=80_000),
            holders=HolderData(count=400, top10_pct=0.30),
            contract=ContractData(is_honeypot=True, notes=["sell tax 100% / honeypot"]),
            wallets=WalletIntel(safety_score=0),
        ),
    ),
    "WHALE": (
        "Concentration risk: top 10 hold 88% — one dump kills it (safety gate should fail)",
        TokenInput(
            mint="WHALE77777777777777777777777777777777777777",
            symbol="WHL", name="Whale Bag", source="dexscreener",
            market=MarketData(mcap=200_000, liquidity_usd=40_000, volume_1h=60_000),
            holders=HolderData(count=150, top10_pct=0.88, dev_pct=0.5),
            contract=ContractData(lp_burned=True),
            wallets=WalletIntel(whale_wallet_count=8, safety_score=40),
        ),
    ),
    "DUST": (
        "Illiquid dust: tiny liquidity & volume — market gate should reject",
        TokenInput(
            mint="DUST88888888888888888888888888888888888888",
            symbol="DUST", name="Dust Particle", source="dexscreener",
            market=MarketData(mcap=8_000, liquidity_usd=600, volume_1h=300),
            holders=HolderData(count=70, top10_pct=0.3),
        ),
    ),
    "GHOST": (
        "Ghost town: ok contract & holders but near-zero volume (dead) — market gate fails",
        TokenInput(
            mint="GHOST99999999999999999999999999999999999999",
            symbol="GHST", name="Ghost Town", source="dexscreener",
            market=MarketData(mcap=150_000, liquidity_usd=35_000, volume_1h=800, txns_1h=4),
            holders=HolderData(count=500, top10_pct=0.25),
            contract=ContractData(lp_burned=True),
        ),
    ),
    "HYPE_NOLIQ": (
        "Social hype but no liquidity: huge twitter/tele, KOLs, yet liquidity too thin (trap)",
        TokenInput(
            mint="HYPEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            symbol="HYPE", name="All Talk", source="dexscreener",
            market=MarketData(mcap=40_000, liquidity_usd=2_000, volume_1h=9_000),
            holders=HolderData(count=120, top10_pct=0.35),
            contract=ContractData(),
            social=SocialData(
                twitter=TwitterData(
                    handle="alltalk", followers=50_000, tweets_1h=120,
                    mentions_1h=900, mention_growth_pct=400.0, sentiment="bullish",
                    engagement=22_000, velocity_tpm=30.0,
                ),
                telegram=TelegramData(members=20_000, alpha_calls=10), kol_count_5m=8,
            ),
        ),
    ),
    "NO_SOCIAL": (
        "Solid fundamentals, zero social presence — tests social dimension at floor",
        TokenInput(
            mint="NOSOCBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            symbol="QUIET", name="Silent Type", source="dexscreener",
            market=MarketData(mcap=300_000, liquidity_usd=70_000, volume_1h=150_000, txns_1h=900),
            activity=ActivityData(
                volume_1m_usd=3_500, volume_5m_usd=15_000, volume_1h_usd=150_000,
                txns_1m=20, txns_5m=80, buys_5m=42, sells_5m=38,
            ),
            holders=HolderData(count=800, top10_pct=0.18),
            contract=ContractData(lp_burned=True),
            social=SocialData(),
        ),
    ),
    # --- New cases exercising the enriched signals -------------------------
    "BUNDLED": (
        "Bundle attack: launch dominated by coordinated bundler wallets — abort fast",
        TokenInput(
            mint="BUNDLECCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
            symbol="BNDL", name="Bundle Bait", source="pumpfun_ws",
            market=MarketData(mcap=45_000, liquidity_usd=12_000, volume_1h=80_000, age_seconds=120),
            activity=ActivityData(
                volume_1m_usd=20_000, volume_5m_usd=60_000, volume_1h_usd=80_000,
                txns_1m=80, txns_5m=300, buys_5m=240, sells_5m=60,
            ),
            holders=HolderData(count=180, top10_pct=0.62, dev_pct=0.08),
            contract=ContractData(bundled_supply=True, notes=["bundle ratio 0.55"]),
            wallets=WalletIntel(
                safety_score=35, bundler_wallet_count=12, sniper_wallet_count=18,
                smart_wallet_buys=0,
            ),
            pumpfun=PumpfunData(
                creator_wallet="CREATOR1111111111111111111111111111111111",
                creator_sol_buy=0.5, bonding_curve_pct=40.0,
            ),
            social=SocialData(),
        ),
    ),
    "DEV_REPEAT_RUG": (
        "Dev with prior rug history — instant abort regardless of optics",
        TokenInput(
            mint="DEVRUGDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",
            symbol="DRUG", name="Same Dev Different Day", source="pumpfun_ws",
            market=MarketData(mcap=30_000, liquidity_usd=8_000, volume_1h=25_000, age_seconds=60),
            holders=HolderData(count=80, top10_pct=0.55),
            contract=ContractData(dev_rug_history=True, notes=["dev rugged 3 prior tokens"]),
            wallets=WalletIntel(safety_score=18),
            pumpfun=PumpfunData(
                creator_wallet="KNOWN_RUGGER22222222222222222222222222222",
                creator_sol_buy=0.0, bonding_curve_pct=12.0,
            ),
        ),
    ),
    "SMART_MONEY": (
        "Smart money entry: heavy proven-profitable wallet buys + healthy curve",
        TokenInput(
            mint="SMARTEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE",
            symbol="SMART", name="Alpha Echo", source="dexscreener",
            market=MarketData(
                mcap=500_000, liquidity_usd=90_000, volume_1h=250_000,
                txns_1h=1400, age_minutes=45, age_seconds=2_700,
            ),
            activity=ActivityData(
                volume_1m_usd=9_000, volume_5m_usd=42_000, volume_1h_usd=250_000,
                txns_1m=45, txns_5m=200, buys_5m=160, sells_5m=40,
            ),
            holders=HolderData(count=700, top10_pct=0.22, dev_pct=0.02),
            contract=ContractData(lp_burned=True),
            wallets=WalletIntel(
                safety_score=92, smart_wallet_buys=11, smart_wallet_count=15,
                kol_wallet_count=6, sniper_wallet_count=4, bundler_wallet_count=0,
                whale_wallet_count=3,
            ),
            social=SocialData(
                twitter=TwitterData(
                    handle="alphaecho", followers=8_000, tweets_1h=40,
                    mentions_1h=220, mention_growth_pct=140.0, sentiment="bullish",
                    engagement=9_500, velocity_tpm=8.0,
                ),
                telegram=TelegramData(members=3_500, alpha_calls=4), kol_count_5m=6,
            ),
        ),
    ),
    "CURVE_NEAR_GRAD": (
        "Pump.fun near graduation (92%): urgency mode — short window of opportunity",
        TokenInput(
            mint="CURVEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
            symbol="GRAD", name="Almost There", source="pumpfun_ws",
            market=MarketData(
                mcap=180_000, liquidity_usd=55_000, volume_1h=120_000,
                txns_1h=900, age_minutes=22, age_seconds=1_320,
            ),
            activity=ActivityData(
                volume_1m_usd=8_500, volume_5m_usd=38_000, volume_1h_usd=120_000,
                txns_1m=55, txns_5m=240, buys_5m=170, sells_5m=70,
            ),
            holders=HolderData(count=520, top10_pct=0.28, dev_pct=0.03),
            contract=ContractData(),
            wallets=WalletIntel(
                safety_score=78, smart_wallet_buys=4, smart_wallet_count=6,
                kol_wallet_count=3, sniper_wallet_count=10, bundler_wallet_count=1,
            ),
            pumpfun=PumpfunData(
                creator_wallet="CREATORXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                creator_sol_buy=2.5, bonding_curve_pct=92.0, is_mayhem_mode=True,
            ),
            social=SocialData(
                twitter=TwitterData(
                    handle="almostthere", followers=4_500, tweets_1h=80,
                    mentions_1h=350, mention_growth_pct=500.0, sentiment="bullish",
                    engagement=6_800, velocity_tpm=18.0,
                ),
                telegram=TelegramData(members=2_200, alpha_calls=8), kol_count_5m=5,
            ),
        ),
    ),
    "SELL_PRESSURE": (
        "Looks ok on paper but buy/sell ratio collapsing — momentum gate flags it",
        TokenInput(
            mint="SELLGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            symbol="DUMP", name="Quiet Bleed", source="dexscreener",
            market=MarketData(
                mcap=220_000, liquidity_usd=45_000, volume_1h=85_000,
                txns_1h=600, age_minutes=120,
            ),
            activity=ActivityData(
                volume_1m_usd=1_800, volume_5m_usd=9_000, volume_1h_usd=85_000,
                txns_1m=15, txns_5m=60, buys_5m=12, sells_5m=48,
            ),
            holders=HolderData(count=600, top10_pct=0.24),
            contract=ContractData(lp_burned=True),
            wallets=WalletIntel(safety_score=70, smart_wallet_buys=0),
            social=SocialData(
                twitter=TwitterData(
                    handle="quietbleed", followers=5_000, tweets_1h=8,
                    mentions_1h=30, mention_growth_pct=-40.0, sentiment="bearish",
                    engagement=400, velocity_tpm=1.5,
                ),
            ),
        ),
    ),
}
