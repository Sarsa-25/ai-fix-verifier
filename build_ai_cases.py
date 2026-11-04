"""Turn the AI-generated fixes in ai_experiment/ into Git branches.

Usage (from the project folder):
    python build_ai_cases.py

For each case aXX it creates:
    ai/aXX-before   ai_cases/aXX.py = ai_experiment/inputs/aXX.py
    ai/aXX-<tool>   ai_cases/aXX.py = ai_experiment/outputs/<tool>/aXX.py

The branches are built with Git plumbing commands, so the working folder,
the current branch and any open files are not touched. Running it again
rebuilds the ai/* branches from the files.
"""

import os
import subprocess
import sys

BASE = "ai_experiment"
TOOLS = ["copilot", "gemini"]
CASES = [f"a{n:02d}" for n in range(1, 9)]


def git(*args, stdin=None):
    result = subprocess.run(
        ["git", *args], input=stdin, capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        print("git", " ".join(args), "failed:", result.stderr.strip())
        sys.exit(1)
    return result.stdout.strip()


def commit_file(source, case, message):
    """Make a commit whose only file is ai_cases/<case>.py with the content of source."""
    blob = git("hash-object", "-w", "--path", f"ai_cases/{case}.py", source)
    # -z: entries end with a NUL byte, so Windows line endings cannot get into the names
    sub_tree = git("mktree", "-z", stdin=f"100644 blob {blob}\t{case}.py\0")
    root_tree = git("mktree", "-z", stdin=f"040000 tree {sub_tree}\tai_cases\0")
    return git("commit-tree", root_tree, "-m", message)


def main():
    made = 0
    for case in CASES:
        source = os.path.join(BASE, "inputs", f"{case}.py")
        commit = commit_file(source, case, f"AI case {case}: vulnerable input")
        git("branch", "-f", f"ai/{case}-before", commit)
        made += 1

        for tool in TOOLS:
            source = os.path.join(BASE, "outputs", tool, f"{case}.py")
            if not os.path.exists(source):
                print(f"missing: {source} (skipped)")
                continue
            commit = commit_file(source, case, f"AI case {case}: fix by {tool}")
            git("branch", "-f", f"ai/{case}-{tool}", commit)
            made += 1

    print(f"Done: {made} branches (ai/aXX-before, ai/aXX-copilot, ai/aXX-gemini).")


if __name__ == "__main__":
    main()
