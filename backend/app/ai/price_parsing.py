"""Parsing compartilhado de preços e zonas a partir de texto extraído
pela Vision AI. Usado tanto pelo entry_engine quanto pela consolidação
técnica, para não duplicar a lógica de regex em dois lugares."""
from __future__ import annotations

import re
from typing import Optional

from app.ai.vision_analysis import NOT_AVAILABLE

_NUMBER_RE = re.compile(r"\d+[.,]\d+")


def parse_zone(text: str) -> Optional[tuple[float, float]]:
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


def parse_price(text: str) -> Optional[float]:
    """Extrai um único valor de preço, ex: current_price."""
    if text.strip().upper() == NOT_AVAILABLE:
        return None
    numbers = _NUMBER_RE.findall(text)
    if not numbers:
        return None
    return float(numbers[0].replace(",", "."))
