"""Estrutura de mercado baseada apenas em candles fechados, sem look-ahead."""
import statistics

def structure(candles, atr):
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    closes = [float(c["close"]) for c in candles]
    n = len(candles)
    if n < 60 or atr <= 0:
        raise ValueError("Histórico ou ATR insuficiente")
    # Pivô confirmado exige duas velas à direita: últimos 2 candles nunca viram pivôs.
    tops = [i for i in range(2, n - 2) if highs[i] > max(highs[i-2:i]) and highs[i] > max(highs[i+1:i+3])]
    bottoms = [i for i in range(2, n - 2) if lows[i] < min(lows[i-2:i]) and lows[i] < min(lows[i+1:i+3])]
    def direction(indices, values):
        if len(indices) < 2:
            return "insufficient_pivots"
        a, b = values[indices[-2]], values[indices[-1]]
        return "higher" if b > a else "lower" if b < a else "equal"
    top_trend = direction(tops, highs)
    bottom_trend = direction(bottoms, lows)
    if top_trend == bottom_trend == "higher":
        market_structure = "higher_highs_higher_lows"
    elif top_trend == bottom_trend == "lower":
        market_structure = "lower_highs_lower_lows"
    else:
        market_structure = "mixed_or_undetermined"
    # Rompimento somente por fechamento acima/abaixo dos extremos das 20 velas anteriores.
    prior_high = max(highs[-21:-1])
    prior_low = min(lows[-21:-1])
    if closes[-1] > prior_high:
        breakout = "close_above_20_bar_high"
    elif closes[-1] < prior_low:
        breakout = "close_below_20_bar_low"
    else:
        breakout = "none"
    # Reteste requer evento de rompimento confirmado e candles posteriores;
    # não presumimos reteste apenas por tocar nível histórico.
    # Volatilidade: ATR atual versus mediana dos 40 ATRs móveis de 14 períodos.
    trs = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(1,n)]
    rolling = [statistics.mean(trs[i-14:i]) for i in range(14,len(trs)+1)]
    baseline = statistics.median(rolling[-40:])
    ratio = atr / baseline if baseline > 0 else 1.0
    regime = "elevated" if ratio >= 1.5 else "compressed" if ratio <= 0.7 else "normal"
    return {
        "pivot_rule": "2_left_2_right_confirmed",
        "confirmed_swing_highs": len(tops),
        "confirmed_swing_lows": len(bottoms),
        "last_confirmed_swing_high": highs[tops[-1]] if tops else None,
        "last_confirmed_swing_low": lows[bottoms[-1]] if bottoms else None,
        "swing_high_direction": top_trend,
        "swing_low_direction": bottom_trend,
        "structure": market_structure,
        "breakout": breakout,
        "retest": "not_evaluated",
        "volatility_regime": regime,
        "atr_vs_baseline_ratio": round(ratio,4),
        "volatility_baseline": "median_of_last_40_rolling_ATR14",
    }
