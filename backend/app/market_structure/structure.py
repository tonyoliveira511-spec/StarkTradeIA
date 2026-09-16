"""
Market Structure Analysis: identifica swing highs/lows (HH/HL/LH/LL) e
classifica o regime atual do mercado. Entrada: lista de Candle (ordem
cronológica). Sem I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.market_data.provider import Candle


class SwingType(str, Enum):
    HH = "HH"
    HL = "HL"
    LH = "LH"
    LL = "LL"


class Regime(str, Enum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    BREAKOUT = "BREAKOUT"
    BREAKDOWN = "BREAKDOWN"
    REVERSAL = "REVERSAL"


@dataclass(frozen=True)
class Swing:
    index: int
    price: float
    type: SwingType


def find_swings(candles: list[Candle], lookback: int = 3) -> list[Swing]:
    """Detecta pivôs locais usando uma janela simples (fractal de `lookback`
    candles de cada lado). `lookback` maior = menos ruído, menos sensibilidade."""
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    n = len(candles)
    pivots_high: list[tuple[int, float]] = []
    pivots_low: list[tuple[int, float]] = []

    for i in range(lookback, n - lookback):
        window_h = highs[i - lookback : i + lookback + 1]
        window_l = lows[i - lookback : i + lookback + 1]
        if highs[i] == max(window_h):
            pivots_high.append((i, highs[i]))
        if lows[i] == min(window_l):
            pivots_low.append((i, lows[i]))

    merged = sorted(pivots_high + pivots_low, key=lambda p: p[0])
    swings: list[Swing] = []
    last_high: float | None = None
    last_low: float | None = None

    for idx, price in merged:
        is_high = (idx, price) in pivots_high
        if is_high:
            if last_high is not None:
                swings.append(
                    Swing(idx, price, SwingType.HH if price > last_high else SwingType.LH)
                )
            last_high = price
        else:
            if last_low is not None:
                swings.append(
                    Swing(idx, price, SwingType.HL if price > last_low else SwingType.LL)
                )
            last_low = price

    return swings


def classify_regime(swings: list[Swing], recent: int = 4) -> Regime:
    """Classifica o regime com base na sequência dos últimos `recent` swings."""
    if len(swings) < 2:
        return Regime.RANGE

    tail = [s.type for s in swings[-recent:]]

    up_evidence = tail.count(SwingType.HH) + tail.count(SwingType.HL)
    down_evidence = tail.count(SwingType.LH) + tail.count(SwingType.LL)

    if up_evidence >= len(tail) - 1 and up_evidence > down_evidence:
        return Regime.TREND_UP
    if down_evidence >= len(tail) - 1 and down_evidence > up_evidence:
        return Regime.TREND_DOWN

    # Alternância recente entre HH/LL sem sequência clara => range ou reversão
    if len(tail) >= 2 and tail[-1] != tail[-2]:
        prev_bias = tail[-2] in (SwingType.HH, SwingType.HL)
        curr_bias = tail[-1] in (SwingType.HH, SwingType.HL)
        if prev_bias != curr_bias:
            return Regime.REVERSAL

    return Regime.RANGE
