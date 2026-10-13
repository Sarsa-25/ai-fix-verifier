import json
import os


def load_findings(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["results"]


def finding_key(item):
    test_id = item["test_id"]
    filename = os.path.basename(item["filename"])

    code_line = ""
    for line in item["code"].split("\n"):
        number, _, text = line.partition(" ")
        if number.isdigit() and int(number) == item["line_number"]:
            code_line = text.strip()

    return (test_id, filename, code_line)


if __name__ == "__main__":
    before = []
    for item in load_findings("results_main.json"):
        before.append(finding_key(item))

    after = []
    for item in load_findings("results_secret.json"):
        after.append(finding_key(item))

    print("before:", before)
    print("after:", after)
    
    print("Resolved:")
    for key in before:
        if (key not in after):
            print(key)

    print("Introduced:")
    for key in after:
        if (key not in before):
            print(key)        