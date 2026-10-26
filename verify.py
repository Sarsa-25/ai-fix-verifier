import os
import subprocess
import sys
import tempfile

from compare import load_findings
from compare import load_findings, classify, verdict


def file_at(ref, path):
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Git failed:", result.stderr)
        sys.exit(1)
    return result.stdout


def save_text(text, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    return path


def scan_ref(ref, path):
    text = file_at(ref, path)
    with tempfile.TemporaryDirectory() as tmp:
        file_path = save_text(text, os.path.join(tmp, os.path.basename(path)))
        out = os.path.join(tmp, "out.json")
        subprocess.run(
            ["bandit", "-r", file_path, "-f", "json", "-o", out],
            capture_output=True,
            text=True,
        )
        if not os.path.exists(out):
            print("Bandit produced no output")
            sys.exit(1)
        return load_findings(out)

before = scan_ref("main", "vulnerable_app.py")
after = scan_ref("fix/sqli-with-secret", "vulnerable_app.py")
resolved, introduced, persisting = classify(before, after)
print(len(resolved), len(introduced), len(persisting))
print("Verdict:", verdict(resolved, introduced, persisting))