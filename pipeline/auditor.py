"""
Token cost auditor — tracks every LLM call across all stages.
Renders a box-drawn table to the terminal and saves output/audit.json.
"""

import json
import os
from collections import defaultdict

from pipeline import claude_client

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "audit.json")


def build_report() -> dict:
    log = claude_client.get_usage_log()

    has_tokens = bool(log) and "input_tokens" in log[0]
    by_stage = defaultdict(
        lambda: {"cost_usd": 0.0, "calls": 0, "input_tokens": 0, "output_tokens": 0}
    )
    total = {"cost_usd": 0.0, "calls": 0, "input_tokens": 0, "output_tokens": 0}

    for entry in log:
        s = entry["stage"]
        by_stage[s]["cost_usd"] += entry["cost_usd"]
        by_stage[s]["calls"] += 1
        by_stage[s]["input_tokens"] += entry.get("input_tokens", 0)
        by_stage[s]["output_tokens"] += entry.get("output_tokens", 0)
        total["cost_usd"] += entry["cost_usd"]
        total["calls"] += 1
        total["input_tokens"] += entry.get("input_tokens", 0)
        total["output_tokens"] += entry.get("output_tokens", 0)

    # Merge Gemini quota data so Gemini-native runs show up in the audit
    gemini_stages = {}
    gemini_total_calls = 0
    try:
        from pipeline.quota import get_status

        qs = get_status()
        gemini_stages = qs.get("by_stage", {})
        gemini_total_calls = qs.get("used", 0)
    except Exception:
        pass

    if gemini_stages:
        for stage, call_count in gemini_stages.items():
            # Only add stages not already covered by claude_client log
            if stage not in by_stage:
                by_stage[stage]["calls"] = call_count
            # Always store gemini call count separately for display
        total["gemini_calls"] = gemini_total_calls
        total["gemini_stages"] = gemini_stages

    if not log and not gemini_stages:
        return {
            "stages": {},
            "total": {"cost_usd": 0.0, "calls": 0},
            "has_token_counts": False,
        }

    for s in by_stage:
        by_stage[s]["cost_usd"] = round(by_stage[s]["cost_usd"], 6)
    total["cost_usd"] = round(total["cost_usd"], 6)

    return {
        "stages": dict(by_stage),
        "total": total,
        "has_token_counts": has_tokens,
        "gemini_stages": gemini_stages,
        "gemini_total_calls": gemini_total_calls,
    }


def print_report(report: dict):
    has_tokens = report.get("has_token_counts", False)
    stages = report["stages"]
    t = report["total"]
    gemini_stages = report.get("gemini_stages", {})
    gemini_total = report.get("gemini_total_calls", 0)

    if has_tokens:
        # ── box layout ──────────────────────────────────────────────────────
        # cols: Stage | Calls | In Tokens | Out Tokens | Total Tokens | Cost $
        cols = ("Stage", "Calls", "In Tokens", "Out Tokens", "Total Tok", "Cost $")
        rows = []
        for stage, d in stages.items():
            total_tok = d["input_tokens"] + d["output_tokens"]
            rows.append(
                (
                    stage,
                    str(d["calls"]),
                    f"{d['input_tokens']:,}",
                    f"{d['output_tokens']:,}",
                    f"{total_tok:,}",
                    f"${d['cost_usd']:.4f}",
                )
            )
        grand_tok = t["input_tokens"] + t["output_tokens"]
        footer = (
            "TOTAL",
            str(t["calls"]),
            f"{t['input_tokens']:,}",
            f"{t['output_tokens']:,}",
            f"{grand_tok:,}",
            f"${t['cost_usd']:.4f}",
        )

        # compute column widths
        widths = [len(c) for c in cols]
        for row in rows + [footer]:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))

        def fmt_row(row):
            return (
                "║ "
                + " ║ ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))
                + " ║"
            )

        sep_top = "╔═" + "═╦═".join("═" * w for w in widths) + "═╗"
        sep_mid = "╠═" + "═╬═".join("═" * w for w in widths) + "═╣"
        sep_foot = "╠═" + "═╬═".join("═" * w for w in widths) + "═╣"
        sep_bot = "╚═" + "═╩═".join("═" * w for w in widths) + "═╝"

        title_width = len(sep_top) - 2
        title_line = "║" + " TOKEN USAGE AUDIT ".center(title_width) + "║"

        print()
        print(sep_top)
        print(title_line)
        print(sep_mid)
        print(fmt_row(cols))
        print(sep_mid)
        for row in rows:
            print(fmt_row(row))
        print(sep_foot)
        print(fmt_row(footer))
        print(sep_bot)
        print(
            f"  Total tokens burned: {grand_tok:,}  |  Total cost: ${t['cost_usd']:.4f}"
        )
        print()

    elif gemini_stages:
        # Gemini-native run — show per-stage call counts
        cols = ("Stage", "Gemini Calls")
        rows = [(s, str(c)) for s, c in sorted(gemini_stages.items())]
        footer = ("TOTAL", str(gemini_total))

        widths = [len(c) for c in cols]
        for row in rows + [footer]:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))

        def fmt_row(row):
            return (
                "║ "
                + " ║ ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))
                + " ║"
            )

        sep_top = "╔═" + "═╦═".join("═" * w for w in widths) + "═╗"
        sep_mid = "╠═" + "═╬═".join("═" * w for w in widths) + "═╣"
        sep_bot = "╚═" + "═╩═".join("═" * w for w in widths) + "═╝"

        title_width = len(sep_top) - 2
        title_line = "║" + " GEMINI USAGE AUDIT ".center(title_width) + "║"

        print()
        print(sep_top)
        print(title_line)
        print(sep_mid)
        print(fmt_row(cols))
        print(sep_mid)
        for row in rows:
            print(fmt_row(row))
        print(sep_mid)
        print(fmt_row(footer))
        print(sep_bot)
        print(f"  Gemini free tier — {gemini_total} API call(s) used today")
        print()

    else:
        # no token counts (claude CLI mode) — simpler table
        cols = ("Stage", "Calls", "Cost $")
        rows = [
            (s, str(d["calls"]), f"${d['cost_usd']:.4f}") for s, d in stages.items()
        ]
        footer = ("TOTAL", str(t["calls"]), f"${t['cost_usd']:.4f}")

        widths = [len(c) for c in cols]
        for row in rows + [footer]:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))

        def fmt_row(row):
            return (
                "║ "
                + " ║ ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))
                + " ║"
            )

        sep_top = "╔═" + "═╦═".join("═" * w for w in widths) + "═╗"
        sep_mid = "╠═" + "═╬═".join("═" * w for w in widths) + "═╣"
        sep_bot = "╚═" + "═╩═".join("═" * w for w in widths) + "═╝"

        title_width = len(sep_top) - 2
        title_line = "║" + " TOKEN USAGE AUDIT ".center(title_width) + "║"

        print()
        print(sep_top)
        print(title_line)
        print(sep_mid)
        print(fmt_row(cols))
        print(sep_mid)
        for row in rows:
            print(fmt_row(row))
        print(sep_mid)
        print(fmt_row(footer))
        print(sep_bot)
        print()


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
