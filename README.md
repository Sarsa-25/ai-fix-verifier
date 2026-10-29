# AI Fix Verifier

A small tool that checks whether a security fix (for example one suggested by an AI assistant) **removes the vulnerability without adding a new one**.

It scans the code before and after the fix with [Bandit](https://bandit.readthedocs.io/), compares the findings, and gives a verdict: **PASS**, **REJECT** or **REVIEW**.

> Master's project (non-thesis) in Cybersecurity.

---

## Why

AI tools can now propose fixes for vulnerabilities. A proposed fix can:

- really fix the problem,
- fix it only partly, or
- fix it and introduce a different vulnerability.

Reading every change by hand does not scale. This project automates a first, repeatable check.

## How it works

```
code before the fix (Git ref) ──► Bandit ──┐
                                           ├──► compare findings ──► verdict
code after the fix  (Git ref) ──► Bandit ──┘
```

Each finding is identified by **(Bandit test ID, file name, source line)** and placed in one group:

| Group | Meaning |
|---|---|
| **resolved** | in the before scan, not in the after scan |
| **introduced** | not in the before scan, new in the after scan |
| **persisting** | in both scans |

Verdict policy (strict):

| Condition | Verdict |
|---|---|
| any introduced or persisting finding | **REJECT** |
| only resolved findings | **PASS** |
| no findings on either side | **REVIEW** |

The policy ignores Bandit severity on purpose: Bandit rates a hardcoded password (B105) as LOW, yet a leaked secret is a real risk.

### Matching details

- **Comments are ignored.** A trailing comment (for example `# safe now`) does not change a finding's identity. Comments are removed with Python's `tokenize`, so a `#` inside a string is kept.
- **Duplicates are counted.** Findings are compared as multisets (`collections.Counter`), so fixing one of two identical vulnerable lines shows as 1 resolved + 1 persisting.
- **`# nosec` is ignored.** Bandit runs with `--ignore-nosec`, so a fix cannot hide a vulnerability by suppressing the warning.

## Setup

Tested with Python 3.14 and Bandit 1.9.4 on Windows.

```powershell
git clone https://github.com/Sarsa-25/ai-fix-verifier.git
cd ai-fix-verifier

# get every test-case branch as a local branch
git fetch --update-head-ok origin "+refs/heads/*:refs/heads/*"

python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Check one fix:

```powershell
python verify.py <before_ref> <after_ref> <file_path>
python verify.py main fix/sqli-with-secret vulnerable_app.py
```

Example output:

```
Policy: any introduced or persisting finding gives REJECT, at every severity
Counts (resolved introduced persisting): 1 1 0

Resolved:
  [MEDIUM/LOW] ('B608', 'vulnerable_app.py', 'query = f"SELECT * FROM users WHERE name = \'{username}\'"')
Introduced:
  [LOW/MEDIUM] ('B105', 'vulnerable_app.py', 'DB_PASSWORD = "FAKE_PASSWORD_12345"')
Persisting:

Verdict: REJECT
```

`[MEDIUM/LOW]` is Bandit's severity/confidence. Each run saves a report and both raw Bandit JSON files in `outputs/`, named with the date and the two refs.

Run the whole test set:

```powershell
python run_cases.py
```

This writes `outputs/<date_time>_summary.md` and `.csv`.

Check a fix in another repository: run the tool from inside that repository, with full paths to this project's Python and `verify.py`. Run it once per changed Python file.

```powershell
cd C:\path\to\other-project
git diff --name-only <before_ref> <after_ref> -- "*.py"
C:\path\to\ai-fix-verifier\.venv\Scripts\python C:\path\to\ai-fix-verifier\verify.py <before_ref> <after_ref> path/to/file.py
```

For a single fix commit, use `<commit>~1` (the commit before it) as the before ref. The reports are saved in `outputs/` inside that repository.

Other scripts:

| Script | Purpose |
|---|---|
| `compare.py` | Matching and verdict logic. Can also compare two Bandit JSON files: `python compare.py before.json after.json` |
| `build_cases.py` | Created the Git branches for cases C05–C19 (already done; refuses to run twice) |

## Test set and results

19 hand-built cases covering six scenario types. Every case is a pair of Git refs, so each result can be re-run.

| Case | Scenario | Change | Tool | Expected |
|---|---|---|---|---|
| C01 | successful fix | SQL injection → parameterized query | PASS | PASS |
| C02 | new vulnerability introduced | SQLi fixed, hardcoded password added | REJECT | REJECT |
| C03 | incomplete fix | only a comment added to the vulnerable line | REJECT | REJECT |
| C04 | incomplete fix | two identical SQLi lines, one fixed | REJECT | REJECT |
| C05 | successful fix | command injection → list arguments, no shell | REJECT | PASS |
| C06 | incomplete fix | `shlex.quote` added, `shell=True` kept | REJECT | REJECT |
| C07 | successful fix | `eval` → `ast.literal_eval` | PASS | PASS |
| C08 | new vulnerability introduced | `eval` → `exec` | REJECT | REJECT |
| C09 | successful fix | `yaml.load` → `yaml.safe_load` | PASS | PASS |
| C10 | incomplete fix | `yaml.load(..., Loader=yaml.Loader)` | REJECT | REJECT |
| C11 | successful fix | `pickle` → `json` | PASS | PASS |
| C12 | unrelated pre-existing finding | old hardcoded password, SQLi fixed | REJECT | PASS |
| C13 | multiple findings | SQLi and `eval`, both fixed | PASS | PASS |
| C14 | multiple findings | SQLi and `eval`, one fixed | REJECT | REJECT |
| C15 | ambiguous comparison | variable renamed, SQLi kept | REJECT | REJECT |
| C16 | ambiguous comparison | vulnerable line split over three lines | REJECT | REJECT |
| C17 | ambiguous comparison | vulnerable function deleted | PASS | REVIEW |
| C18 | ambiguous comparison | no findings before or after | REVIEW | REVIEW |
| C19 | ambiguous comparison | `# nosec` added to the vulnerable line | REJECT | REJECT |

**Verdict agreement: 16/19** (run of 2026-10-29, `outputs/2026-10-29_174140_summary.md`).
"Expected" is a human judgement of each fix, set before the run.

Branches: C01 `fix/sqli-parameterized`, C02 `fix/sqli-with-secret`, C03 `test/comment-only` (all against `main`), C04 `test/dup-before` → `test/dup-partial`, C05–C19 `case/CXX-before` → `case/CXX-after`.

The fixes in this test set were written by hand with help from a chat assistant. They are not output from an AI coding tool.

## Real-world check

The tool was also run on a real fix in an open-source project: [OpenStack heat-translator](https://github.com/openstack/heat-translator), commit `3cf56881413` (2017, "Replace yaml.load() with yaml.safe_load()"). The project's own developer wrote this fix.

```powershell
verify.py 3cf56881413~1 3cf56881413 <file>
```

| File | Counts (r i p) | Verdict |
|---|---|---|
| `translator/common/utils.py` | 1 0 1 | REJECT |
| `translator/hot/tosca/tosca_policies_scaling.py` | 1 0 0 | PASS |
| `translator/shell.py` | 1 0 0 | PASS |

The fix is correct in all three files, and the unsafe `yaml.load` (B506) is resolved in each one. `utils.py` is still rejected, because an older finding that has nothing to do with the fix remains in the file (B113, an HTTP request without a timeout). This is the same limitation as case C12, now seen on real code. The reports are in `outputs/real-world/heat-translator/`.

## Limitations

- **C05: correct fix rejected.** Bandit flags every use of `subprocess` (B404, B603, B607), even a safe one.
- **C12: correct fix rejected.** The strict policy also counts unrelated findings that were already in the file. The real-world check shows the same problem.
- **C17: deleted code passes.** Removing the vulnerable function removes the finding, and a static scan cannot see the lost functionality.
- **Text changes break matching.** If the vulnerable line itself changes (C06, C10, C15, C16), the same finding is counted as resolved + introduced. The verdict stays correct here, but the counts are wrong.
- **One file per run**, and only what Bandit can detect. Bandit is a pattern-based scanner and can miss issues.
- The 19 cases are small and hand-built; the results do not show general accuracy.

## Project structure

```
verify.py          entry point: scan two refs, compare, save report
compare.py         finding identity, comparison, verdict
run_cases.py       run all 19 cases and build the summary table
build_cases.py     create the case/C05–C19 branches
vulnerable_app.py  SQL injection example used by C01–C04
outputs/           saved reports and summaries (evidence)
requirements.txt   pinned dependencies
```
