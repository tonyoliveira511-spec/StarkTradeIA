"""
QuotexAdapter — única camada do sistema que conhece a Quotex.

⚠️ NÃO OFICIAL: não existe API pública/oficial da Quotex. Esta camada
encapsula a biblioteca `pyquotex` (github.com/cleitonleonel/pyquotex),
que se comunica via engenharia reversa do WebSocket privado da corretora.
Ver docs/QUOTEX_ADAPTER.md para riscos e trade-offs.

Métodos e assinaturas confirmados por introspecção direta da classe
`pyquotex.stable_api.Quotex` (sem necessidade de credenciais) — não por
documentação, que diverge entre forks/versões.

REGRA ABSOLUTA: este arquivo (e todo o pacote app/quotex/) NUNCA deve conter
métodos de compra, venda, abertura ou fechamento de ordem, nem qualquer
forma de automação de operação. Somente leitura de dados de mercado.
`buy`, `sell_option`, `open_pending` etc. existem na biblioteca subjacente
mas NUNCA são chamados ou expostos por este adapter.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from pyquotex.stable_api import Quotex

from app.market_data.provider import (
    Asset,
    Candle,
    DataQuality,
    MarketDataProvider,
    MarketType,
    PriceTick,
)

logger = logging.getLogger("quotex_adapter")

STALE_TICK_THRESHOLD_SECONDS = 5.0
DISCONNECT_QUALITY_AFTER_SECONDS = 20.0


class QuotexConnectionError(RuntimeError):
    """Erro de conexão/autenticação com a Quotex."""


def _infer_market_type(asset_code: str) -> MarketType:
    return MarketType.OTC if asset_code.lower().endswith("_otc") else MarketType.REAL


class QuotexAdapter(MarketDataProvider):
    def __init__(self, email: str, password: str, *, is_demo: bool = True):
        self._email = email
        self._password = password
        self._is_demo = is_demo
        self._client = Quotex(email=email, password=password, lang="pt")
        self._last_tick_at: dict[str, datetime] = {}
        self._connected = False
        self._streaming_assets: set[str] = set()

    async def connect(self) -> None:
        # Define o modo ANTES de conectar, para nunca operar acidentalmente
        # sobre a conta real sem confirmação explícita do chamador.
        self._client.set_account_mode("PRACTICE" if self._is_demo else "REAL")

        check, reason = await self._client.connect()
        if not check:
            raise QuotexConnectionError(reason or "Falha desconhecida ao conectar")
        self._connected = True
        logger.info("Conectado à Quotex (modo %s)", "PRACTICE" if self._is_demo else "REAL")

    async def disconnect(self) -> None:
        if self._connected:
            await self._client.close()
        self._connected = False

    async def get_assets(self) -> list[Asset]:
        # get_all_assets() -> dict[str, str]: mapeia nome de exibição/código
        # interno. A biblioteca não expõe status aberto/fechado nem payout
        # nesse método — isso vem de check_asset_open() por ativo, então
        # combinamos os dois para montar o objeto Asset completo.
        raw_assets = await self._client.get_all_assets()

        assets: list[Asset] = []
        for asset_code, display_name in raw_assets.items():
            try:
                open_info, details = await self._client.check_asset_open(asset_code)
                is_open = bool(open_info) if open_info is not None else False
            except Exception:
                # Se checar o status de um ativo específico falhar, marcamos
                # como fechado em vez de assumir aberto — mais seguro para
                # o Signal Engine, que não deve operar sobre incerteza.
                is_open = False

            payout: Optional[float] = None
            try:
                payout_result = await self._client.get_payout_by_asset(asset_code)
                if isinstance(payout_result, (int, float)):
                    payout = float(payout_result)
                elif isinstance(payout_result, dict):
                    for v in payout_result.values():
                        if isinstance(v, (int, float)):
                            payout = float(v)
                            break
            except Exception:
                payout = None

            assets.append(
                Asset(
                    symbol=asset_code,
                    display_name=display_name,
                    market_type=_infer_market_type(asset_code),
                    payout=payout,
                    is_open=is_open,
                )
            )
        return assets

    async def get_candles(
        self,
        asset: str,
        timeframe_seconds: int,
        count: int,
        end_time: Optional[datetime] = None,
    ) -> list[Candle]:
        end_from_time = end_time.timestamp() if end_time else None
        offset_seconds = count * timeframe_seconds

        raw_candles = await self._client.get_candles(
            asset=asset,
            end_from_time=end_from_time,
            offset=offset_seconds,
            period=timeframe_seconds,
        )
        if not raw_candles:
            return []

        candles: list[Candle] = []
        for c in raw_candles:
            raw_time = c.get("time")
            if isinstance(raw_time, (int, float)):
                open_time = datetime.fromtimestamp(raw_time, tz=timezone.utc)
            elif isinstance(raw_time, str):
                open_time = datetime.fromisoformat(raw_time)
            else:
                continue

            candles.append(
                Candle(
                    asset=asset,
                    timeframe_seconds=timeframe_seconds,
                    open_time=open_time,
                    open=float(c.get("open", c.get("o", 0.0))),
                    high=float(c.get("high", c.get("max", c.get("h", 0.0)))),
                    low=float(c.get("low", c.get("min", c.get("l", 0.0)))),
                    close=float(c.get("close", c.get("c", 0.0))),
                    volume=c.get("volume"),
                )
            )
        return candles

    async def subscribe_candles(
        self, asset: str, timeframe_seconds: int
    ) -> AsyncIterator[Candle]:
        # start_candles_stream inicia o streaming no client subjacente, mas
        # não devolve um async generator nativo — a biblioteca entrega
        # candles via callback/estado interno. Fazemos polling curto sobre
        # get_candles como ponte simples até confirmar (com dados reais) o
        # mecanismo de callback exato desta versão.
        self._client.start_candles_stream(asset=asset, period=timeframe_seconds)
        self._streaming_assets.add(asset)
        last_open_time: Optional[datetime] = None

        try:
            while asset in self._streaming_assets:
                candles = await self.get_candles(asset, timeframe_seconds, count=2)
                if candles:
                    latest = candles[-1]
                    self._last_tick_at[asset] = datetime.now(timezone.utc)
                    if latest.open_time != last_open_time:
                        last_open_time = latest.open_time
                        yield latest
                await asyncio.sleep(min(timeframe_seconds, 2))
        finally:
            self._streaming_assets.discard(asset)
            self._client.stop_candles_stream(asset)

    async def get_current_price(self, asset: str) -> PriceTick:
        realtime = await self._client.get_realtime_price(asset)
        if not realtime:
            raise QuotexConnectionError(f"Sem preço em tempo real para {asset}")

        latest = realtime[-1]
        price = float(latest.get("price", latest.get("close", 0.0)))
        self._last_tick_at[asset] = datetime.now(timezone.utc)

        return PriceTick(
            asset=asset,
            price=price,
            timestamp=datetime.now(timezone.utc),
            quality=self.data_quality(asset),
        )

    async def get_payout(self, asset: str) -> Optional[float]:
        result = await self._client.get_payout_by_asset(asset)
        if isinstance(result, (int, float)):
            return float(result)
        if isinstance(result, dict):
            for v in result.values():
                if isinstance(v, (int, float)):
                    return float(v)
        return None

    def data_quality(self, asset: str) -> DataQuality:
        last = self._last_tick_at.get(asset)
        if last is None:
            return DataQuality.UNAVAILABLE
        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        if elapsed > DISCONNECT_QUALITY_AFTER_SECONDS:
            return DataQuality.UNAVAILABLE
        if elapsed > STALE_TICK_THRESHOLD_SECONDS:
            return DataQuality.DELAYED
        return DataQuality.EXCELLENT
