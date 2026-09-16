from app.market_data.provider import DataQuality
from app.signal_engine.engine import Direction, SignalConfig, SubScores, compute_signal


def _neutral_scores() -> SubScores:
    return SubScores(
        trend=5, structure=-4, support_resistance=3, momentum=0,
        rsi=-2, macd=1, volatility=0, price_action=2,
    )


def _strong_put_scores() -> SubScores:
    return SubScores(
        trend=-90, structure=-85, support_resistance=-80, momentum=-70,
        rsi=-60, macd=-50, volatility=-40, price_action=-75,
    )


def test_conflicting_indicators_result_in_wait():
    result = compute_signal(_neutral_scores(), SignalConfig(), DataQuality.EXCELLENT)
    assert result.direction == Direction.WAIT


def test_strong_bearish_alignment_gives_put():
    result = compute_signal(_strong_put_scores(), SignalConfig(), DataQuality.EXCELLENT)
    assert result.direction == Direction.PUT
    assert result.confidence >= SignalConfig().min_score_to_trade


def test_poor_data_quality_forces_wait_even_with_strong_signal():
    result = compute_signal(_strong_put_scores(), SignalConfig(), DataQuality.UNAVAILABLE)
    assert result.direction == Direction.WAIT


def test_weights_must_sum_to_one():
    from app.signal_engine.engine import Weights
    bad = Weights(trend=0.5, structure=0.5, support_resistance=0.5,
                   momentum=0, rsi=0, macd=0, volatility=0, price_action=0)
    try:
        bad.validate()
        assert False, "deveria ter levantado ValueError"
    except ValueError:
        pass
