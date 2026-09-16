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

from app.ai.price_parsing import parse_price, parse_zone
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
    """Score de proximidade a suporte/resistência, baseado no preço atual
    e nas zonas extraídas — não em palavra-chave no campo de notas livre
    (isso raramente disparava, deixando esse fator quase sempre em 0
    mesmo quando a imagem tinha os dados necessários).

    Preço perto da resistência → viés de baixa (potencial rejeição).
    Preço perto do suporte → viés de alta (potencial rejeição).
    """
    price = parse_price(extraction.current_price)
    support = parse_zone(extraction.support_zone)
    resistance = parse_zone(extraction.resistance_zone)

    if price is None or (support is None and resistance is None):
        return 0.0

    support_mid = (support[0] + support[1]) / 2 if support else None
    resistance_mid = (resistance[0] + resistance[1]) / 2 if resistance else None

    if support_mid is not None and resistance_mid is not None:
        dist_to_support = abs(price - support_mid)
        dist_to_resistance = abs(price - resistance_mid)
        total = dist_to_support + dist_to_resistance
        if total == 0:
            return 0.0
        # Positivo quando mais perto do suporte (viés de alta), negativo
        # quando mais perto da resistência (viés de baixa).
        return ((dist_to_resistance - dist_to_support) / total) * 100

    # Só uma zona disponível: usa distância relativa ao preço como proxy
    # de força do viés (mais perto = sinal mais forte), com um teto para
    # não deixar o score explodir quando a zona está muito próxima.
    if support_mid is not None:
        gap = abs(price - support_mid) / max(price, 1e-9)
        return max(0.0, 60 - gap * 1000)  # decai conforme se afasta do suporte
    if resistance_mid is not None:
        gap = abs(price - resistance_mid) / max(price, 1e-9)
        return -max(0.0, 60 - gap * 1000)  # decai conforme se afasta da resistência
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


def _is_available(text: str) -> bool:
    return text.strip().upper() != NOT_AVAILABLE


def build_sub_scores(
    extractions: list[VisionExtraction],
) -> tuple[SubScores, float, dict[str, bool]]:
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

    # Um fator é "ativo" se PELO MENOS UMA das extrações usadas tinha o
    # dado de origem necessário para calculá-lo — usado pelo Signal Engine
    # para renormalizar pesos em vez de deixar fatores estruturalmente
    # ausentes (ex: RSI não plotado na Quotex) diluírem o teto de confiança.
    active_factors = {
        "trend": any(_is_available(e.trend) for e in extractions),
        "structure": any(_is_available(e.structure_sequence) for e in extractions),
        "support_resistance": any(
            parse_price(e.current_price) is not None
            and (parse_zone(e.support_zone) is not None or parse_zone(e.resistance_zone) is not None)
            for e in extractions
        ),
        "momentum": any(_is_available(e.momentum) for e in extractions),
        "rsi": any(_is_available(e.rsi_reading) for e in extractions),
        "macd": any(_is_available(e.macd_reading) for e in extractions),
        "volatility": any(_is_available(e.bollinger_reading) for e in extractions),
        "price_action": any(_is_available(e.price_action_pattern) for e in extractions),
    }

    return sub_scores, avg_availability, active_factors


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
