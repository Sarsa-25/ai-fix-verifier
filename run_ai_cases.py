"""Run the verifier on the AI-generated fixes and build one summary table.

Usage (from the project folder, after build_ai_cases.py):
    python run_ai_cases.py

Each fix runs twice: strict policy, and target mode (--target).
Writes outputs/<date_time>_summary.md and .csv (title "AI fixes run").
"Expected" is the human judgement of each fix, made by reading the code
before running the tool. The reasons are in NOTES below.
"""

from datetime import datetime

from run_cases import run_case, write_summary

TOOLS = ["copilot", "gemini"]

# case: (what the input contains, target IDs)
CASES = {
    "a01": ("SQL injection", "B608"),
    "a02": ("SQL injection, two identical lines", "B608"),
    "a03": ("command injection (shell=True)", "B602"),
    "a04": ("eval on user input", "B307"),
    "a05": ("unsafe yaml.load", "B506"),
    "a06": ("unsafe pickle.loads", "B301"),
    "a07": ("SQL injection + unrelated hardcoded password", "B608"),
    "a08": ("SQL injection and eval", "B608,B307"),
}

# Human judgement per (case, tool). Default PASS: the fix removes the vulnerability safely.
EXPECTED = {
    ("a04", "gemini"): "REJECT",
    ("a08", "gemini"): "REJECT",
}
NOTES = {
    ("a03", "copilot"): "list args, shell=False, input check and timeout; Bandit still flags subprocess",
    ("a03", "gemini"): "list args, no shell; Bandit still flags subprocess",
    ("a04", "copilot"): "AST calculator with size and exponent limits",
    ("a04", "gemini"): "AST calculator without exponent limit: 9**9**9 hangs (denial of service)",
    ("a07", "copilot"): "also removed the unused password",
    ("a07", "gemini"): "also removed the unused password",
    ("a08", "copilot"): "both fixed; calculator has limits",
    ("a08", "gemini"): "both fixed, but calculator has no exponent limit (denial of service)",
}


def main():
    rows = []
    for case, (content, target) in CASES.items():
        for tool in TOOLS:
            before, after, path = f"ai/{case}-before", f"ai/{case}-{tool}", f"ai_cases/{case}.py"
            counts, strict = run_case(before, after, path)
            _, targeted = run_case(before, after, path, target)
            expected = EXPECTED.get((case, tool), "PASS")
            rows.append([
                case, tool, content, counts, strict, target, targeted, expected,
                "yes" if strict == expected else "no",
                "yes" if targeted == expected else "no",
                NOTES.get((case, tool), ""),
            ])
            print(f"{case} {tool:<8} {counts:<7} strict {strict:<7} target {targeted:<7} expected {expected}")

    total = len(rows)
    strict_ok = sum(1 for r in rows if r[8] == "yes")
    target_ok = sum(1 for r in rows if r[9] == "yes")
    footer = [
        f"Verdict agreement (strict): {strict_ok}/{total}",
        f"Verdict agreement (target mode): {target_ok}/{total}",
        "",
        "Fixes produced on 2026-11-04 by GitHub Copilot Chat (VS Code, model Auto: gpt-6-luna or "
        "mai-code-1.1-flash, see ai_experiment/log.csv) and the Gemini app (Gemini 3.6 Flash), "
        "with the prompt in ai_experiment/prompt.txt.",
    ]

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S") + "_ai"
    header = ["Case", "Tool", "Input", "Counts (r i p)", "Strict", "Target", "Target mode",
              "Expected", "Strict match", "Target match", "Note"]
    path = write_summary(stamp, "AI fixes run", header, rows, footer)

    print()
    print("\n".join(footer[:2]))
    print(f"Saved: {path}")


if __name__ == "__main__":
    main()
