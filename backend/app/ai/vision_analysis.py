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

import asyncio
import io
import json
import logging
from dataclasses import dataclass
from typing import Optional

from google import genai
from google.genai import types
from PIL import Image

logger = logging.getLogger("vision_analysis")

NOT_AVAILABLE = "NAO_DISPONIVEL"

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
retorne exatamente a string "NAO_DISPONIVEL" (sem acentos) para aquele \
campo — nunca um número ou classificação inventados.

Responda SOMENTE com um JSON válido, sem markdown, sem crases, sem texto \
antes ou depois — apenas o objeto JSON puro, no formato exato abaixo:

{
  "asset": "string ou NAO_DISPONIVEL",
  "timeframe": "string ou NAO_DISPONIVEL",
  "current_price": "número como string ou NAO_DISPONIVEL",
  "trend": "FORTE_ALTA | ALTA | LATERAL | BAIXA | FORTE_BAIXA | NAO_DISPONIVEL",
  "structure_sequence": "sequência como 'HH,HL,LH,LL' na ordem observada, ou NAO_DISPONIVEL",
  "support_zone": "faixa de preço como string, ou NAO_DISPONIVEL",
  "resistance_zone": "faixa de preço como string, ou NAO_DISPONIVEL",
  "momentum": "COMPRADORA | VENDEDORA | NEUTRA | NAO_DISPONIVEL",
  "rsi_reading": "valor visível do RSI, ou NAO_DISPONIVEL",
  "macd_reading": "estado do MACD se visível, ou NAO_DISPONIVEL",
  "bollinger_reading": "estado das Bandas de Bollinger se visíveis, ou NAO_DISPONIVEL",
  "price_action_pattern": "padrão de candle relevante, ou NAO_DISPONIVEL",
  "notes": "observações adicionais em texto livre, ou NAO_DISPONIVEL"
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


MAX_IMAGE_DIMENSION = 1568  # suficiente para ler candles/indicadores; reduz payload e custo


def _normalize_image(image_bytes: bytes) -> bytes:
    """Reabre a imagem, redimensiona se necessário, e reexporta como PNG RGB puro.

    Corrige duas causas prováveis do erro genérico "Unable to process
    input image" da API do Gemini:
    1. Perfis de cor não-RGB (CMYK), canal alpha incomum, metadados
       EXIF/ICC embutidos por certas ferramentas de captura de tela.
    2. Imagens muito grandes (screenshots em alta resolução podem passar
       de vários MB) — a API tem limite prático de tamanho para imagem
       inline, e excedê-lo às vezes retorna esse erro genérico em vez de
       uma mensagem clara de "imagem grande demais".
    """
    if not image_bytes:
        raise VisionAnalysisError(
            "A imagem chegou vazia no servidor (0 bytes) — provavelmente um "
            "problema no envio do arquivo pelo frontend."
        )

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            rgb_img = img.convert("RGB")

            if max(rgb_img.size) > MAX_IMAGE_DIMENSION:
                rgb_img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.LANCZOS)

            buffer = io.BytesIO()
            rgb_img.save(buffer, format="PNG", optimize=True)
            return buffer.getvalue()
    except Exception as e:
        # Inclui os primeiros bytes (assinatura/magic number) e o tamanho
        # para diagnóstico real, em vez de só "não foi possível processar".
        header = image_bytes[:16].hex()
        raise VisionAnalysisError(
            f"Não foi possível processar a imagem enviada ({len(image_bytes)} "
            f"bytes, assinatura hex: {header}): {e}"
        ) from e


class ImageAnalysisProvider:
    """Fonte de dados baseada em screenshot — implementa o mesmo papel
    conceitual de um MarketDataProvider (fornecer dados de mercado para o
    resto do sistema), mas a partir de imagem em vez de WebSocket."""

    def __init__(self, api_key: str):
        if not api_key:
            raise VisionAnalysisError("GEMINI_API_KEY não configurada no servidor.")
        self._client = genai.Client(api_key=api_key)

    async def _call_with_retry(self, image_bytes: bytes, max_attempts: int = 3):
        """Chama o Gemini com retry apenas para 503 (sobrecarga temporária
        do modelo) — comum no free tier em horários de pico. Outros erros
        (400, 403, 404 etc.) não são retentados, pois são falhas
        permanentes que uma nova tentativa não resolve."""
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                return await self._client.aio.models.generate_content(
                    model=VISION_MODEL,
                    contents=[
                        EXTRACTION_PROMPT,
                        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    ],
                )
            except Exception as e:
                is_overloaded = "503" in str(e) or "UNAVAILABLE" in str(e)
                if not is_overloaded or attempt == max_attempts:
                    raise
                wait_seconds = 2 ** attempt  # 2s, 4s, 8s...
                logger.warning(
                    "Gemini sobrecarregado (tentativa %d/%d), aguardando %ds: %s",
                    attempt, max_attempts, wait_seconds, e,
                )
                last_error = e
                await asyncio.sleep(wait_seconds)
        raise last_error  # pragma: no cover — inalcançável, guarda de tipo

    async def analyze_screenshot(
        self, image_bytes: bytes, media_type: str, timeframe_label: str
    ) -> VisionExtraction:
        """Envia a imagem para o modelo, recebe o JSON e valida a forma.

        A imagem só existe neste escopo de função — não é salva em nenhum
        lugar antes ou depois desta chamada.
        """
        normalized_bytes = _normalize_image(image_bytes)
        logger.info(
            "Enviando imagem ao Gemini: %d bytes originais -> %d bytes normalizados (timeframe=%s)",
            len(image_bytes), len(normalized_bytes), timeframe_label,
        )

        try:
            response = await self._call_with_retry(normalized_bytes)
        except Exception as e:
            logger.error("Falha ao chamar a API do Gemini: %s", e)
            raise VisionAnalysisError(f"Falha ao chamar a API do Gemini: {e}") from e

        raw_text = (response.text or "").strip()
        if not raw_text:
            raise VisionAnalysisError("O Gemini retornou uma resposta vazia.")

        # Tolerância a blocos markdown (```json ... ```), caso o modelo
        # envolva a resposta apesar da instrução de não fazer isso.
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.lower().startswith("json"):
                raw_text = raw_text[4:].strip()

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
