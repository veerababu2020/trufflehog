import json
import csv

input_file = "trufflehog.json"
output_file = "trufflehog.csv"

with open(input_file, "r", encoding="utf-8") as infile, \
     open(output_file, "w", newline="", encoding="utf-8") as outfile:

    writer = csv.writer(outfile)
    writer.writerow([
        "detector",
        "secret",
        "repo",
        "file",
        "line",
        "commit"
    ])

    for line in infile:
        try:
            finding = json.loads(line)

            git = (
                finding.get("SourceMetadata", {})
                       .get("Data", {})
                       .get("Git", {})
            )

            writer.writerow([
                finding.get("DetectorName", ""),
                finding.get("Redacted") or finding.get("Raw", ""),
                git.get("repository", ""),
                git.get("file", ""),
                git.get("line", ""),
                git.get("commit", "")
            ])

        except Exception as e:
            print(f"Error: {e}")

print(f"Saved to {output_file}")
