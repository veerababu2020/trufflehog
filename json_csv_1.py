import json
import csv

INPUT_FILE = "trufflehog.json"
OUTPUT_FILE = "trufflehog.csv"


def get_git_data(finding):
    return (
        finding.get("SourceMetadata", {})
               .get("Data", {})
               .get("Git", {})
    )


rows = []

try:
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # Try JSON array first
    try:
        data = json.loads(content)

        if isinstance(data, dict):
            data = [data]

        findings = data

    except json.JSONDecodeError:
        # Fall back to JSONL format
        findings = []
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            findings.append(json.loads(line))

    for finding in findings:
        git = get_git_data(finding)

        rows.append([
            finding.get("DetectorName", ""),
            finding.get("Verified", ""),
            finding.get("Redacted") or finding.get("Raw", ""),
            git.get("repository", ""),
            git.get("file", ""),
            git.get("line", ""),
            git.get("commit", ""),
            git.get("email", ""),
            git.get("timestamp", "")
        ])

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as outfile:
        writer = csv.writer(outfile)

        writer.writerow([
            "detector",
            "verified",
            "secret",
            "repo",
            "file",
            "line",
            "commit",
            "email",
            "timestamp"
        ])

        writer.writerows(rows)

    print(f"Successfully exported {len(rows)} findings to {OUTPUT_FILE}")

except Exception as e:
    print(f"ERROR: {e}")
