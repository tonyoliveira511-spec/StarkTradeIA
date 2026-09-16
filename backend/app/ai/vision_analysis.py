"""
ImageAnalysisProvider — extrai dados estruturados de um screenshot de
gráfico usando o Gemini (Google), aproveitando o free tier multimodal.

REGRA CENTRAL (item 3 do briefing): a IA NUNCA inventa um valor que não
está visível na imagem. Para qualquer campo que não possa ser determinado
com confiança a partir do que está desenhado no gráfico, o modelo deve
responder exatamente "NÃO DISPONÍVEL" — e este módulo trata essa string
como ausência de dado, nunca como um valor a ser usado em cálculo.

As imagens NUNCA são persistidas: chegam como bytes em memória, são
enviadas para a API do Gemini dentro da própria requisição, e são
descartadas assim que a função retorna. Nenhum arquivo é escrito em disco.

Usa response_mime_type="application/json" com um response_schema
explícito — o Gemini valida a estrutura antes de devolver, o que é mais
confiável do que só pedir "responda em JSON" no texto do prompt.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from google import genai
from google.genai import types

logger = logging.getLogger("vision_analysis")

NOT_AVAILABLE = "NÃO DISPONÍVEL"

# Modelo multimodal atual do Google AI Studio. NOTA: o Google descontinua
# versões de modelo com alguma frequência para contas novas (aconteceu com
# o gemini-2.5-flash, usado na primeira versão deste arquivo). Se este
# modelo também for descontinuado no futuro, o próprio erro da API
# geralmente informa o nome do substituto recomendado — atualizar aqui.
VISION_MODEL = "gemini-3.6-flash"

EXTRACTION_PROMPT = """\
Você é um analista técnico extraindo dados de um screenshot de gráfico de \
velas (candlestick) de uma plataforma de operações digitais/binárias.

REGRA ABSOLUTA: você NUNCA deve inventar, estimar ou "chutar" um valor que \
não esteja claramente visível na imagem. Se um dado não puder ser \
determinado com confiança a partir do que está desenhado no gráfico, \
retorne exatamente a string "NÃO DISPONÍVEL" para aquele campo — nunca um \
número ou classificação inventados.

Analise a imagem a seguir e preencha os campos do schema fornecido.
"""

# Schema estrito: o Gemini é forçado a preencher exatamente estes campos,
# todos como string (para permitir o valor sentinela "NÃO DISPONÍVEL"
# mesmo em campos conceitualmente numéricos, como current_price/rsi_reading).
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "asset": {"type": "STRING"},
        "timeframe": {"type": "STRING"},
        "current_price": {"type": "STRING"},
        "trend": {
            "type": "STRING",
            "enum": ["FORTE_ALTA", "ALTA", "LATERAL", "BAIXA", "FORTE_BAIXA", NOT_AVAILABLE],
        },
        "structure_sequence": {"type": "STRING"},
        "support_zone": {"type": "STRING"},
        "resistance_zone": {"type": "STRING"},
        "momentum": {
            "type": "STRING",
            "enum": ["COMPRADORA", "VENDEDORA", "NEUTRA", NOT_AVAILABLE],
        },
        "rsi_reading": {"type": "STRING"},
        "macd_reading": {"type": "STRING"},
        "bollinger_reading": {"type": "STRING"},
        "price_action_pattern": {"type": "STRING"},
        "notes": {"type": "STRING"},
    },
    "required": [
        "asset", "timeframe", "current_price", "trend", "structure_sequence",
        "support_zone", "resistance_zone", "momentum", "rsi_reading",
        "macd_reading", "bollinger_reading", "price_action_pattern", "notes",
    ],
}


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
            raise VisionAnalysisError("GEMINI_API_KEY não configurada no servidor.")
        self._client = genai.Client(api_key=api_key)

    async def analyze_screenshot(
        self, image_bytes: bytes, media_type: str, timeframe_label: str
    ) -> VisionExtraction:
        """Envia a imagem para o modelo, recebe o JSON e valida a forma.

        A imagem só existe neste escopo de função — não é salva em nenhum
        lugar antes ou depois desta chamada.
        """
        try:
            response = await self._client.aio.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    EXTRACTION_PROMPT,
                    types.Part.from_bytes(data=image_bytes, mime_type=media_type),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                ),
            )
        except Exception as e:
            logger.error("Falha ao chamar a API do Gemini: %s", e)
            raise VisionAnalysisError(f"Falha ao chamar a API do Gemini: {e}") from e

        raw_text = (response.text or "").strip()
        if not raw_text:
            raise VisionAnalysisError("O Gemini retornou uma resposta vazia.")

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error("Resposta do modelo não é JSON válido: %s", raw_text[:300])
            raise VisionAnalysisError(f"O modelo não retornou JSON válido: {e}") from e

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
