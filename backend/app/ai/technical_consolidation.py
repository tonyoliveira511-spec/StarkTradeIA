"""
Technical Analysis Engine (modo screenshot) — consolida uma ou mais
VisionExtraction (uma por timeframe) em SubScores para o Signal Engine
já existente, e produz uma sugestão de expiração puramente técnica
(sem estatística/ML — isso é o item 10/15 do briefing: nesta fase é
análise de confluência, não probabilidade calibrada).

Princípio de design: cada campo ausente (NOT_AVAILABLE) contribui 0
(neutro) para o sub-score correspondente — nunca é preenchido com um
palpite. Isso é o que torna AGUARDAR um resultado honesto quando a
imagem não tem informação suficiente, em vez de forçar uma direção.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.ai.vision_analysis import NOT_AVAILABLE, VisionExtraction
from app.signal_engine.engine import SubScores

TREND_SCORES = {
    "FORTE_ALTA": 100,
    "ALTA": 60,
    "LATERAL": 0,
    "BAIXA": -60,
    "FORTE_BAIXA": -100,
}

MOMENTUM_SCORES = {
    "COMPRADORA": 70,
    "VENDEDORA": -70,
    "NEUTRA": 0,
}


def _trend_score(trend: str) -> float:
    return TREND_SCORES.get(trend.strip().upper(), 0.0)


def _momentum_score(momentum: str) -> float:
    return MOMENTUM_SCORES.get(momentum.strip().upper(), 0.0)


def _structure_score(sequence: str) -> float:
    if sequence.strip().upper() == NOT_AVAILABLE:
        return 0.0
    tokens = [t.strip().upper() for t in sequence.split(",") if t.strip()]
    if not tokens:
        return 0.0
    bullish = sum(1 for t in tokens if t in ("HH", "HL"))
    bearish = sum(1 for t in tokens if t in ("LH", "LL"))
    total = bullish + bearish
    if total == 0:
        return 0.0
    return ((bullish - bearish) / total) * 100


def _rsi_score(rsi_reading: str) -> float:
    if rsi_reading.strip().upper() == NOT_AVAILABLE:
        return 0.0
    try:
        value = float(rsi_reading.replace(",", ".").strip())
    except ValueError:
        return 0.0
    if value >= 70:
        return -60
    if value <= 30:
        return 60
    return (value - 50) * 1.2


def _macd_score(macd_reading: str) -> float:
    text = macd_reading.strip().upper()
    if text == NOT_AVAILABLE:
        return 0.0
    if "ALTA" in text or "CRUZAMENTO POSITIVO" in text or "BULLISH" in text:
        return 50
    if "BAIXA" in text or "CRUZAMENTO NEGATIVO" in text or "BEARISH" in text:
        return -50
    return 0.0


def _bollinger_score(bollinger_reading: str) -> float:
    text = bollinger_reading.strip().upper()
    if text == NOT_AVAILABLE:
        return 0.0
    if "BANDA SUPERIOR" in text:
        return -30
    if "BANDA INFERIOR" in text:
        return 30
    return 0.0


def _price_action_score(pattern: str) -> float:
    text = pattern.strip().upper()
    if text == NOT_AVAILABLE:
        return 0.0
    if any(k in text for k in ("ENGULFING DE ALTA", "PIN BAR DE ALTA", "MARTELO")):
        return 60
    if any(k in text for k in ("ENGULFING DE BAIXA", "PIN BAR DE BAIXA", "ESTRELA CADENTE")):
        return -60
    return 0.0


def _support_resistance_score(extraction: VisionExtraction) -> float:
    notes = extraction.notes.strip().upper()
    if notes == NOT_AVAILABLE:
        return 0.0
    if "REJEIÇÃO DE RESISTÊNCIA" in notes or "REJEIÇÃO DA RESISTÊNCIA" in notes:
        return -50
    if "REJEIÇÃO DE SUPORTE" in notes or "REJEIÇÃO DO SUPORTE" in notes:
        return 50
    return 0.0


@dataclass(frozen=True)
class TimeframeWeight:
    label: str
    weight: float


DEFAULT_ROLE_WEIGHTS = {
    "context": 0.3,
    "structure": 0.35,
    "entry": 0.35,
}


def _assign_roles(extractions: list[VisionExtraction]) -> list[TimeframeWeight]:
    if len(extractions) == 1:
        return [TimeframeWeight(extractions[0].timeframe_label, 1.0)]

    def _minutes(label: str) -> float:
        digits = "".join(c for c in label if c.isdigit())
        return float(digits) if digits else 0.0

    ordered = sorted(extractions, key=lambda e: _minutes(e.timeframe_label), reverse=True)
    roles = ["context", "structure", "entry"][: len(ordered)]
    return [
        TimeframeWeight(e.timeframe_label, DEFAULT_ROLE_WEIGHTS[role])
        for e, role in zip(ordered, roles)
    ]


def build_sub_scores(extractions: list[VisionExtraction]) -> tuple[SubScores, float]:
    if not extractions:
        raise ValueError("Nenhuma extração fornecida")

    weights = {tw.label: tw.weight for tw in _assign_roles(extractions)}
    total_weight = sum(weights.values()) or 1.0

    def weighted(scorer) -> float:
        return sum(
            scorer(e) * weights.get(e.timeframe_label, 0.0) for e in extractions
        ) / total_weight

    trend = weighted(lambda e: _trend_score(e.trend))
    structure = weighted(lambda e: _structure_score(e.structure_sequence))
    momentum = weighted(lambda e: _momentum_score(e.momentum))
    rsi = weighted(lambda e: _rsi_score(e.rsi_reading))
    macd = weighted(lambda e: _macd_score(e.macd_reading))
    bollinger = weighted(lambda e: _bollinger_score(e.bollinger_reading))
    price_action = weighted(lambda e: _price_action_score(e.price_action_pattern))
    support_resistance = weighted(_support_resistance_score)

    sub_scores = SubScores(
        trend=trend,
        structure=structure,
        support_resistance=support_resistance,
        momentum=momentum,
        rsi=rsi,
        macd=macd,
        volatility=bollinger,
        price_action=price_action,
    )

    avg_availability = sum(e.availability_ratio() for e in extractions) / len(extractions)
    return sub_scores, avg_availability


def suggest_expiry(sub_scores: SubScores, confidence: float) -> tuple[int, str]:
    """Sugestão de expiração puramente técnica (sem estatística/ML — ver
    docs/EXPIRY_ENGINE.md). Tendência+momentum fortes e alinhados
    favorecem prazos maiores; sinal fraco favorece prazos menores."""
    trend_strength = abs(sub_scores.trend)
    momentum_strength = abs(sub_scores.momentum)
    combined_strength = (trend_strength + momentum_strength) / 2

    if confidence < 0.5:
        return 5, (
            "Poucos dados visíveis na imagem — sugerindo o prazo mais curto "
            "para limitar exposição à incerteza."
        )
    if combined_strength >= 70:
        return 15, "Tendência e momentum fortes e alinhados favorecem um prazo maior."
    if combined_strength >= 40:
        return 10, "Tendência/momentum moderados — prazo intermediário."
    return 5, "Sinal presente mas com força limitada — prazo mais curto reduz exposição."
