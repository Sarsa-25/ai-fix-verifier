import subprocess


def ping(host):
    if not isinstance(host, str):
        raise TypeError("host must be a string")

    host = host.strip()
    if not host:
        raise ValueError("host must not be empty")

    # Reject shell metacharacters and whitespace to avoid command injection
    if any(ch in host for ch in [";", "&", "|", ">", "<", "`", "$", "(", ")", "\n", "\r"]):
        raise ValueError("invalid host")

    return subprocess.run(
        ["ping", "-c", "1", host],
        shell=False,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
