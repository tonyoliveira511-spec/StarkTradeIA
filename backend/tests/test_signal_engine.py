from app.market_data.provider import DataQuality
from app.signal_engine.engine import Direction, SignalConfig, SubScores, Weights, compute_signal


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


def _partial_data_put_scores() -> SubScores:
    """Sub-scores fortes de PUT nos fatores disponíveis, mas RSI/MACD/
    volatilidade zerados por ausência de dado (não por indicador neutro).
    Cenário real: screenshot só com candles, sem indicadores plotados."""
    return SubScores(
        trend=-100, structure=-33.3, support_resistance=-75, momentum=-70,
        rsi=0, macd=0, volatility=0, price_action=-60,
    )


def test_without_active_factors_missing_data_caps_confidence():
    """Sem informar quais fatores tinham dado real, o sistema não consegue
    distinguir 'indicador neutro' de 'indicador ausente' — o teto de
    confiança fica artificialmente baixo mesmo com forte confluência."""
    result = compute_signal(_partial_data_put_scores(), SignalConfig(), DataQuality.EXCELLENT)
    assert result.direction == Direction.WAIT


def test_active_factors_renormalizes_and_unlocks_confidence():
    """Informando que RSI/MACD/volatilidade não tinham dado de origem
    (não que eram neutros), o peso deles é redistribuído e a mesma
    confluência agora gera um sinal de verdade."""
    active = {
        "trend": True, "structure": True, "support_resistance": True,
        "momentum": True, "rsi": False, "macd": False,
        "volatility": False, "price_action": True,
    }
    result = compute_signal(
        _partial_data_put_scores(), SignalConfig(), DataQuality.EXCELLENT,
        active_factors=active,
    )
    assert result.direction == Direction.PUT
    assert result.confidence >= SignalConfig().min_score_to_trade
    assert any("peso redistribuído" in r for r in result.reasons)


def test_all_factors_active_behaves_like_default():
    """Quando todos os fatores estão ativos, informar active_factors não
    deve mudar o resultado em relação a não informar nada."""
    all_active = {k: True for k in Weights().as_dict()}
    scores = _strong_put_scores()
    result_default = compute_signal(scores, SignalConfig(), DataQuality.EXCELLENT)
    result_explicit = compute_signal(
        scores, SignalConfig(), DataQuality.EXCELLENT, active_factors=all_active
    )
    assert result_default.direction == result_explicit.direction
    assert round(result_default.confidence, 4) == round(result_explicit.confidence, 4)
