from app.indicators.technical import atr, bollinger_bands, ema, macd, rsi


def test_ema_length_matches_input():
    values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    result = ema(values, period=3)
    assert len(result) == len(values)


def test_rsi_bounds():
    values = [float(i) for i in range(1, 40)]  # tendência de alta constante
    result = rsi(values, period=14)
    valid = [v for v in result if v == v]  # remove NaN
    assert all(0 <= v <= 100 for v in valid)
    assert valid[-1] > 50  # tendência de alta => RSI alto


def test_macd_shapes():
    values = [float(i % 7) + i * 0.1 for i in range(60)]
    result = macd(values)
    assert len(result.macd) == len(values)
    assert len(result.signal) == len(values)
    assert len(result.histogram) == len(values)


def test_bollinger_upper_above_lower():
    values = [10 + (i % 5) for i in range(30)]
    bands = bollinger_bands(values, period=10)
    for u, l in zip(bands.upper, bands.lower):
        if u == u and l == l:  # ignora NaN
            assert u >= l


def test_atr_non_negative():
    highs = [10, 11, 12, 11, 13, 14]
    lows = [9, 9.5, 10, 10, 11, 12]
    closes = [9.5, 10.5, 11, 10.5, 12, 13]
    result = atr(highs, lows, closes, period=3)
    valid = [v for v in result if v == v]
    assert all(v >= 0 for v in valid)
