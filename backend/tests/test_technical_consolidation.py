from app.ai.vision_analysis import VisionExtraction
from app.ai.technical_consolidation import build_sub_scores, suggest_expiry


def _extraction(**overrides) -> VisionExtraction:
    defaults = dict(
        timeframe_label="15m", asset="EUR/USD", detected_timeframe="15m",
        current_price="1.6000", trend="NAO_DISPONIVEL", structure_sequence="NAO_DISPONIVEL",
        support_zone="NAO_DISPONIVEL", resistance_zone="NAO_DISPONIVEL",
        momentum="NAO_DISPONIVEL", rsi_reading="NAO_DISPONIVEL", macd_reading="NAO_DISPONIVEL",
        bollinger_reading="NAO_DISPONIVEL", price_action_pattern="NAO_DISPONIVEL",
        notes="NAO_DISPONIVEL",
    )
    defaults.update(overrides)
    return VisionExtraction(**defaults)


def test_all_not_available_yields_neutral_scores_and_wait():
    e = _extraction()
    sub_scores, availability = build_sub_scores([e])
    assert sub_scores.trend == 0
    assert sub_scores.structure == 0
    assert availability == 0.25  # asset, detected_timeframe e current_price têm valor no default do helper


def test_strong_bullish_trend_and_momentum():
    e = _extraction(trend="FORTE_ALTA", momentum="COMPRADORA")
    sub_scores, _ = build_sub_scores([e])
    assert sub_scores.trend > 0
    assert sub_scores.momentum > 0


def test_structure_sequence_bearish():
    e = _extraction(structure_sequence="LH,LL,LL")
    sub_scores, _ = build_sub_scores([e])
    assert sub_scores.structure < 0


def test_structure_sequence_bullish():
    e = _extraction(structure_sequence="HH,HL,HH")
    sub_scores, _ = build_sub_scores([e])
    assert sub_scores.structure > 0


def test_rsi_overbought_and_oversold():
    overbought = _extraction(rsi_reading="80")
    oversold = _extraction(rsi_reading="20")
    over_scores, _ = build_sub_scores([overbought])
    under_scores, _ = build_sub_scores([oversold])
    assert over_scores.rsi < 0
    assert under_scores.rsi > 0


def test_multi_timeframe_confluence_increases_confidence():
    strong_put = [
        _extraction(timeframe_label="15m", trend="FORTE_BAIXA", momentum="VENDEDORA"),
        _extraction(timeframe_label="5m", trend="BAIXA", momentum="VENDEDORA",
                    structure_sequence="LH,LL", price_action_pattern="engulfing de baixa"),
        _extraction(timeframe_label="1m", trend="BAIXA", momentum="VENDEDORA"),
    ]
    sub_scores, availability = build_sub_scores(strong_put)
    assert sub_scores.trend < -30
    assert sub_scores.momentum < -30
    assert availability > 0


def test_suggest_expiry_low_confidence_gives_shortest():
    e = _extraction()
    sub_scores, availability = build_sub_scores([e])
    minutes, reason = suggest_expiry(sub_scores, availability)
    assert minutes == 5


def test_suggest_expiry_strong_signal_gives_longer():
    strong = _extraction(trend="FORTE_ALTA", momentum="COMPRADORA")
    sub_scores, availability = build_sub_scores([strong])
    minutes, _ = suggest_expiry(sub_scores, confidence=1.0)
    assert minutes >= 10
