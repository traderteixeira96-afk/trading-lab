#!/usr/bin/env python3
"""Análise descritiva de Forex e ouro; lacunas de sessão não são preenchidas."""
import datetime as dt
import json
import pathlib
import statistics
import sys
from crypto_analysis import ema
from market_structure import structure

DURATIONS = {"15m":900000,"1h":3600000,"4h":14400000}

def analyze(bars, interval, now_ms):
    if len(bars) < 60:
        raise ValueError("Histórico insuficiente")
    stamps = [int(x["open_time_ms"]) for x in bars]
    if stamps != sorted(set(stamps)):
        raise ValueError("Candles duplicados ou desordenados")
    duration = DURATIONS[interval]
    gaps = sum(b-a != duration for a,b in zip(stamps,stamps[1:]))
    if any(b-a < duration for a,b in zip(stamps,stamps[1:])):
        raise ValueError("Sobreposição de candles")
    if any(int(x["close_time_ms"]) >= now_ms for x in bars):
        raise ValueError("Candle aberto ou futuro")
    closes = [float(x["close"]) for x in bars]
    highs = [float(x["high"]) for x in bars]
    lows = [float(x["low"]) for x in bars]
    tr = [max(highs[i]-lows[i],abs(highs[i]-closes[i-1]),abs(lows[i]-closes[i-1])) for i in range(1,len(bars))]
    atr = statistics.mean(tr[-14:])
    e20,e50 = ema(closes,20),ema(closes,50)
    fresh = 0 <= now_ms-int(bars[-1]["close_time_ms"]) <= 2*duration
    bias = "bullish" if closes[-1]>e20>e50 else "bearish" if closes[-1]<e20<e50 else "neutral"
    # ATR e estrutura podem ser afetados por lacunas de fim de semana; não ocultar isso.
    return {"fresh":fresh,"bias":bias if fresh else "unavailable","last_close":closes[-1],"ema20":e20,"ema50":e50,"atr14":atr,"atr_pct":100*atr/closes[-1],"support_20":min(lows[-21:-1]),"resistance_20":max(highs[-21:-1]),"gaps_in_history":gaps,"last_candle_close_utc":dt.datetime.fromtimestamp(int(bars[-1]["close_time_ms"])/1000,dt.timezone.utc).isoformat(),"market_structure":structure(bars,atr),"candles_used":len(bars)}

def main():
    source=json.loads(pathlib.Path("data/multimarket/latest.json").read_text(encoding="utf-8"))
    if source["provider"]!="Twelve Data" or source["timezone"]!="UTC" or not source["closed_candles_only"]:
        raise ValueError("Fonte inválida")
    now=dt.datetime.now(dt.timezone.utc)
    report={"schema_version":1,"provider":"Twelve Data","market":source["market"],"generated_at_utc":now.isoformat(),"source_generated_at_utc":source["generated_at_utc"],"method":"EMA20/50, ATR14, pivôs confirmados, extremos 20 candles","execution_enabled":False,"note":"Preços indicativos; gaps de sessões podem distorcer ATR e estrutura. Sem execução.","assets":{}}
    for symbol,frames in source["candles"].items():
        values={tf:analyze(frames[tf],tf,int(now.timestamp()*1000)) for tf in DURATIONS}
        biases=[v["bias"] for v in values.values()]
        overall="unavailable" if "unavailable" in biases else biases[0] if len(set(biases))==1 and biases[0] in ("bullish","bearish") else "mixed_or_neutral"
        report["assets"][symbol]={"multitimeframe_bias":overall,"timeframes":values}
    dest=pathlib.Path("reports/multimarket/latest.json")
    dest.parent.mkdir(parents=True,exist_ok=True)
    temp=dest.with_suffix(".tmp")
    temp.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    temp.replace(dest)

if __name__=="__main__":
    try:
        main()
    except (ValueError,KeyError,OSError,TypeError) as exc:
        print(f"Falha na análise: {exc}",file=sys.stderr)
        sys.exit(1)
