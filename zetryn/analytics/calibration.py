"""Confidence calibration: map raw model scores to empirical win rates.

An LLM's ``final_score`` is not a probability — scores cluster around a few
values and a 0.65 does not mean "wins 65% of the time". Once realized outcomes
exist (the bot's closed trades), a :class:`CalibrationMap` can be fitted from
``(score, won, source)`` records and used to translate a raw score into the
win rate actually observed for scores like it — optionally per source, since
different feeds (pumpfun, birdeye, KOL) calibrate differently.

Pure computation, no I/O: the bot exports its outcome rows and calls
:meth:`CalibrationMap.fit`; the map serializes to a plain dict so it can be
persisted and shipped like any other knowledge asset.

Method: histogram binning over [0, 1] with shrinkage. Each bin's empirical
win rate is shrunk toward the global rate by ``prior_strength`` pseudo-counts
(per-source bins shrink toward the global bin), so sparse bins degrade
gracefully toward the aggregate instead of overfitting a handful of trades.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CalibrationRecord:
    """One realized outcome: the raw score at decision time and whether it won."""

    score: float
    won: bool
    source: str | None = None


@dataclass
class BinStats:
    count: int = 0
    wins: int = 0

    def add(self, won: bool) -> None:
        self.count += 1
        if won:
            self.wins += 1


@dataclass
class CalibrationMap:
    """Score → empirical win-rate lookup, fitted from realized outcomes.

    Use :meth:`fit` to build one; :meth:`calibrate` to translate a raw score.
    ``to_dict`` / ``from_dict`` round-trip to JSON-safe plain data.
    """

    n_bins: int = 10
    prior_strength: float = 10.0
    min_source_samples: int = 20
    total: int = 0
    global_wins: int = 0
    bins: list[BinStats] = field(default_factory=list)
    source_bins: dict[str, list[BinStats]] = field(default_factory=dict)
    source_counts: dict[str, int] = field(default_factory=dict)

    # -- construction ---------------------------------------------------------

    @classmethod
    def fit(
        cls,
        records: list[CalibrationRecord],
        *,
        n_bins: int = 10,
        prior_strength: float = 10.0,
        min_source_samples: int = 20,
    ) -> CalibrationMap:
        m = cls(
            n_bins=n_bins,
            prior_strength=prior_strength,
            min_source_samples=min_source_samples,
            bins=[BinStats() for _ in range(n_bins)],
        )
        for r in records:
            idx = m._bin_index(r.score)
            m.total += 1
            if r.won:
                m.global_wins += 1
            m.bins[idx].add(r.won)
            if r.source:
                per = m.source_bins.setdefault(
                    r.source, [BinStats() for _ in range(n_bins)]
                )
                per[idx].add(r.won)
                m.source_counts[r.source] = m.source_counts.get(r.source, 0) + 1
        return m

    # -- lookup ---------------------------------------------------------------

    def calibrate(self, score: float, *, source: str | None = None) -> float:
        """Return the empirical win rate for scores like ``score``.

        Falls back gracefully: source bin (when that source has enough data)
        → global bin → global rate → the raw score itself (empty map).
        """
        if self.total == 0:
            return score
        idx = self._bin_index(score)
        global_rate = self.global_wins / self.total
        g = self.bins[idx]
        global_bin_rate = (g.wins + self.prior_strength * global_rate) / (
            g.count + self.prior_strength
        )
        if (
            source
            and source in self.source_bins
            and self.source_counts.get(source, 0) >= self.min_source_samples
        ):
            s = self.source_bins[source][idx]
            return (s.wins + self.prior_strength * global_bin_rate) / (
                s.count + self.prior_strength
            )
        return global_bin_rate

    def report(self) -> dict:
        """Per-bin raw stats for analytics dashboards / prompt tuning."""

        def rows(bins: list[BinStats]) -> list[dict]:
            width = 1.0 / self.n_bins
            return [
                {
                    "range": [round(i * width, 4), round((i + 1) * width, 4)],
                    "count": b.count,
                    "wins": b.wins,
                    "win_rate": round(b.wins / b.count, 4) if b.count else None,
                }
                for i, b in enumerate(bins)
            ]

        return {
            "total": self.total,
            "global_win_rate": round(self.global_wins / self.total, 4)
            if self.total
            else None,
            "bins": rows(self.bins),
            "sources": {
                src: {"count": self.source_counts.get(src, 0), "bins": rows(bins)}
                for src, bins in self.source_bins.items()
            },
        }

    # -- serialization --------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "n_bins": self.n_bins,
            "prior_strength": self.prior_strength,
            "min_source_samples": self.min_source_samples,
            "total": self.total,
            "global_wins": self.global_wins,
            "bins": [[b.count, b.wins] for b in self.bins],
            "source_bins": {
                src: [[b.count, b.wins] for b in bins]
                for src, bins in self.source_bins.items()
            },
            "source_counts": dict(self.source_counts),
        }

    @classmethod
    def from_dict(cls, data: dict) -> CalibrationMap:
        return cls(
            n_bins=data["n_bins"],
            prior_strength=data["prior_strength"],
            min_source_samples=data["min_source_samples"],
            total=data["total"],
            global_wins=data["global_wins"],
            bins=[BinStats(count=c, wins=w) for c, w in data["bins"]],
            source_bins={
                src: [BinStats(count=c, wins=w) for c, w in bins]
                for src, bins in data["source_bins"].items()
            },
            source_counts=dict(data["source_counts"]),
        )

    # -- internals ------------------------------------------------------------

    def _bin_index(self, score: float) -> int:
        clamped = max(0.0, min(1.0, score))
        return min(int(clamped * self.n_bins), self.n_bins - 1)
