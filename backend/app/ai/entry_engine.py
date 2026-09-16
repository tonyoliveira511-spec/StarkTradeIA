"""
Entry Engine — determina zona de entrada, condição de confirmação e de
invalidação a partir da extração visual e da direção do sinal.

Princípio (item 9 do briefing original): o ponto de entrada natural em
price action é a própria zona de suporte/resistência, não um valor
arbitrário perto do preço atual. Para CALL, a entrada é a região de
suporte (compra na rejeição); para PUT, a região de resistência (venda
na rejeição). Se a zona correspondente não estiver disponível na
extração, não inventamos uma — retornamos None nesse campo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.ai.vision_analysis import NOT_AVAILABLE, VisionExtraction
from app.signal_engine.engine import Direction

_NUMBER_RE = re.compile(r"\d+[.,]\d+")


def _parse_zone(text: str) -> Optional[tuple[float, float]]:
    """Extrai um intervalo de preço de uma string como '111.193 - 111.200'.
    Se só houver um número, trata como um único ponto (low == high)."""
    if text.strip().upper() == NOT_AVAILABLE:
        return None
    numbers = [float(n.replace(",", ".")) for n in _NUMBER_RE.findall(text)]
    if len(numbers) >= 2:
        return (min(numbers[0], numbers[1]), max(numbers[0], numbers[1]))
    if len(numbers) == 1:
        return (numbers[0], numbers[0])
    return None


@dataclass(frozen=True)
class EntryInfo:
    zone_low: float
    zone_high: float
    confirmation: str
    invalidation: str


def compute_entry(direction: Direction, extraction: VisionExtraction) -> Optional[EntryInfo]:
    """Retorna None quando a direção é AGUARDAR (não há entrada a marcar)
    ou quando a extração não tem a zona necessária para a direção."""
    if direction == Direction.WAIT:
        return None

    if direction == Direction.CALL:
        zone = _parse_zone(extraction.support_zone)
        if zone is None:
            return None
        low, high = zone
        return EntryInfo(
            zone_low=low,
            zone_high=high,
            confirmation="Rejeição do suporte com fechamento de alta na região.",
            invalidation=f"Rompimento confirmado abaixo de {low:.5f}.",
        )

    # PUT
    zone = _parse_zone(extraction.resistance_zone)
    if zone is None:
        return None
    low, high = zone
    return EntryInfo(
        zone_low=low,
        zone_high=high,
        confirmation="Rejeição da resistência com fechamento de baixa na região.",
        invalidation=f"Rompimento confirmado acima de {high:.5f}.",
    )


def pick_entry_extraction(extractions: list[VisionExtraction]) -> VisionExtraction:
    """Escolhe a extração de menor timeframe (mais granular) para calcular
    a zona de entrada — é o gráfico onde entrada/confirmação fazem mais
    sentido, mesmo quando outros timeframes deram o contexto/estrutura."""
    def _minutes(label: str) -> float:
        digits = "".join(c for c in label if c.isdigit())
        return float(digits) if digits else float("inf")

    return min(extractions, key=lambda e: _minutes(e.timeframe_label))
