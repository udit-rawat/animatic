"""
Token cost auditor.
Reads the usage log from claude_client and produces a per-stage
breakdown plus a grand total. Saves to output/audit.json.
"""
import json
import os
from collections import defaultdict

from pipeline import claude_client

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "audit.json")


def build_report() -> dict:
    log = claude_client.get_usage_log()
    if not log:
        return {"stages": {}, "total": {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}}

    by_stage: dict[str, dict] = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "calls": 0})
    total = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "calls": 0}

    for entry in log:
        s = entry["stage"]
        by_stage[s]["input_tokens"] += entry["input_tokens"]
        by_stage[s]["output_tokens"] += entry["output_tokens"]
        by_stage[s]["cost_usd"] += entry["cost_usd"]
        by_stage[s]["calls"] += 1
        total["input_tokens"] += entry["input_tokens"]
        total["output_tokens"] += entry["output_tokens"]
        total["cost_usd"] += entry["cost_usd"]
        total["calls"] += 1

    # Round costs
    for s in by_stage:
        by_stage[s]["cost_usd"] = round(by_stage[s]["cost_usd"], 6)
    total["cost_usd"] = round(total["cost_usd"], 6)

    return {"stages": dict(by_stage), "total": total}


def print_report(report: dict):
    print("\n" + "=" * 55)
    print("  TOKEN AUDIT")
    print("=" * 55)
    print(f"  {'Stage':<15} {'Calls':>5}  {'In tok':>8}  {'Out tok':>8}  {'Cost $':>9}")
    print("  " + "-" * 51)
    for stage, data in report["stages"].items():
        print(
            f"  {stage:<15} {data['calls']:>5}  {data['input_tokens']:>8,}  "
            f"{data['output_tokens']:>8,}  ${data['cost_usd']:>8.4f}"
        )
    print("  " + "-" * 51)
    t = report["total"]
    print(
        f"  {'TOTAL':<15} {t['calls']:>5}  {t['input_tokens']:>8,}  "
        f"{t['output_tokens']:>8,}  ${t['cost_usd']:>8.4f}"
    )
    print("=" * 55 + "\n")


def save_report(report: dict):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Audit saved to {OUTPUT_PATH}")


def main():
    report = build_report()
    print_report(report)
    save_report(report)
    return report


if __name__ == "__main__":
    main()
