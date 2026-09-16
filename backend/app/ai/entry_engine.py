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

from dataclasses import dataclass
from typing import Optional

from app.ai.price_parsing import parse_zone
from app.ai.vision_analysis import VisionExtraction
from app.signal_engine.engine import Direction


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
        zone = parse_zone(extraction.support_zone)
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
    zone = parse_zone(extraction.resistance_zone)
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
