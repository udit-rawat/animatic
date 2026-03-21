"""
Token cost auditor — works in both CLI mode (cost_usd only) and SDK mode (full token counts).
Saves to output/audit.json after each full pipeline run.
"""
import json
import os
from collections import defaultdict

from pipeline import claude_client

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "audit.json")


def build_report() -> dict:
    log = claude_client.get_usage_log()
    if not log:
        return {"stages": {}, "total": {"cost_usd": 0.0, "calls": 0}}

    has_tokens = "input_tokens" in log[0]
    by_stage = defaultdict(lambda: {"cost_usd": 0.0, "calls": 0, "input_tokens": 0, "output_tokens": 0})
    total = {"cost_usd": 0.0, "calls": 0, "input_tokens": 0, "output_tokens": 0}

    for entry in log:
        s = entry["stage"]
        by_stage[s]["cost_usd"]       += entry["cost_usd"]
        by_stage[s]["calls"]          += 1
        by_stage[s]["input_tokens"]   += entry.get("input_tokens", 0)
        by_stage[s]["output_tokens"]  += entry.get("output_tokens", 0)
        total["cost_usd"]             += entry["cost_usd"]
        total["calls"]                += 1
        total["input_tokens"]         += entry.get("input_tokens", 0)
        total["output_tokens"]        += entry.get("output_tokens", 0)

    for s in by_stage:
        by_stage[s]["cost_usd"] = round(by_stage[s]["cost_usd"], 6)
    total["cost_usd"] = round(total["cost_usd"], 6)

    return {"stages": dict(by_stage), "total": total, "has_token_counts": has_tokens}


def print_report(report: dict):
    has_tokens = report.get("has_token_counts", False)
    print("\n" + "=" * (55 if has_tokens else 45))
    print("  TOKEN COST AUDIT")
    print("=" * (55 if has_tokens else 45))
    if has_tokens:
        print(f"  {'Stage':<15} {'Calls':>5}  {'In tok':>8}  {'Out tok':>8}  {'Cost $':>9}")
        print("  " + "-" * 51)
        for stage, d in report["stages"].items():
            print(f"  {stage:<15} {d['calls']:>5}  {d['input_tokens']:>8,}  {d['output_tokens']:>8,}  ${d['cost_usd']:>8.4f}")
        print("  " + "-" * 51)
        t = report["total"]
        print(f"  {'TOTAL':<15} {t['calls']:>5}  {t['input_tokens']:>8,}  {t['output_tokens']:>8,}  ${t['cost_usd']:>8.4f}")
    else:
        print(f"  {'Stage':<15} {'Calls':>5}  {'Cost $':>10}")
        print("  " + "-" * 35)
        for stage, d in report["stages"].items():
            print(f"  {stage:<15} {d['calls']:>5}  ${d['cost_usd']:>9.4f}")
        print("  " + "-" * 35)
        t = report["total"]
        print(f"  {'TOTAL':<15} {t['calls']:>5}  ${t['cost_usd']:>9.4f}")
    print("=" * (55 if has_tokens else 45) + "\n")


def save_report(report: dict):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Audit saved → {OUTPUT_PATH}")


def main():
    report = build_report()
    print_report(report)
    save_report(report)
    return report


if __name__ == "__main__":
    main()
