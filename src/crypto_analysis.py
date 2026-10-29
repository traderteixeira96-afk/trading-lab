#!/usr/bin/env python3
"""Análise determinística e educacional de candles fechados MEXC Spot."""
import argparse
import datetime as dt
import json
import math
import pathlib
import statistics
import sys

INTERVALS = ("15m", "1h", "4h")
INTERVAL_MS = {"15m": 900000, "1h": 3600000, "4h": 14400000}
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def ema(values, period):
    if len(values) < period:
        raise ValueError("Histórico insuficiente para EMA")
    result = statistics.mean(values[:period])
    alpha = 2 / (period + 1)
    for value in values[period:]:
        result = alpha * value + (1 - alpha) * result
    return result


def analyze(candles, interval, now_ms):
    if len(candles) < 60:
        raise ValueError(f"Menos de 60 candles fechados em {interval}")
    timestamps = [int(c["open_time_ms"]) for c in candles]
    if timestamps != sorted(set(timestamps)):
        raise ValueError("Candles fora de ordem ou duplicados")
    if any(b - a != INTERVAL_MS[interval] for a, b in zip(timestamps, timestamps[1:])):
        raise ValueError(f"Lacuna de candles em {interval}")
    if int(candles[-1]["close_time_ms"]) >= now_ms:
        raise ValueError("Candle ainda aberto")
    close = [float(c["close"]) for c in candles]
    high = [float(c["high"]) for c in candles]
    low = [float(c["low"]) for c in candles]
    if any(not all(map(math.isfinite, row)) for row in zip(close, high, low)):
        raise ValueError("Valores não finitos")
    if any(l <= 0 or h < max(l, c) for l, h, c in zip(low, high, close)):
        raise ValueError("OHLC inválido")
    e20 = ema(close, 20)
    e50 = ema(close, 50)
    last = close[-1]
    trs = [
        max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
        for i in range(1, len(close))
    ]
    atr14 = statistics.mean(trs[-14:])
    # Níveis históricos excluem o candle mais recente, evitando incluir o próprio fechamento.
    support = min(low[-21:-1])
    resistance = max(high[-21:-1])
    bias = "bullish" if last > e20 > e50 else "bearish" if last < e20 < e50 else "neutral"
    age_ms = now_ms - int(candles[-1]["close_time_ms"])
    # Tolerância: candle mais recente deve ter encerrado há no máximo 2 períodos.
    fresh = 0 <= age_ms <= 2 * INTERVAL_MS[interval]
    return {
        "bias": bias if fresh else "unavailable",
        "fresh": fresh,
        "last_close": round(last, 8),
        "ema20": round(e20, 8),
        "ema50": round(e50, 8),
        "atr14": round(atr14, 8),
        "atr_pct": round(100 * atr14 / last, 4),
        "support_20": round(support, 8),
        "resistance_20": round(resistance, 8),
        "last_candle_close_utc": dt.datetime.fromtimestamp(
            int(candles[-1]["close_time_ms"]) / 1000, dt.timezone.utc
        ).isoformat(),
        "candles_used": len(candles),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/crypto/latest.json")
    parser.add_argument("--output", default="reports/crypto/latest.json")
    args = parser.parse_args()
    source = json.loads(pathlib.Path(args.input).read_text(encoding="utf-8"))
    if source.get("provider") != "MEXC Spot Public API" or source.get("market") != "spot":
        raise ValueError("Fonte inesperada")
    now = dt.datetime.now(dt.timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    report = {
        "schema_version": 1,
        "generated_at_utc": now.isoformat(),
        "source_generated_at_utc": source["generated_at_utc"],
        "source_path": args.input,
        "market": "spot",
        "provider": "MEXC Spot Public API",
        "method": "EMA20/EMA50 + ATR14 + extremos das 20 velas anteriores",
        "execution_enabled": False,
        "disclaimer": "Análise descritiva, não é recomendação ou sinal de negociação.",
        "assets": {},
    }
    for symbol in SYMBOLS:
        frames = {}
        for interval in INTERVALS:
            frames[interval] = analyze(source["candles"][symbol][interval], interval, now_ms)
        available = [v["bias"] for v in frames.values() if v["bias"] != "unavailable"]
        if len(available) != 3:
            overall = "unavailable"
        elif all(b == "bullish" for b in available):
            overall = "bullish"
        elif all(b == "bearish" for b in available):
            overall = "bearish"
        else:
            overall = "mixed_or_neutral"
        report["assets"][symbol] = {"multitimeframe_bias": overall, "timeframes": frames}
        print(f"{symbol}: {overall}", flush=True)
    dest = pathlib.Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_suffix(dest.suffix + ".tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(dest)
    print(f"Relatório salvo: {dest}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERRO na análise: {exc}", file=sys.stderr)
        sys.exit(1)
