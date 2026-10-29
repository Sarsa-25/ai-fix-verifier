import shlex
import subprocess


def ping(host):
    return subprocess.run(f"ping -c 1 {shlex.quote(host)}", shell=True, capture_output=True)
