#!/usr/bin/env python3
"""Guarda um histórico compacto, auditável e sem duplicações por snapshot."""
import argparse
import datetime as dt
import json
import pathlib
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="reports/crypto/latest.json")
    parser.add_argument("--history-dir", default="data/history")
    args = parser.parse_args()
    report = json.loads(pathlib.Path(args.report).read_text(encoding="utf-8"))
    source_time = report["source_generated_at_utc"]
    month = dt.datetime.fromisoformat(source_time.replace("Z", "+00:00")).strftime("%Y-%m")
    path = pathlib.Path(args.history_dir) / f"{month}.jsonl"
    record = {
        "source_generated_at_utc": source_time,
        "analysis_generated_at_utc": report["generated_at_utc"],
        "provider": report["provider"],
        "market": report["market"],
        "method": report["method"],
        "assets": report["assets"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if path.exists():
        entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    entries = [entry for entry in entries if entry["source_generated_at_utc"] != source_time]
    entries.append(record)
    entries.sort(key=lambda entry: entry["source_generated_at_utc"])
    temp = path.with_suffix(".jsonl.tmp")
    temp.write_text("".join(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n" for entry in entries), encoding="utf-8")
    temp.replace(path)
    print(f"Histórico: {path} ({len(entries)} snapshots)", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERRO no histórico: {exc}", file=sys.stderr)
        sys.exit(1)
