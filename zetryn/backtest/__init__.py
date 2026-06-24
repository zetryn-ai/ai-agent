"""Generic backtest harness: replay a graph over a historical dataset."""

from .runner import Backtester, BacktestResult, MetricsFn, RunRecord

__all__ = ["BacktestResult", "Backtester", "MetricsFn", "RunRecord"]
