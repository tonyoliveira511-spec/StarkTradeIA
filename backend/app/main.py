from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.ai.entry_engine import compute_entry, pick_entry_extraction
from app.ai.technical_consolidation import build_sub_scores, suggest_expiry
from app.ai.vision_analysis import ImageAnalysisProvider, VisionAnalysisError, VisionExtraction
from app.core.config import get_settings
from app.signal_engine.engine import Direction, SignalConfig, compute_signal
from app.market_data.provider import DataQuality

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("starktrade_ia")

app = FastAPI(
    title="StarkTrade IA",
    description=(
        "Análise técnica de screenshots de gráfico via Vision AI — "
        "somente leitura. Não envia, executa ou automatiza operações. "
        "Imagens não são armazenadas: existem só durante o processamento."
    ),
    version="0.2.0-mvp-screenshot",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

MAX_IMAGES = 3
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8MB por imagem
ALLOWED_MEDIA_TYPES = {"image/png", "image/jpeg", "image/webp"}


def get_vision_provider() -> ImageAnalysisProvider:
    return ImageAnalysisProvider(api_key=settings.gemini_api_key)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "read_only": True, "stores_images": False}


@app.post("/api/analyze")
async def analyze(
    timeframes: list[str] = Form(...),
    images: list[UploadFile] = File(...),
) -> dict:
    """
    Recebe 1-3 screenshots + o rótulo de timeframe de cada um (ex: "15m"),
    extrai dados visuais, consolida em sub-scores e retorna CALL/PUT/AGUARDAR.

    As imagens são lidas em memória (`await image.read()`), usadas apenas
    para a chamada à Vision AI, e descartadas ao final da função — nunca
    escritas em disco, nunca enviadas a armazenamento permanente.
    """
    if len(images) != len(timeframes):
        raise HTTPException(400, "Número de imagens e de timeframes deve ser igual.")
    if not (1 <= len(images) <= MAX_IMAGES):
        raise HTTPException(400, f"Envie de 1 a {MAX_IMAGES} imagens.")

    try:
        provider = get_vision_provider()
    except VisionAnalysisError as e:
        raise HTTPException(503, str(e))

    async def analyze_one(image: UploadFile, timeframe_label: str) -> VisionExtraction:
        if image.content_type not in ALLOWED_MEDIA_TYPES:
            raise HTTPException(400, f"Tipo de imagem não suportado: {image.content_type}")

        image_bytes = await image.read()
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(400, f"Imagem '{image.filename}' excede {MAX_IMAGE_BYTES // 1024 // 1024}MB.")

        try:
            return await provider.analyze_screenshot(
                image_bytes=image_bytes,
                media_type=image.content_type,
                timeframe_label=timeframe_label,
            )
        except VisionAnalysisError as e:
            logger.error("Falha na análise visual: %s", e)
            raise HTTPException(502, f"Falha ao analisar imagem: {e}")
        finally:
            # `image_bytes` sai de escopo aqui e é coletado pelo GC — em
            # nenhum momento foi escrito em disco ou enviado a storage.
            del image_bytes

    # Chamadas em paralelo — cada imagem já demora alguns segundos na Vision
    # AI; com 1 imagem não muda nada, mas com 2-3 evita esperar em série
    # (era a causa da lentidão percebida pelo usuário com o modo multi-timeframe).
    extractions: list[VisionExtraction] = await asyncio.gather(
        *(analyze_one(image, tf) for image, tf in zip(images, timeframes))
    )

    sub_scores, availability = build_sub_scores(extractions)

    config = SignalConfig()
    signal = compute_signal(sub_scores, config, data_quality=DataQuality.EXCELLENT)

    expiry_minutes, expiry_reason = suggest_expiry(sub_scores, availability)

    entry = None
    if signal.direction != Direction.WAIT:
        entry_extraction = pick_entry_extraction(extractions)
        entry = compute_entry(signal.direction, entry_extraction)

    return {
        "direction": signal.direction.value,
        "score": round(signal.confidence, 1),
        "reasons": signal.reasons,
        "expiry_suggestion_minutes": expiry_minutes if signal.direction != Direction.WAIT else None,
        "expiry_reason": expiry_reason,
        "data_availability": round(availability * 100, 1),
        "entry": (
            {
                "zone_low": entry.zone_low,
                "zone_high": entry.zone_high,
                "confirmation": entry.confirmation,
                "invalidation": entry.invalidation,
            }
            if entry
            else None
        ),
        "extractions": [
            {
                "timeframe_label": e.timeframe_label,
                "asset": e.asset,
                "detected_timeframe": e.detected_timeframe,
                "current_price": e.current_price,
                "trend": e.trend,
                "structure_sequence": e.structure_sequence,
                "support_zone": e.support_zone,
                "resistance_zone": e.resistance_zone,
                "momentum": e.momentum,
                "rsi_reading": e.rsi_reading,
                "macd_reading": e.macd_reading,
                "bollinger_reading": e.bollinger_reading,
                "price_action_pattern": e.price_action_pattern,
                "notes": e.notes,
            }
            for e in extractions
        ],
    }
