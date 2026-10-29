#!/usr/bin/env python3
"""Diagnóstico isolado da cobertura Twelve Data; nunca imprime a API key."""
import datetime as dt
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

SYMBOLS = ("EUR/USD", "GBP/USD", "USD/JPY", "XAU/USD", "XAG/USD", "WTI/USD")
URL = "https://api.twelvedata.com/time_series"


def main():
    key = os.environ.get("TWELVE_DATA_API_KEY")
    if not key:
        raise SystemExit("Segredo TWELVE_DATA_API_KEY ausente")
    results = {}
    for symbol in SYMBOLS:
        params = urllib.parse.urlencode({"symbol": symbol, "interval": "15min", "outputsize": 5, "timezone": "UTC", "apikey": key})
        req = urllib.request.Request(URL + "?" + params, headers={"User-Agent": "TradingLab-coverage-probe/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                payload = json.load(response)
            values = payload.get("values")
            if isinstance(values, list) and values:
                results[symbol] = {"status": "available", "returned_bars": len(values), "latest_bar_time": values[0].get("datetime"), "timezone": payload.get("meta", {}).get("exchange_timezone"), "meta_timezone": payload.get("meta", {}).get("timezone"), "meta_symbol": payload.get("meta", {}).get("symbol"), "latest_bar_is_after_probe_utc_if_naive_utc": values[0].get("datetime", "") > dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
            else:
                results[symbol] = {"status": "unavailable", "provider_code": payload.get("code"), "reason": "API não retornou candles"}
        except urllib.error.HTTPError as exc:
            results[symbol] = {"status": "http_error", "http_status": exc.code}
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            results[symbol] = {"status": "request_failed", "error_type": type(exc).__name__}
        print(f"{symbol}: {results[symbol]['status']}", flush=True)
    report = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider": "Twelve Data",
        "purpose": "coverage_probe_only",
        "interval": "15min",
        "requested_timezone": "UTC",
        "note": "Disponibilidade pontual, sem validação de integridade, horário de fechamento ou direito de uso em produção.",
        "results": results,
    }
    target = pathlib.Path("reports/providers/twelvedata_probe.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
