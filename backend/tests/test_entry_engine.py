from app.ai.entry_engine import compute_entry, pick_entry_extraction
from app.ai.price_parsing import parse_zone as _parse_zone
from app.ai.vision_analysis import VisionExtraction
from app.signal_engine.engine import Direction


def _extraction(**overrides) -> VisionExtraction:
    defaults = dict(
        timeframe_label="15m", asset="EUR/USD", detected_timeframe="15m",
        current_price="1.6098", trend="BAIXA", structure_sequence="LH,LL",
        support_zone="1.6060 - 1.6065", resistance_zone="1.6095 - 1.6100",
        momentum="VENDEDORA", rsi_reading="35", macd_reading="NAO_DISPONIVEL",
        bollinger_reading="NAO_DISPONIVEL", price_action_pattern="NAO_DISPONIVEL",
        notes="NAO_DISPONIVEL",
    )
    defaults.update(overrides)
    return VisionExtraction(**defaults)


def test_parse_zone_range():
    assert _parse_zone("1.6095 - 1.6100") == (1.6095, 1.6100)


def test_parse_zone_single_number():
    assert _parse_zone("1.6098") == (1.6098, 1.6098)


def test_parse_zone_not_available():
    assert _parse_zone("NAO_DISPONIVEL") is None


def test_wait_has_no_entry():
    e = _extraction()
    assert compute_entry(Direction.WAIT, e) is None


def test_put_uses_resistance_zone():
    e = _extraction()
    entry = compute_entry(Direction.PUT, e)
    assert entry is not None
    assert entry.zone_low == 1.6095
    assert entry.zone_high == 1.6100
    assert "resistência" in entry.confirmation.lower() or "rejeição" in entry.confirmation.lower()
    assert "1.61000" in entry.invalidation or "1.6100" in entry.invalidation


def test_call_uses_support_zone():
    e = _extraction()
    entry = compute_entry(Direction.CALL, e)
    assert entry is not None
    assert entry.zone_low == 1.6060
    assert entry.zone_high == 1.6065


def test_missing_zone_returns_none():
    e = _extraction(support_zone="NAO_DISPONIVEL")
    assert compute_entry(Direction.CALL, e) is None


def test_pick_entry_extraction_chooses_smallest_timeframe():
    e15 = _extraction(timeframe_label="15m")
    e5 = _extraction(timeframe_label="5m")
    e1 = _extraction(timeframe_label="1m")
    chosen = pick_entry_extraction([e15, e5, e1])
    assert chosen.timeframe_label == "1m"


def test_pick_entry_extraction_single_image():
    e15 = _extraction(timeframe_label="15m")
    assert pick_entry_extraction([e15]).timeframe_label == "15m"
