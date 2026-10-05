import json

def load_findings(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["results"]

if __name__ == "__main__":
    findings = load_findings("results_secret.json")
    for item in findings:
        print(item["test_id"], item["line_number"])