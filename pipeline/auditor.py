"""
Token cost auditor.
Reads the usage log from claude_client (cost_usd per call, sourced from
the claude CLI JSON envelope) and produces a per-stage breakdown.
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

    by_stage: dict[str, dict] = defaultdict(lambda: {"cost_usd": 0.0, "calls": 0})
    total = {"cost_usd": 0.0, "calls": 0}

    for entry in log:
        s = entry["stage"]
        by_stage[s]["cost_usd"] += entry["cost_usd"]
        by_stage[s]["calls"] += 1
        total["cost_usd"] += entry["cost_usd"]
        total["calls"] += 1

    for s in by_stage:
        by_stage[s]["cost_usd"] = round(by_stage[s]["cost_usd"], 6)
    total["cost_usd"] = round(total["cost_usd"], 6)

    return {"stages": dict(by_stage), "total": total}


def print_report(report: dict):
    print("\n" + "=" * 45)
    print("  TOKEN COST AUDIT")
    print("=" * 45)
    print(f"  {'Stage':<15} {'Calls':>5}  {'Cost $':>10}")
    print("  " + "-" * 35)
    for stage, data in report["stages"].items():
        print(f"  {stage:<15} {data['calls']:>5}  ${data['cost_usd']:>9.4f}")
    print("  " + "-" * 35)
    t = report["total"]
    print(f"  {'TOTAL':<15} {t['calls']:>5}  ${t['cost_usd']:>9.4f}")
    print("=" * 45 + "\n")


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
