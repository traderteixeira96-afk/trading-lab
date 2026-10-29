#!/usr/bin/env python3
"""Coletor Twelve Data isolado: UTC, candles fechados, sem publicar credenciais."""
import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SYMBOLS = ("EUR/USD", "GBP/USD", "USD/JPY", "XAU/USD")
INTERVALS = {"15m": ("15min", 900000), "1h": ("1h", 3600000), "4h": ("4h", 14400000)}
LIMIT = 120

def fetch(symbol, interval, key):
    api_interval, duration = INTERVALS[interval]
    params = urllib.parse.urlencode({"symbol": symbol, "interval": api_interval, "outputsize": LIMIT + 8, "timezone": "UTC", "apikey": key})
    request = urllib.request.Request("https://api.twelvedata.com/time_series?" + params, headers={"User-Agent": "TradingLab/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        raise ValueError(f"{symbol}/{interval}: HTTP {exc.code}") from None
    if not isinstance(payload.get("values"), list):
        raise ValueError(f"{symbol}/{interval}: resposta sem candles; provider_code={payload.get('code')}")
    now_ms = int(time.time() * 1000)
    candles = []
    for bar in payload["values"]:
        timestamp = dt.datetime.strptime(bar["datetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)
        open_ms = int(timestamp.timestamp() * 1000)
        if open_ms + duration > now_ms:
            continue
        o, h, l, c = [float(bar[k]) for k in ("open", "high", "low", "close")]
        if not (0 < l <= min(o,c) <= max(o,c) <= h):
            raise ValueError(f"{symbol}/{interval}: OHLC inválido")
        candles.append({"open_time_ms": open_ms, "close_time_ms": open_ms + duration - 1, "open":bar["open"], "high":bar["high"], "low":bar["low"], "close":bar["close"]})
    candles.sort(key=lambda x:x["open_time_ms"])
    if len({x["open_time_ms"] for x in candles}) != len(candles) or len(candles) < 60:
        raise ValueError(f"{symbol}/{interval}: candles duplicados ou insuficientes")
    return candles[-LIMIT:]

def main():
    key = os.getenv("TWELVE_DATA_API_KEY")
    if not key:
        raise ValueError("TWELVE_DATA_API_KEY ausente")
    result = {"schema_version":1, "provider":"Twelve Data", "market":"fx_and_metal_spot_indicative", "timezone":"UTC", "generated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(), "closed_candles_only":True, "candles":{}}
    calls = 0
    for symbol in SYMBOLS:
        result["candles"][symbol.replace("/","")] = {}
        for interval in INTERVALS:
            # Plano gratuito: no máximo 8 créditos por minuto; 6 chamadas/minuto com folga.
            if calls and calls % 6 == 0:
                time.sleep(65)
            candles = fetch(symbol, interval, key)
            result["candles"][symbol.replace("/","")][interval] = candles
            calls += 1
            print(f"{symbol} {interval}: {len(candles)} candles fechados", flush=True)
    dest = pathlib.Path("data/multimarket/latest.json")
    dest.parent.mkdir(parents=True,exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    tmp.replace(dest)

if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"Falha na coleta Twelve Data: {exc}",file=sys.stderr)
        sys.exit(1)
