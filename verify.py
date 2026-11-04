"""Verify a vulnerability fix by scanning two Git refs with Bandit.

Usage:
    python verify.py <before_ref> <after_ref> <file_path> [--target B608,B307]

Example:
    python verify.py main fix/sqli-with-secret vulnerable_app.py
    python verify.py main fix/sqli-with-secret vulnerable_app.py --target B608

Without --target the strict policy is used: any introduced or persisting
finding gives REJECT. With --target, old findings outside the target are
reported but do not reject the fix.

Each run writes a dated report and the two raw Bandit JSON files to outputs/.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime

from compare import classify, finding_key, verdict, verdict_target

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
            [sys.executable, "-m", "bandit", "-r", file_path, "--ignore-nosec", "-f", "json", "-o", out],
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


def build_report(before_ref, after_ref, path, resolved, introduced, persisting, result, labels, targets=None):
    def show(key):
        note = ""
        if targets and key[0] not in targets:
            note = "  (not targeted)"
        return f"  [{labels.get(key, '?')}] {key}{note}"

    if targets:
        policy = (
            f"Policy: target mode ({','.join(sorted(targets))}): REJECT if anything is introduced "
            "or a target finding persists; other old findings are only reported"
        )
    else:
        policy = "Policy: any introduced or persisting finding gives REJECT, at every severity"

    lines = [
        f"Date: {datetime.now().isoformat(timespec='seconds')}",
        f"Before ref: {before_ref}",
        f"After ref: {after_ref}",
        f"File: {path}",
        "",
        policy,
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


def parse_args():
    parser = argparse.ArgumentParser(description="Verify a fix by scanning two Git refs with Bandit.")
    parser.add_argument("before_ref")
    parser.add_argument("after_ref")
    parser.add_argument("file_path")
    parser.add_argument(
        "--target",
        help="comma-separated Bandit test IDs the fix should remove, for example B608,B307",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    before_ref, after_ref, path = args.before_ref, args.after_ref, args.file_path
    targets = None
    if args.target:
        targets = {t.strip().upper() for t in args.target.split(",") if t.strip()}

    before_json = scan_ref(before_ref, path)
    after_json = scan_ref(after_ref, path)

    resolved, introduced, persisting = classify(before_json["results"], after_json["results"])
    if targets:
        result = verdict_target(resolved, introduced, persisting, targets)
    else:
        result = verdict(resolved, introduced, persisting)

    labels = describe(before_json["results"])
    labels.update(describe(after_json["results"]))
    report = build_report(
        before_ref, after_ref, path, resolved, introduced, persisting, result, labels, targets
    )
    print(report, end="")

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    file_tag = os.path.splitext(os.path.basename(path))[0]
    mode_tag = "_target" if targets else ""
    prefix = os.path.join(
        OUTPUT_DIR,
        f"{stamp}_{safe_name(before_ref)}_vs_{safe_name(after_ref)}_{file_tag}{mode_tag}",
    )
    save_text(report, prefix + "_report.txt")
    save_text(json.dumps(before_json, indent=2), prefix + "_before.json")
    save_text(json.dumps(after_json, indent=2), prefix + "_after.json")
    print(f"Saved: {prefix}_report.txt")


if __name__ == "__main__":
    main()
