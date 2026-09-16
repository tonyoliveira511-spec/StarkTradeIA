"""
ImageAnalysisProvider — extrai dados estruturados de um screenshot de
gráfico usando um modelo multimodal (Claude Vision).

REGRA CENTRAL (item 3 do briefing): a IA NUNCA inventa um valor que não
está visível na imagem. Para qualquer campo que não possa ser determinado
com confiança a partir do que está desenhado no gráfico, o modelo deve
responder exatamente "NÃO DISPONÍVEL" — e este módulo trata essa string
como ausência de dado, nunca como um valor a ser usado em cálculo.

As imagens NUNCA são persistidas: chegam como bytes em memória, são
enviadas para a API da Anthropic dentro da própria requisição, e são
descartadas assim que a função retorna. Nenhum arquivo é escrito em disco
e nenhuma linha deste módulo grava a imagem em armazenamento permanente.
"""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from anthropic import AsyncAnthropic

logger = logging.getLogger("vision_analysis")

NOT_AVAILABLE = "NÃO DISPONÍVEL"

VISION_MODEL = "claude-sonnet-4-5"

EXTRACTION_PROMPT = """\
Você é um analista técnico extraindo dados de um screenshot de gráfico de \
velas (candlestick) de uma plataforma de operações digitais/binárias.

REGRA ABSOLUTA: você NUNCA deve inventar, estimar ou "chutar" um valor que \
não esteja claramente visível na imagem. Se um dado não puder ser \
determinado com confiança a partir do que está desenhado no gráfico, \
retorne exatamente a string "NÃO DISPONÍVEL" para aquele campo — nunca um \
número ou classificação inventados.

Responda SOMENTE com um JSON válido (sem markdown, sem texto antes ou \
depois), no formato exato abaixo:

{
  "asset": "string ou NÃO DISPONÍVEL",
  "timeframe": "string ou NÃO DISPONÍVEL",
  "current_price": "número como string ou NÃO DISPONÍVEL",
  "trend": "FORTE_ALTA | ALTA | LATERAL | BAIXA | FORTE_BAIXA | NÃO DISPONÍVEL",
  "structure_sequence": "sequência como 'HH,HL,LH,LL' na ordem observada, ou NÃO DISPONÍVEL",
  "support_zone": "faixa de preço como string, ou NÃO DISPONÍVEL",
  "resistance_zone": "faixa de preço como string, ou NÃO DISPONÍVEL",
  "momentum": "COMPRADORA | VENDEDORA | NEUTRA | NÃO DISPONÍVEL",
  "rsi_reading": "valor visível do RSI (se o indicador estiver plotado), ou NÃO DISPONÍVEL",
  "macd_reading": "descrição do estado do MACD se visível (ex: 'cruzamento de alta'), ou NÃO DISPONÍVEL",
  "bollinger_reading": "descrição se as bandas de Bollinger estiverem visíveis (ex: 'squeeze', 'expansão', 'preço tocando banda superior'), ou NÃO DISPONÍVEL",
  "price_action_pattern": "padrão de candle relevante visível (ex: 'engulfing de baixa', 'pin bar'), ou NÃO DISPONÍVEL",
  "notes": "observações adicionais relevantes em texto livre, ou NÃO DISPONÍVEL"
}

Analise a imagem a seguir:
"""


@dataclass(frozen=True)
class VisionExtraction:
    timeframe_label: str  # rótulo informado pelo usuário (ex: "15m"), não extraído da imagem
    asset: str
    detected_timeframe: str
    current_price: str
    trend: str
    structure_sequence: str
    support_zone: str
    resistance_zone: str
    momentum: str
    rsi_reading: str
    macd_reading: str
    bollinger_reading: str
    price_action_pattern: str
    notes: str

    def field_or_none(self, value: str) -> Optional[str]:
        return None if value.strip().upper() == NOT_AVAILABLE else value

    def availability_ratio(self) -> float:
        """Proporção de campos com dado real (não NÃO DISPONÍVEL). Usado
        para reduzir a confiança do sinal quando a imagem tem pouca
        informação legível."""
        fields = [
            self.asset, self.detected_timeframe, self.current_price, self.trend,
            self.structure_sequence, self.support_zone, self.resistance_zone,
            self.momentum, self.rsi_reading, self.macd_reading,
            self.bollinger_reading, self.price_action_pattern,
        ]
        available = sum(1 for f in fields if self.field_or_none(f) is not None)
        return available / len(fields)


class VisionAnalysisError(RuntimeError):
    pass


class ImageAnalysisProvider:
    """Fonte de dados baseada em screenshot — implementa o mesmo papel
    conceitual de um MarketDataProvider (fornecer dados de mercado para o
    resto do sistema), mas a partir de imagem em vez de WebSocket."""

    def __init__(self, api_key: str):
        if not api_key:
            raise VisionAnalysisError("ANTHROPIC_API_KEY não configurada no servidor.")
        self._client = AsyncAnthropic(api_key=api_key)

    async def analyze_screenshot(
        self, image_bytes: bytes, media_type: str, timeframe_label: str
    ) -> VisionExtraction:
        """Envia a imagem para o modelo, recebe o JSON e valida a forma.

        A imagem só existe neste escopo de função — não é salva em nenhum
        lugar antes ou depois desta chamada.
        """
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        response = await self._client.messages.create(
            model=VISION_MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": EXTRACTION_PROMPT},
                    ],
                }
            ],
        )

        raw_text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error("Resposta do modelo não é JSON válido: %s", raw_text[:300])
            raise VisionAnalysisError(
                f"O modelo não retornou JSON válido: {e}"
            ) from e

        def get_field(key: str) -> str:
            value = data.get(key, NOT_AVAILABLE)
            if not isinstance(value, str) or not value.strip():
                return NOT_AVAILABLE
            return value.strip()

        return VisionExtraction(
            timeframe_label=timeframe_label,
            asset=get_field("asset"),
            detected_timeframe=get_field("timeframe"),
            current_price=get_field("current_price"),
            trend=get_field("trend"),
            structure_sequence=get_field("structure_sequence"),
            support_zone=get_field("support_zone"),
            resistance_zone=get_field("resistance_zone"),
            momentum=get_field("momentum"),
            rsi_reading=get_field("rsi_reading"),
            macd_reading=get_field("macd_reading"),
            bollinger_reading=get_field("bollinger_reading"),
            price_action_pattern=get_field("price_action_pattern"),
            notes=get_field("notes"),
        )
