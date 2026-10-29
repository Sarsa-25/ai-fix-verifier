"""Run every test case through verify.py and build one summary table.

Usage (from the project folder, with .venv active):
    python run_cases.py

Writes outputs/<date_time>_summary.md and outputs/<date_time>_summary.csv.
Each case also leaves its normal verify.py report in outputs/.
"Expected" is the human judgement of the fix, decided before running (see the report).
"""

import csv
import os
import re
import subprocess
import sys
from datetime import datetime

OUTPUT_DIR = "outputs"

# (id, before ref, after ref, file, scenario type, expected verdict, short title)
CASES = [
    ("C01", "main", "fix/sqli-parameterized", "vulnerable_app.py", "successful fix", "PASS", "SQLi: parameterized query"),
    ("C02", "main", "fix/sqli-with-secret", "vulnerable_app.py", "new vulnerability introduced", "REJECT", "SQLi fixed, hardcoded password added"),
    ("C03", "main", "test/comment-only", "vulnerable_app.py", "incomplete fix", "REJECT", "SQLi: only a comment added"),
    ("C04", "test/dup-before", "test/dup-partial", "vulnerable_app.py", "incomplete fix", "REJECT", "Two identical SQLi lines, one fixed"),
    ("C05", "case/C05-before", "case/C05-after", "cases/c05.py", "successful fix", "PASS", "Command injection: list args, no shell"),
    ("C06", "case/C06-before", "case/C06-after", "cases/c06.py", "incomplete fix", "REJECT", "Command injection: shlex.quote, shell kept"),
    ("C07", "case/C07-before", "case/C07-after", "cases/c07.py", "successful fix", "PASS", "eval replaced by ast.literal_eval"),
    ("C08", "case/C08-before", "case/C08-after", "cases/c08.py", "new vulnerability introduced", "REJECT", "eval replaced by exec"),
    ("C09", "case/C09-before", "case/C09-after", "cases/c09.py", "successful fix", "PASS", "yaml.load replaced by yaml.safe_load"),
    ("C10", "case/C10-before", "case/C10-after", "cases/c10.py", "incomplete fix", "REJECT", "yaml.load with Loader=yaml.Loader"),
    ("C11", "case/C11-before", "case/C11-after", "cases/c11.py", "successful fix", "PASS", "pickle replaced by json"),
    ("C12", "case/C12-before", "case/C12-after", "cases/c12.py", "unrelated pre-existing finding", "PASS", "Old unrelated password, SQLi fixed"),
    ("C13", "case/C13-before", "case/C13-after", "cases/c13.py", "multiple findings", "PASS", "Two different vulns, both fixed"),
    ("C14", "case/C14-before", "case/C14-after", "cases/c14.py", "multiple findings", "REJECT", "Two different vulns, one fixed"),
    ("C15", "case/C15-before", "case/C15-after", "cases/c15.py", "ambiguous comparison", "REJECT", "Variable renamed, SQLi kept"),
    ("C16", "case/C16-before", "case/C16-after", "cases/c16.py", "ambiguous comparison", "REJECT", "Vulnerable line split over 3 lines"),
    ("C17", "case/C17-before", "case/C17-after", "cases/c17.py", "ambiguous comparison", "REVIEW", "Vulnerable function deleted"),
    ("C18", "case/C18-before", "case/C18-after", "cases/c18.py", "ambiguous comparison", "REVIEW", "No findings on either side"),
    ("C19", "case/C19-before", "case/C19-after", "cases/c19.py", "ambiguous comparison", "REJECT", "nosec comment added to vulnerable line"),
]


def run_case(before, after, path):
    """Run verify.py and return (counts, verdict) read from its output."""
    result = subprocess.run(
        [sys.executable, "verify.py", before, after, path],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    counts = re.search(r"Counts \(resolved introduced persisting\): (\d+) (\d+) (\d+)", result.stdout)
    found = re.search(r"Verdict: (\w+)", result.stdout)
    if result.returncode != 0 or not counts or not found:
        print(result.stdout, result.stderr)
        return "error", "ERROR"
    return " ".join(counts.groups()), found.group(1)


def main():
    rows = []
    for cid, before, after, path, scenario, expected, title in CASES:
        counts, got = run_case(before, after, path)
        match = "yes" if got == expected else "no"
        rows.append([cid, title, scenario, counts, got, expected, match])
        print(f"{cid}  {counts:<7} {got:<7} expected {expected:<7} {match}")

    agree = sum(1 for r in rows if r[6] == "yes")
    total = len(rows)

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    header = ["Case", "Title", "Scenario", "Counts (r i p)", "Tool verdict", "Expected", "Match"]

    with open(os.path.join(OUTPUT_DIR, f"{stamp}_summary.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    lines = [
        f"# Test run {stamp}",
        "",
        "| " + " | ".join(header) + " |",
        "|" + "---|" * len(header),
        *["| " + " | ".join(r) + " |" for r in rows],
        "",
        f"Verdict agreement: {agree}/{total}",
    ]
    with open(os.path.join(OUTPUT_DIR, f"{stamp}_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nVerdict agreement: {agree}/{total}")
    print(f"Saved: {OUTPUT_DIR}/{stamp}_summary.md")


if __name__ == "__main__":
    main()
