"""Run every test case through verify.py and build one summary table.

Usage (from the project folder, with .venv active):
    python run_cases.py

Each case runs twice: strict policy, and target mode (--target).
Writes outputs/<date_time>_summary.md and outputs/<date_time>_summary.csv.
Each run also leaves its normal verify.py report in outputs/.
"Expected" is the human judgement of the fix, decided before running (see the report).
"""

import csv
import os
import re
import subprocess
import sys
from datetime import datetime

OUTPUT_DIR = "outputs"

# (id, before ref, after ref, file, scenario type, target IDs, expected verdict, short title)
CASES = [
    ("C01", "main", "fix/sqli-parameterized", "vulnerable_app.py", "successful fix", "B608", "PASS", "SQLi: parameterized query"),
    ("C02", "main", "fix/sqli-with-secret", "vulnerable_app.py", "new vulnerability introduced", "B608", "REJECT", "SQLi fixed, hardcoded password added"),
    ("C03", "main", "test/comment-only", "vulnerable_app.py", "incomplete fix", "B608", "REJECT", "SQLi: only a comment added"),
    ("C04", "test/dup-before", "test/dup-partial", "vulnerable_app.py", "incomplete fix", "B608", "REJECT", "Two identical SQLi lines, one fixed"),
    ("C05", "case/C05-before", "case/C05-after", "cases/c05.py", "successful fix", "B602", "PASS", "Command injection: list args, no shell"),
    ("C06", "case/C06-before", "case/C06-after", "cases/c06.py", "incomplete fix", "B602", "REJECT", "Command injection: shlex.quote, shell kept"),
    ("C07", "case/C07-before", "case/C07-after", "cases/c07.py", "successful fix", "B307", "PASS", "eval replaced by ast.literal_eval"),
    ("C08", "case/C08-before", "case/C08-after", "cases/c08.py", "new vulnerability introduced", "B307", "REJECT", "eval replaced by exec"),
    ("C09", "case/C09-before", "case/C09-after", "cases/c09.py", "successful fix", "B506", "PASS", "yaml.load replaced by yaml.safe_load"),
    ("C10", "case/C10-before", "case/C10-after", "cases/c10.py", "incomplete fix", "B506", "REJECT", "yaml.load with Loader=yaml.Loader"),
    ("C11", "case/C11-before", "case/C11-after", "cases/c11.py", "successful fix", "B301", "PASS", "pickle replaced by json"),
    ("C12", "case/C12-before", "case/C12-after", "cases/c12.py", "unrelated pre-existing finding", "B608", "PASS", "Old unrelated password, SQLi fixed"),
    ("C13", "case/C13-before", "case/C13-after", "cases/c13.py", "multiple findings", "B608,B307", "PASS", "Two different vulns, both fixed"),
    ("C14", "case/C14-before", "case/C14-after", "cases/c14.py", "multiple findings", "B608,B307", "REJECT", "Two different vulns, one fixed"),
    ("C15", "case/C15-before", "case/C15-after", "cases/c15.py", "ambiguous comparison", "B608", "REJECT", "Variable renamed, SQLi kept"),
    ("C16", "case/C16-before", "case/C16-after", "cases/c16.py", "ambiguous comparison", "B608", "REJECT", "Vulnerable line split over 3 lines"),
    ("C17", "case/C17-before", "case/C17-after", "cases/c17.py", "ambiguous comparison", "B608", "REVIEW", "Vulnerable function deleted"),
    ("C18", "case/C18-before", "case/C18-after", "cases/c18.py", "ambiguous comparison", "B608", "REVIEW", "No findings on either side"),
    ("C19", "case/C19-before", "case/C19-after", "cases/c19.py", "ambiguous comparison", "B608", "REJECT", "nosec comment added to vulnerable line"),
]


def run_case(before, after, path, target=None):
    """Run verify.py and return (counts, verdict) read from its output."""
    command = [sys.executable, "verify.py", before, after, path]
    if target:
        command += ["--target", target]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    counts = re.search(r"Counts \(resolved introduced persisting\): (\d+) (\d+) (\d+)", result.stdout)
    found = re.search(r"Verdict: (\w+)", result.stdout)
    if result.returncode != 0 or not counts or not found:
        print(result.stdout, result.stderr)
        return "error", "ERROR"
    return " ".join(counts.groups()), found.group(1)


def write_summary(stamp, title, header, rows, footer):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, f"{stamp}_summary.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    lines = [
        f"# {title} {stamp}",
        "",
        "| " + " | ".join(header) + " |",
        "|" + "---|" * len(header),
        *["| " + " | ".join(r) + " |" for r in rows],
        "",
        *footer,
    ]
    path = os.path.join(OUTPUT_DIR, f"{stamp}_summary.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def main():
    rows = []
    for cid, before, after, path, scenario, target, expected, title in CASES:
        counts, strict = run_case(before, after, path)
        _, targeted = run_case(before, after, path, target)
        rows.append([
            cid, title, scenario, counts, strict, target, targeted, expected,
            "yes" if strict == expected else "no",
            "yes" if targeted == expected else "no",
        ])
        print(f"{cid}  {counts:<7} strict {strict:<7} target {targeted:<7} expected {expected}")

    total = len(rows)
    strict_ok = sum(1 for r in rows if r[8] == "yes")
    target_ok = sum(1 for r in rows if r[9] == "yes")
    footer = [
        f"Verdict agreement (strict): {strict_ok}/{total}",
        f"Verdict agreement (target mode): {target_ok}/{total}",
    ]

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    header = ["Case", "Title", "Scenario", "Counts (r i p)", "Strict", "Target", "Target mode",
              "Expected", "Strict match", "Target match"]
    path = write_summary(stamp, "Test run", header, rows, footer)

    print()
    print("\n".join(footer))
    print(f"Saved: {path}")


if __name__ == "__main__":
    main()
