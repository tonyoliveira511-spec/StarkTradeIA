"""
Indicadores técnicos calculados a partir de séries de candles.

Funções puras, sem I/O e sem dependência de Quotex/banco — recebem listas de
preços/candles e devolvem números. Isso torna o módulo trivialmente testável
e reutilizável tanto no motor em tempo real quanto no backtesting (mesma
função, mesmo resultado, sem look-ahead bias por construção).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def ema(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        return [float("nan")] * len(values)
    arr = np.asarray(values, dtype=float)
    alpha = 2 / (period + 1)
    out = np.empty_like(arr)
    out[: period - 1] = float("nan")
    out[period - 1] = arr[:period].mean()
    for i in range(period, len(arr)):
        out[i] = alpha * arr[i] + (1 - alpha) * out[i - 1]
    return out.tolist()


def rsi(values: list[float], period: int = 14) -> list[float]:
    arr = np.asarray(values, dtype=float)
    if len(arr) <= period:
        return [float("nan")] * len(arr)
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.zeros_like(arr)
    avg_loss = np.zeros_like(arr)
    avg_gain[period] = gains[:period].mean()
    avg_loss[period] = losses[:period].mean()

    for i in range(period + 1, len(arr)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period

    out = np.full_like(arr, np.nan)
    for i in range(period, len(arr)):
        if avg_loss[i] == 0:
            out[i] = 100.0
        else:
            rs = avg_gain[i] / avg_loss[i]
            out[i] = 100 - (100 / (1 + rs))
    return out.tolist()


@dataclass(frozen=True)
class MACDResult:
    macd: list[float]
    signal: list[float]
    histogram: list[float]


def macd(
    values: list[float], fast: int = 12, slow: int = 26, signal_period: int = 9
) -> MACDResult:
    ema_fast = np.asarray(ema(values, fast))
    ema_slow = np.asarray(ema(values, slow))
    macd_line = ema_fast - ema_slow
    valid = ~np.isnan(macd_line)
    signal_line = np.full_like(macd_line, np.nan)
    if valid.sum() >= signal_period:
        clean = macd_line[valid]
        sig = ema(clean.tolist(), signal_period)
        signal_line[valid] = sig
    histogram = macd_line - signal_line
    return MACDResult(
        macd=macd_line.tolist(),
        signal=signal_line.tolist(),
        histogram=histogram.tolist(),
    )


@dataclass(frozen=True)
class BollingerResult:
    upper: list[float]
    middle: list[float]
    lower: list[float]
    bandwidth: list[float]  # (upper-lower)/middle — usado p/ squeeze/expansão


def bollinger_bands(
    values: list[float], period: int = 20, std_dev: float = 2.0
) -> BollingerResult:
    arr = np.asarray(values, dtype=float)
    middle = np.full_like(arr, np.nan)
    upper = np.full_like(arr, np.nan)
    lower = np.full_like(arr, np.nan)
    for i in range(period - 1, len(arr)):
        window = arr[i - period + 1 : i + 1]
        mean = window.mean()
        std = window.std(ddof=0)
        middle[i] = mean
        upper[i] = mean + std_dev * std
        lower[i] = mean - std_dev * std
    with np.errstate(invalid="ignore", divide="ignore"):
        bandwidth = (upper - lower) / middle
    return BollingerResult(
        upper=upper.tolist(),
        middle=middle.tolist(),
        lower=lower.tolist(),
        bandwidth=bandwidth.tolist(),
    )


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float]:
    h, l, c = (np.asarray(x, dtype=float) for x in (highs, lows, closes))
    n = len(c)
    tr = np.zeros(n)
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    out = np.full(n, np.nan)
    if n > period:
        out[period] = tr[1 : period + 1].mean()
        for i in range(period + 1, n):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out.tolist()
