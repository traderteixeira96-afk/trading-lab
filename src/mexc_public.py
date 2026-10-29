#!/usr/bin/env python3
"""Coleta pública de candles MEXC Spot, sem chaves nem bibliotecas externas."""
import argparse
import datetime as dt
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.mexc.com/api/v3/klines"
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
INTERVALS = ("15m", "1h", "4h")
INTERVAL_MS = {"15m": 900000, "1h": 3600000, "4h": 14400000}
# A API spot MEXC utiliza 60m, não 1h, para candles de uma hora.
API_INTERVAL = {"15m": "15m", "1h": "60m", "4h": "4h"}
LIMIT = 120


def fetch(symbol, interval, now_ms):
    # Solicita mais candles para poder descartar com segurança o candle aberto.
    query = urllib.parse.urlencode({
        "symbol": symbol, "interval": API_INTERVAL[interval], "limit": LIMIT + 2
    })
    req = urllib.request.Request(
        BASE + "?" + query,
        headers={"User-Agent": "TradingLab-PublicMarketData/1.0",
                 "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            raw = json.load(response)
    except urllib.error.HTTPError as exc:
        details = exc.read(1500).decode("utf-8", errors="replace")
        raise ValueError(
            f"MEXC {symbol}/{interval} (API {API_INTERVAL[interval]}): "
            f"HTTP {exc.code}; resposta={details}"
        ) from exc
    if not isinstance(raw, list):
        raise ValueError(f"Resposta inesperada para {symbol}/{interval}: {str(raw)[:250]}")
    candles = []
    for item in raw:
        if not isinstance(item, list) or len(item) < 6:
            raise ValueError(f"Candle inválido: {symbol}/{interval}")
        open_ms = int(item[0])
        close_ms = int(item[6]) if len(item) > 6 else open_ms + INTERVAL_MS[interval] - 1
        if close_ms >= now_ms:
            continue
        candles.append({
            "open_time_ms": open_ms,
            "close_time_ms": close_ms,
            "open": str(item[1]),
            "high": str(item[2]),
            "low": str(item[3]),
            "close": str(item[4]),
            "volume_base": str(item[5]),
        })
    candles.sort(key=lambda c: c["open_time_ms"])
    if not candles:
        raise ValueError(f"Nenhum candle fechado para {symbol}/{interval}")
    if len({c["open_time_ms"] for c in candles}) != len(candles):
        raise ValueError(f"Horários duplicados para {symbol}/{interval}")
    return candles[-LIMIT:]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/crypto/latest.json")
    args = parser.parse_args()
    now_ms = int(time.time() * 1000)
    output = {
        "schema_version": 1,
        "provider": "MEXC Spot Public API",
        "market": "spot",
        "generated_at_utc": dt.datetime.fromtimestamp(
            now_ms / 1000, dt.timezone.utc
        ).isoformat(),
        "closed_candles_only": True,
        "candles": {},
    }
    for symbol in SYMBOLS:
        output["candles"][symbol] = {}
        for interval in INTERVALS:
            candles = fetch(symbol, interval, now_ms)
            output["candles"][symbol][interval] = candles
            print(f"{symbol} {interval}: {len(candles)} candles fechados", flush=True)
    path = pathlib.Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    print(f"Arquivo salvo: {path}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (urllib.error.URLError, ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"ERRO na coleta: {exc}", file=sys.stderr)
        sys.exit(1)
