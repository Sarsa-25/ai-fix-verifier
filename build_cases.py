"""Create one Git branch pair per test case (C05-C19).

Usage (from the project folder, on main, with .venv active):
    python build_cases.py

For each case it creates:
    case/CXX-before  -> cases/cXX.py with the vulnerable code
    case/CXX-after   -> cases/cXX.py with the fix

The fixes were drafted in chat by Claude (chat-drafted), not produced by an AI coding tool.
Cases C01-C04 already exist as fix/* and test/* branches.
"""

import os
import subprocess
import sys

SQL_BAD = '''import sqlite3


def get_user(conn, username):
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE name = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()
'''
SQL_GOOD = '''import sqlite3


def get_user(conn, username):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = ?", (username,))
    return cursor.fetchall()
'''
CMD_BAD = '''import subprocess


def ping(host):
    return subprocess.run(f"ping -c 1 {host}", shell=True, capture_output=True)
'''
CMD_GOOD = '''import subprocess


def ping(host):
    return subprocess.run(["ping", "-c", "1", host], capture_output=True)
'''
CMD_QUOTE = '''import shlex
import subprocess


def ping(host):
    return subprocess.run(f"ping -c 1 {shlex.quote(host)}", shell=True, capture_output=True)
'''
EVAL_BAD = '''def calc(expr):
    return eval(expr)
'''
EVAL_GOOD = '''import ast


def calc(expr):
    return ast.literal_eval(expr)
'''
EVAL_EXEC = '''def calc(expr):
    result = {}
    exec(f"value = {expr}", {}, result)
    return result["value"]
'''
YAML_BAD = '''import yaml


def load_config(text):
    return yaml.load(text)
'''
YAML_GOOD = '''import yaml


def load_config(text):
    return yaml.safe_load(text)
'''
YAML_UNSAFE = '''import yaml


def load_config(text):
    return yaml.load(text, Loader=yaml.Loader)
'''
PICKLE_BAD = '''import pickle


def load_data(blob):
    return pickle.loads(blob)
'''
PICKLE_GOOD = '''import json


def load_data(blob):
    return json.loads(blob)
'''
PRE_BAD = '''import sqlite3

API_KEY = "sk_test_123456"


def get_user(conn, username):
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE name = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()
'''
PRE_FIX = PRE_BAD.replace('''    query = f"SELECT * FROM users WHERE name = '{username}'"
    cursor.execute(query)''', '''    cursor.execute("SELECT * FROM users WHERE name = ?", (username,))''')
PRE_BAD2 = PRE_BAD.replace('API_KEY = "sk_test_123456"', 'password = "hunter2"')
PRE_FIX2 = PRE_FIX.replace('API_KEY = "sk_test_123456"', 'password = "hunter2"')
MULTI_BAD = SQL_BAD + '''

def calc(expr):
    return eval(expr)
'''
MULTI_GOOD = SQL_GOOD + '''

def calc(expr):
    import ast
    return ast.literal_eval(expr)
'''
MULTI_ONE = SQL_GOOD + '''

def calc(expr):
    return eval(expr)
'''
RENAME = SQL_BAD.replace("query = f", "sql = f").replace("cursor.execute(query)", "cursor.execute(sql)")
SPLIT = SQL_BAD.replace('''    query = f"SELECT * FROM users WHERE name = '{username}'"''', '''    query = (
        f"SELECT * FROM users WHERE name = '{username}'"
    )''')
REMOVED = '''import sqlite3
'''
CLEAN_A = '''def add(a, b):
    return a + b
'''
CLEAN_B = '''def add(a, b):
    """Return the sum."""
    return a + b
'''
NOSEC = SQL_BAD.replace('''    query = f"SELECT * FROM users WHERE name = '{username}'"''', '''    query = f"SELECT * FROM users WHERE name = '{username}'"  # nosec''')
COMMENT = SQL_BAD.replace('''    query = f"SELECT * FROM users WHERE name = '{username}'"''', '''    query = f"SELECT * FROM users WHERE name = '{username}'"  # safe now''')
DUP_BAD = SQL_BAD + '''

def find_user(conn, username):
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE name = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()
'''
DUP_PART = SQL_BAD + '''

def find_user(conn, username):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = ?", (username,))
    return cursor.fetchall()
'''
SECRET = SQL_GOOD.replace("import sqlite3\n", 'import sqlite3\n\nDB_PASSWORD = "FAKE_PASSWORD_12345"\n')


CASES = [
    ("C05", "Command injection: list args, no shell", CMD_BAD, CMD_GOOD),
    ("C06", "Command injection: shlex.quote, shell=True kept", CMD_BAD, CMD_QUOTE),
    ("C07", "eval replaced by ast.literal_eval", EVAL_BAD, EVAL_GOOD),
    ("C08", "eval replaced by exec", EVAL_BAD, EVAL_EXEC),
    ("C09", "yaml.load replaced by yaml.safe_load", YAML_BAD, YAML_GOOD),
    ("C10", "yaml.load with Loader=yaml.Loader", YAML_BAD, YAML_UNSAFE),
    ("C11", "pickle replaced by json", PICKLE_BAD, PICKLE_GOOD),
    ("C12", "Unrelated pre-existing password, SQLi fixed", PRE_BAD2, PRE_FIX2),
    ("C13", "Two different vulns, both fixed", MULTI_BAD, MULTI_GOOD),
    ("C14", "Two different vulns, one fixed", MULTI_BAD, MULTI_ONE),
    ("C15", "Variable renamed, SQLi kept", SQL_BAD, RENAME),
    ("C16", "Vulnerable line split over 3 lines", SQL_BAD, SPLIT),
    ("C17", "Vulnerable function deleted", SQL_BAD, REMOVED),
    ("C18", "No findings on either side", CLEAN_A, CLEAN_B),
    ("C19", "nosec comment added to vulnerable line", SQL_BAD, NOSEC),
]


def git(*args):
    result = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print("git", " ".join(args), "failed:", result.stderr.strip())
        sys.exit(1)
    return result.stdout


def write_case(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    if git("rev-parse", "--abbrev-ref", "HEAD").strip() != "main":
        print("Run this on main: git checkout main")
        sys.exit(1)
    if git("status", "--porcelain", "--untracked-files=no").strip():
        print("You have uncommitted changes. Commit or restore them first.")
        sys.exit(1)
    existing = git("branch", "--list", "case/*").split()
    if existing:
        print("case/* branches already exist, nothing done:", " ".join(existing))
        sys.exit(1)

    try:
        for cid, title, before, after in CASES:
            path = f"cases/{cid.lower()}.py"
            git("checkout", "-q", "-b", f"case/{cid}-before", "main")
            write_case(path, before)
            git("add", path)
            git("commit", "-q", "-m", f"case {cid} before: {title}")

            git("checkout", "-q", "-b", f"case/{cid}-after")
            write_case(path, after)
            git("add", path)
            git("commit", "-q", "-m", f"case {cid} after: {title}")
            print(f"{cid}  case/{cid}-before  case/{cid}-after  {path}")
    finally:
        git("checkout", "-q", "main")

    print("Done. Back on main.")


if __name__ == "__main__":
    main()
