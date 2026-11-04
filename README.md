# AI Fix Verifier

AI tools are getting good at suggesting fixes for security bugs. But how do you know a suggested fix actually worked? It might fix the bug, fix only part of it, or fix it and quietly add a new problem somewhere else.

This is my master's project in Cybersecurity (non-thesis). It's a small tool that answers one question about a fix: **did it remove the vulnerability without adding a new one?**

It runs [Bandit](https://bandit.readthedocs.io/) on the code before and after the fix, compares the two sets of findings, and gives a verdict: **PASS**, **REJECT** or **REVIEW**.

**Try it without installing anything:** [open the demo in Google Colab](https://colab.research.google.com/github/Sarsa-25/ai-fix-verifier/blob/main/demo.ipynb) and click *Runtime → Run all* (about two minutes).

---

## How it works

```
code before the fix (Git ref) ──► Bandit ──┐
                                           ├──► compare findings ──► verdict
code after the fix  (Git ref) ──► Bandit ──┘
```

Every finding gets an identity made of three things: the Bandit test ID, the file name, and the line of code. Then each finding goes into one of three groups:

| Group | Meaning |
|---|---|
| **resolved** | was there before the fix, gone after |
| **introduced** | wasn't there before, appeared after |
| **persisting** | there before and still there after |

And the verdict follows from the groups:

| What the tool sees | Verdict |
|---|---|
| anything introduced or persisting | **REJECT** |
| only resolved findings | **PASS** |
| no findings at all, before or after | **REVIEW** |

I chose a strict rule on purpose and ignore Bandit's severity. Bandit rates a hardcoded password (B105) as LOW, but a leaked password is a real risk, so I didn't want it to slip through.

The strict rule has one weak spot: an old finding that has nothing to do with the fix still rejects it. So there is also a **target mode**. You tell the tool which Bandit test the fix is meant to remove (`--target B608`), and the rule becomes:

| What the tool sees | Verdict |
|---|---|
| anything introduced | **REJECT** |
| a target finding still there | **REJECT** |
| a target finding resolved | **PASS** (other old findings are listed as "not targeted") |
| no target finding before the fix | **REVIEW** |

Without `--target` the tool stays strict.

### Three problems I found in the comparison, and how I fixed them

Comparing "before" and "after" turned out to be trickier than I expected. Three test cases broke my first version:

- **A comment changed the identity.** If a fix only added `# safe now` to the vulnerable line, the line's text changed, so the tool counted the same bug as "resolved" plus "introduced". Now comments are stripped with Python's `tokenize` before comparing (and a `#` inside a string is kept).
- **Duplicates were merged.** With two identical vulnerable lines and only one of them fixed, the partial fix was invisible. Now findings are counted with `collections.Counter`, so it shows 1 resolved and 1 persisting.
- **`# nosec` could hide a bug.** Adding `# nosec` makes Bandit skip a line, so a "fix" could just silence the warning and pass. Now Bandit runs with `--ignore-nosec`.

## Setup

I tested it with Python 3.14 and Bandit 1.9.4 on Windows.

```powershell
git clone https://github.com/Sarsa-25/ai-fix-verifier.git
cd ai-fix-verifier

# a fresh clone only has main; this gets every test-case branch too
git fetch --update-head-ok origin "+refs/heads/*:refs/heads/*"

python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

To check one fix:

```powershell
python verify.py <before_ref> <after_ref> <file_path>
python verify.py main fix/sqli-with-secret vulnerable_app.py
```

What you get:

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

This fix removed the SQL injection but added a hardcoded password, so it's rejected. `[MEDIUM/LOW]` is Bandit's severity/confidence. Every run also saves the report and both raw Bandit outputs in `outputs/`.

In target mode, add the Bandit test IDs the fix should remove:

```powershell
python verify.py main fix/sqli-with-secret vulnerable_app.py --target B608
```

To run the whole test set (each case runs in both modes):

```powershell
python run_cases.py
```

To run the AI-generated fixes:

```powershell
python run_ai_cases.py
```

To check a fix in a different repository, run the tool from inside that repository, using the full paths to this project's Python and `verify.py`. Run it once for each Python file the fix changed:

```powershell
cd C:\path\to\other-project
git diff --name-only <before_ref> <after_ref> -- "*.py"
C:\path\to\ai-fix-verifier\.venv\Scripts\python C:\path\to\ai-fix-verifier\verify.py <before_ref> <after_ref> path/to/file.py
```

For a single fix commit, use `<commit>~1` (the commit just before it) as the "before" ref.

The other files:

| File | What it does |
|---|---|
| `compare.py` | the matching and the verdict. It can also compare two Bandit JSON files: `python compare.py before.json after.json` |
| `run_cases.py` | runs all 19 cases in both modes and writes a summary table |
| `run_ai_cases.py` | runs the 16 AI-generated fixes and writes a summary table |
| `build_ai_cases.py` | turns the files in `ai_experiment/` into `ai/*` branches |
| `build_cases.py` | created the branches for cases C05–C19 (already run; it refuses to run twice) |
| `demo.ipynb` | the Colab demo |

## Test set and results

I built 19 small cases to cover six kinds of situations. Each case is a pair of Git refs (before and after), so anyone can re-run it. Before running the tool, I wrote down what the right verdict should be ("Expected").

| Case | Scenario | Change | Strict | Target mode | Expected |
|---|---|---|---|---|---|
| C01 | successful fix | SQL injection → parameterized query | PASS | PASS | PASS |
| C02 | new vulnerability introduced | SQLi fixed, hardcoded password added | REJECT | REJECT | REJECT |
| C03 | incomplete fix | only a comment added to the vulnerable line | REJECT | REJECT | REJECT |
| C04 | incomplete fix | two identical SQLi lines, one fixed | REJECT | REJECT | REJECT |
| C05 | successful fix | command injection → list arguments, no shell | REJECT | REJECT | PASS |
| C06 | incomplete fix | `shlex.quote` added, `shell=True` kept | REJECT | REJECT | REJECT |
| C07 | successful fix | `eval` → `ast.literal_eval` | PASS | PASS | PASS |
| C08 | new vulnerability introduced | `eval` → `exec` | REJECT | REJECT | REJECT |
| C09 | successful fix | `yaml.load` → `yaml.safe_load` | PASS | PASS | PASS |
| C10 | incomplete fix | `yaml.load(..., Loader=yaml.Loader)` | REJECT | REJECT | REJECT |
| C11 | successful fix | `pickle` → `json` | PASS | PASS | PASS |
| C12 | unrelated pre-existing finding | old hardcoded password, SQLi fixed | REJECT | PASS | PASS |
| C13 | multiple findings | SQLi and `eval`, both fixed | PASS | PASS | PASS |
| C14 | multiple findings | SQLi and `eval`, one fixed | REJECT | REJECT | REJECT |
| C15 | ambiguous comparison | variable renamed, SQLi kept | REJECT | REJECT | REJECT |
| C16 | ambiguous comparison | vulnerable line split over three lines | REJECT | REJECT | REJECT |
| C17 | ambiguous comparison | vulnerable function deleted | PASS | PASS | REVIEW |
| C18 | ambiguous comparison | no findings before or after | REVIEW | REVIEW | REVIEW |
| C19 | ambiguous comparison | `# nosec` added to the vulnerable line | REJECT | REJECT | REJECT |

**The tool's verdict matched mine in 16 of 19 cases with the strict rule, and 17 of 19 in target mode** (run of 2026-11-04, saved in `outputs/2026-11-04_200914_summary.md`). Target mode fixes C12. C05 and C17 are still wrong; see Limitations.

Branches: C01 `fix/sqli-parameterized`, C02 `fix/sqli-with-secret`, C03 `test/comment-only` (all compared with `main`), C04 `test/dup-before` → `test/dup-partial`, C05–C19 `case/CXX-before` → `case/CXX-after`.

## Fixes from real AI tools

The fixes above were written by hand. To test the tool on what AI tools really produce, I gave 8 vulnerable files to **GitHub Copilot** (Copilot Chat in VS Code, model chosen by "Auto": gpt-6-luna or mai-code-1.1-flash) and to **Gemini** (Gemini 3.6 Flash). Every case used the same prompt in a new chat:

> Fix the security vulnerabilities in this Python file. Reply with the complete fixed file only, in one Python code block.

I saved each answer without changing it (`ai_experiment/`, with the models and dates in `ai_experiment/log.csv`). Copilot ran in an empty folder, so it couldn't read this project and copy the hand-written fixes.

| Case | Vulnerability | Copilot | Gemini | Expected (Copilot / Gemini) |
|---|---|---|---|---|
| a01 | SQL injection | PASS | PASS | PASS / PASS |
| a02 | SQL injection, two identical lines | PASS | PASS | PASS / PASS |
| a03 | command injection (`shell=True`) | REJECT | REJECT | PASS / PASS |
| a04 | `eval` on user input | PASS | PASS | PASS / **REJECT** |
| a05 | `yaml.load` | PASS | PASS | PASS / PASS |
| a06 | `pickle.loads` | PASS | PASS | PASS / PASS |
| a07 | SQL injection + unrelated hardcoded password | PASS | PASS | PASS / PASS |
| a08 | SQL injection and `eval` | PASS | PASS | PASS / **REJECT** |

**12 of 16 verdicts match**, in both modes (run of 2026-11-04, `outputs/2026-11-04_202940_ai_summary.md`).

What I learned from it:

- **Both tools removed every targeted finding.** None of the 16 fixes left the original vulnerability in place.
- **a03 is rejected although both fixes are correct.** It's the same reason as C05: Bandit flags any use of `subprocess`.
- **Gemini's a04 and a08 pass, but they shouldn't.** Both tools replaced `eval` with a small calculator. Copilot's limits the size of powers; Gemini's doesn't, so `calc("9**9**9")` keeps running forever (denial of service). Bandit can't see this, so the tool says PASS for both. The tool is only as good as the scanner behind it.
- **Both tools did more than they were asked.** In a07 both also removed the unrelated hardcoded password.
- **Copilot's "Auto" used two different models** for different cases.

## Trying it on real code

### 1. A real open-source fix

I ran the tool on a 2017 security fix in [OpenStack heat-translator](https://github.com/openstack/heat-translator), commit `3cf56881413` ("Replace yaml.load() with yaml.safe_load()"). That project's developers wrote the fix themselves.

```powershell
verify.py 3cf56881413~1 3cf56881413 <file>
```

| File | Counts (r i p) | Verdict |
|---|---|---|
| `translator/common/utils.py` | 1 0 1 | REJECT |
| `translator/hot/tosca/tosca_policies_scaling.py` | 1 0 0 | PASS |
| `translator/shell.py` | 1 0 0 | PASS |

The fix is correct in all three files: the unsafe `yaml.load` (B506) is gone each time. `utils.py` still got rejected, because an older, unrelated finding stayed in that file (B113, an HTTP request with no timeout). It's the same weakness as case C12, this time on real code. With `--target B506`, `utils.py` gets **PASS** and B113 is listed as "not targeted". Reports: `outputs/real-world/heat-translator/`.

### 2. My own project: find, fix, verify

[job-tracker](https://github.com/Sarsa-25/job-tracker) is a small Flask app I built earlier. Bandit found one issue in it:

```
B201  app.run(debug=True)   Severity: HIGH   Confidence: MEDIUM   CWE-94
```

`debug=True` turns on the Werkzeug debugger. If the app can be reached over the network, anyone can run code on the server through it. I fixed it on a branch so debug mode stays off unless `FLASK_DEBUG=1` is set:

```python
app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
```

The tool gave `1 0 0` and **PASS**: B201 resolved, nothing new introduced. So I merged the fix. Report: `outputs/real-world/job-tracker/`.

## Limitations

- **C05, a correct fix rejected.** Bandit flags every use of `subprocess` (B404, B603, B607), even a safe one.
- **C12, a correct fix rejected (strict rule only).** The strict rule also counts old findings that have nothing to do with the fix. I saw the same thing in the open-source check. Target mode solves this, but you have to know which finding the fix is for.
- **C17, deleted code passes.** If you delete the vulnerable function, the finding disappears. A static scanner can't tell that you also lost the feature.
- **Any change to the vulnerable line breaks matching.** In C06, C10, C15 and C16 the line's text changed, so the same bug was counted as resolved + introduced. The verdict was still right in these cases, but the counts were wrong.
- **A weaker fix can pass.** Gemini's calculator in a04 and a08 allows a denial of service, but Bandit sees nothing, so the tool says PASS. The tool only knows what Bandit reports.
- It checks **one file per run**, and only finds what Bandit can detect. Bandit works by patterns and can miss things.
- 19 hand-built cases and 16 AI fixes on small files are not enough to make any claim about general accuracy.

## How this project was made

I built this project with help from an AI chat assistant (Claude). The assistant drafted much of the code and the fixes in the test set. I chose between the options it proposed, ran every experiment on my own machine, checked the results, and wrote the job-tracker fix myself.

The fixes in the 19-case test set are not output from an AI coding tool. The 16 fixes in "Fixes from real AI tools" are: they came straight from GitHub Copilot and Gemini, without changes.

## Project structure

```
verify.py          entry point: scan two refs, compare, save a report
compare.py         finding identity, comparison, verdict
run_cases.py       runs all 19 cases (strict and target mode) and builds the summary table
build_ai_cases.py  turns ai_experiment/ into ai/* branches
run_ai_cases.py    runs the 16 AI-generated fixes
ai_experiment/     inputs, prompt, AI answers and log for the AI experiment
build_cases.py     created the case/C05–C19 branches
demo.ipynb         Google Colab demo
vulnerable_app.py  the SQL injection example used by C01–C04
outputs/           saved reports and summaries (evidence)
requirements.txt   pinned dependencies
```
