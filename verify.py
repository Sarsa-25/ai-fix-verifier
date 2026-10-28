"""Verify a vulnerability fix by scanning two Git refs with Bandit.

Usage:
    python verify.py <before_ref> <after_ref> <file_path>

Example:
    python verify.py main fix/sqli-with-secret vulnerable_app.py

Each run writes a dated report and the two raw Bandit JSON files to outputs/.
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime

from compare import classify, finding_key, verdict

OUTPUT_DIR = "outputs"


def file_at(ref, path):
    """Return the content of `path` as it exists at Git ref `ref`."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        print(f"Git failed for {ref}:{path}:", result.stderr.strip())
        sys.exit(1)
    return result.stdout


def save_text(text, path):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def scan_ref(ref, path):
    """Scan the file at `ref` with Bandit and return the full Bandit JSON."""
    text = file_at(ref, path)
    with tempfile.TemporaryDirectory() as tmp:
        file_path = save_text(text, os.path.join(tmp, os.path.basename(path)))
        out = os.path.join(tmp, "out.json")
        # sys.executable -m bandit uses the Bandit installed in the active .venv
        subprocess.run(
            [sys.executable, "-m", "bandit", "-r", file_path, "-f", "json", "-o", out],
            capture_output=True,
            text=True,
        )
        if not os.path.exists(out):
            print(f"Bandit produced no output for {ref}")
            sys.exit(1)
        with open(out, encoding="utf-8") as f:
            return json.load(f)


def safe_name(ref):
    """Make a Git ref usable in a file name (fix/sqli -> fix-sqli)."""
    return ref.replace("/", "-").replace("\\", "-")


def describe(findings):
    """Map each finding key to 'severity/confidence' as reported by Bandit."""
    labels = {}
    for item in findings:
        labels[finding_key(item)] = f"{item['issue_severity']}/{item['issue_confidence']}"
    return labels


def build_report(before_ref, after_ref, path, resolved, introduced, persisting, result, labels):
    def show(key):
        return f"  [{labels.get(key, '?')}] {key}"

    lines = [
        f"Date: {datetime.now().isoformat(timespec='seconds')}",
        f"Before ref: {before_ref}",
        f"After ref: {after_ref}",
        f"File: {path}",
        "",
        "Policy: any introduced or persisting finding gives REJECT, at every severity",
        f"Counts (resolved introduced persisting): {len(resolved)} {len(introduced)} {len(persisting)}",
        "",
        "Resolved:",
        *[show(key) for key in resolved],
        "Introduced:",
        *[show(key) for key in introduced],
        "Persisting:",
        *[show(key) for key in persisting],
        "",
        f"Verdict: {result}",
    ]
    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) != 4:
        print("Usage: python verify.py <before_ref> <after_ref> <file_path>")
        sys.exit(1)

    before_ref, after_ref, path = sys.argv[1], sys.argv[2], sys.argv[3]

    before_json = scan_ref(before_ref, path)
    after_json = scan_ref(after_ref, path)

    resolved, introduced, persisting = classify(before_json["results"], after_json["results"])
    result = verdict(resolved, introduced, persisting)

    labels = describe(before_json["results"])
    labels.update(describe(after_json["results"]))
    report = build_report(
        before_ref, after_ref, path, resolved, introduced, persisting, result, labels
    )
    print(report, end="")

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    prefix = os.path.join(
        OUTPUT_DIR, f"{stamp}_{safe_name(before_ref)}_vs_{safe_name(after_ref)}"
    )
    save_text(report, prefix + "_report.txt")
    save_text(json.dumps(before_json, indent=2), prefix + "_before.json")
    save_text(json.dumps(after_json, indent=2), prefix + "_after.json")
    print(f"Saved: {prefix}_report.txt")


if __name__ == "__main__":
    main()
