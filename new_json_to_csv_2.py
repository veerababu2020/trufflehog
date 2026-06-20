import json
import csv

INPUT_FILE = "2.json"
OUTPUT_FILE = "2.csv"

def get_nested(data, *keys):
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, {})
        else:
            return ""
    return current if current != {} else ""

rows = []

with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:

    # Read entire file
    content = f.read().strip()

    findings = []

    # Case 1: JSON Array
    try:
        data = json.loads(content)

        if isinstance(data, list):
            findings = data
        elif isinstance(data, dict):
            findings = [data]

    except Exception:

        # Case 2: JSON Lines (TruffleHog default)
        findings = []

        decoder = json.JSONDecoder()
        pos = 0

        while pos < len(content):
            try:
                obj, index = decoder.raw_decode(content, pos)
                findings.append(obj)
                pos = index

                while pos < len(content) and content[pos].isspace():
                    pos += 1

            except Exception:
                pos += 1

for finding in findings:

    git = (
        get_nested(finding, "SourceMetadata", "Data", "Git")
        or get_nested(finding, "SourceMetadata", "Data", "github")
        or {}
    )

    secret = (
        finding.get("Redacted")
        or finding.get("Raw")
        or ""
    )

    rows.append([
        finding.get("DetectorName", ""),
        finding.get("Verified", ""),
        secret,
        git.get("repository", ""),
        git.get("file", ""),
        git.get("line", ""),
        git.get("commit", ""),
        git.get("email", ""),
        git.get("timestamp", "")
    ])

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(
        f,
        quoting=csv.QUOTE_ALL
    )

    writer.writerow([
        "DetectorName",
        "Verified",
        "Secret",
        "Repository",
        "File",
        "Line",
        "Commit",
        "Email",
        "Timestamp"
    ])

    writer.writerows(rows)

print(f"Exported {len(rows)} findings to {OUTPUT_FILE}")
