"""
MarketDataProvider — contrato único que o resto da aplicação usa para obter
dados de mercado. Nenhum módulo fora de `app/quotex/` deve importar código
específico da Quotex diretamente. Isso permite trocar a corretora/fonte de
dados no futuro sem tocar em indicators, market_structure, signal_engine etc.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import AsyncIterator, Optional


class MarketType(str, Enum):
    REAL = "REAL"
    OTC = "OTC"


class DataQuality(str, Enum):
    EXCELLENT = "EXCELLENT"   # feed ao vivo, latência normal
    DELAYED = "DELAYED"       # feed vivo mas com atraso/gap detectado
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class Asset:
    symbol: str                # ex: "EURUSD"
    display_name: str          # ex: "EUR/USD"
    market_type: MarketType
    payout: Optional[float]    # percentual de payout atual, se disponível
    is_open: bool


@dataclass(frozen=True)
class Candle:
    asset: str
    timeframe_seconds: int
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None


@dataclass(frozen=True)
class PriceTick:
    asset: str
    price: float
    timestamp: datetime
    quality: DataQuality


class MarketDataProvider(ABC):
    """Contrato que qualquer adapter de corretora precisa implementar.

    IMPORTANTE: esta interface é intencionalmente somente-leitura.
    Não existe (e não deve existir) nenhum método de execução de ordem
    (buy/sell/close/cancel) neste projeto.
    """

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    async def get_assets(self) -> list[Asset]:
        ...

    @abstractmethod
    async def get_candles(
        self,
        asset: str,
        timeframe_seconds: int,
        count: int,
        end_time: Optional[datetime] = None,
    ) -> list[Candle]:
        """Histórico de candles fechados. Usado para contexto e backtesting."""
        ...

    @abstractmethod
    async def subscribe_candles(
        self, asset: str, timeframe_seconds: int
    ) -> AsyncIterator[Candle]:
        """Stream de candles em tempo real (fechados e em formação)."""
        ...

    @abstractmethod
    async def get_current_price(self, asset: str) -> PriceTick:
        ...

    @abstractmethod
    async def get_payout(self, asset: str) -> Optional[float]:
        ...

    @abstractmethod
    def data_quality(self, asset: str) -> DataQuality:
        """Avaliação de qualidade do feed para este ativo, usada pelo
        Signal Engine para decidir AGUARDAR quando os dados não são confiáveis."""
        ...
