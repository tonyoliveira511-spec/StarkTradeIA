"""
Signal Engine: combina os sub-scores (trend, structure, S/R, momentum, RSI,
MACD, volatility, price action) num score final ponderado e decide
CALL / PUT / AGUARDAR.

Os pesos são configuráveis (ver Weights) e não devem ser tratados como
definitivos — item 12 do briefing original: serão calibrados via
backtesting, não fixados por intuição.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.market_data.provider import DataQuality


class Direction(str, Enum):
    CALL = "CALL"
    PUT = "PUT"
    WAIT = "AGUARDAR"


@dataclass
class Weights:
    trend: float = 0.20
    structure: float = 0.20
    support_resistance: float = 0.15
    momentum: float = 0.15
    rsi: float = 0.10
    macd: float = 0.05
    volatility: float = 0.05
    price_action: float = 0.10

    def as_dict(self) -> dict[str, float]:
        return {
            "trend": self.trend,
            "structure": self.structure,
            "support_resistance": self.support_resistance,
            "momentum": self.momentum,
            "rsi": self.rsi,
            "macd": self.macd,
            "volatility": self.volatility,
            "price_action": self.price_action,
        }

    def validate(self) -> None:
        total = sum(self.as_dict().values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Pesos devem somar 1.0, soma atual = {total:.3f}")


@dataclass
class SubScores:
    """Cada sub-score vai de -100 (forte PUT) a +100 (forte CALL)."""

    trend: float
    structure: float
    support_resistance: float
    momentum: float
    rsi: float
    macd: float
    volatility: float
    price_action: float


@dataclass
class SignalConfig:
    weights: Weights = field(default_factory=Weights)
    min_score_to_trade: float = 60.0   # |score| abaixo disso => AGUARDAR
    min_data_quality: DataQuality = DataQuality.EXCELLENT


@dataclass(frozen=True)
class SignalResult:
    direction: Direction
    score: float          # -100..100 (sinal) usado internamente
    confidence: float     # 0..100, |score|, o que é exibido na UI
    reasons: list[str]


def compute_signal(
    sub_scores: SubScores,
    config: SignalConfig,
    data_quality: DataQuality,
    active_factors: dict[str, bool] | None = None,
) -> SignalResult:
    """
    `active_factors`: quando fornecido, indica quais fatores tinham dado
    de origem disponível (não "não disponível" na extração). Fatores
    inativos são zerados e o peso deles é redistribuído proporcionalmente
    entre os fatores ativos, em vez de simplesmente contar como 0 e
    reduzir o teto máximo de confiança alcançável. Sem isso, uma fonte de
    dados que estruturalmente nunca preenche certos campos (ex: screenshot
    sem RSI/MACD plotados) faria o sistema nunca atingir confiança alta
    mesmo com confluência perfeita nos fatores que a imagem realmente mostra.
    """
    config.weights.validate()

    if data_quality != DataQuality.EXCELLENT and data_quality != config.min_data_quality:
        return SignalResult(
            direction=Direction.WAIT,
            score=0.0,
            confidence=0.0,
            reasons=[f"Qualidade de dados insuficiente: {data_quality.value}"],
        )

    w = config.weights.as_dict()
    if active_factors:
        active_weight_sum = sum(w[k] for k, active in active_factors.items() if active)
        if active_weight_sum > 0:
            w = {
                k: (w[k] / active_weight_sum if active_factors.get(k, True) else 0.0)
                for k in w
            }
        # Se nenhum fator estiver ativo, mantém os pesos originais — o
        # score vai sair 0 de qualquer forma (todos os sub_scores serão 0).

    weighted_sum = (
        sub_scores.trend * w["trend"]
        + sub_scores.structure * w["structure"]
        + sub_scores.support_resistance * w["support_resistance"]
        + sub_scores.momentum * w["momentum"]
        + sub_scores.rsi * w["rsi"]
        + sub_scores.macd * w["macd"]
        + sub_scores.volatility * w["volatility"]
        + sub_scores.price_action * w["price_action"]
    )

    confidence = abs(weighted_sum)
    reasons: list[str] = []

    if active_factors:
        inactive = [k for k, active in active_factors.items() if not active]
        if inactive:
            reasons.append(
                f"Fatores sem dado suficiente na imagem ({', '.join(inactive)}) "
                "tiveram peso redistribuído entre os demais."
            )

    if confidence < config.min_score_to_trade:
        reasons.append(
            f"Score {confidence:.1f} abaixo do mínimo configurado "
            f"({config.min_score_to_trade}) — indicadores conflitantes ou fracos."
        )
        return SignalResult(Direction.WAIT, weighted_sum, confidence, reasons)

    direction = Direction.CALL if weighted_sum > 0 else Direction.PUT
    reasons.append(f"Score ponderado {weighted_sum:.1f} favorece {direction.value}.")
    return SignalResult(direction, weighted_sum, confidence, reasons)
