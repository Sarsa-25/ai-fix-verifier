import io
import json
import os
import sys
import tokenize
from collections import Counter


def load_findings(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["results"]


def strip_comment(line):
    """Remove a trailing Python comment, but keep '#' that is inside a string."""
    try:
        for tok in tokenize.generate_tokens(io.StringIO(line).readline):
            if tok.type == tokenize.COMMENT:
                return line[: tok.start[1]].rstrip()
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Partial line (e.g. the first line of a multi-line call): keep it as is
        pass
    return line.strip()


def finding_key(item):
    test_id = item["test_id"]
    filename = os.path.basename(item["filename"])

    code_line = ""
    for line in item["code"].split("\n"):
        number, _, text = line.partition(" ")
        if number.isdigit() and int(number) == item["line_number"]:
            code_line = strip_comment(text.strip())

    return (test_id, filename, code_line)


def verdict(resolved, introduced, persisting):
    """Strict policy: any introduced or persisting finding fails the fix."""
    if introduced or persisting:
        return "REJECT"
    elif resolved:
        return "PASS"
    else:
        return "REVIEW"


def classify(before_findings, after_findings):
    """Compare findings as multisets, so identical keys are counted, not merged.

    Example: before has the same key twice, after has it once
    -> 1 resolved, 0 introduced, 1 persisting.
    """
    before = Counter(finding_key(item) for item in before_findings)
    after = Counter(finding_key(item) for item in after_findings)

    resolved = list((before - after).elements())
    introduced = list((after - before).elements())
    persisting = list((before & after).elements())

    return resolved, introduced, persisting


if __name__ == "__main__":
    # Compare two Bandit JSON files directly (verify.py is the main entry point).
    if len(sys.argv) != 3:
        print("Usage: python compare.py <before.json> <after.json>")
        sys.exit(1)

    resolved, introduced, persisting = classify(
        load_findings(sys.argv[1]), load_findings(sys.argv[2])
    )
    print("resolved:", resolved)
    print("introduced:", introduced)
    print("persisting:", persisting)
    print("Verdict:", verdict(resolved, introduced, persisting))
