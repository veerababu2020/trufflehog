import csv
import re

INPUT_FILE = "2.json"
OUTPUT_FILE = "2.csv"

def extract(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else ""

rows = []

with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
    for line_num, line in enumerate(f, start=1):

        detector = extract(r'DetectorName[:"]+([^",]+)', line)
        commit = extract(r'commit[:"]+([^",]+)', line)
        repository = extract(r'repository[:"]+([^",]+)', line)
        file_name = extract(r'file[:"]+([^",]+)', line)
        email = extract(r'email[:"]+([^",]+)', line)
        timestamp = extract(r'timestamp[:"]+([^",]+)', line)
        line_number = extract(r'line[:"]+([^",]+)', line)
        secret = extract(r'Raw[:"]+([^",]+)', line)

        # Skip completely empty rows
        if not any([
            detector,
            commit,
            repository,
            file_name,
            email,
            timestamp,
            line_number,
            secret
        ]):
            continue

        rows.append([
            detector,
            commit,
            repository,
            file_name,
            line_number,
            email,
            timestamp,
            secret
        ])

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)

    writer.writerow([
        "DetectorName",
        "Commit",
        "Repository",
        "File",
        "Line",
        "Email",
        "Timestamp",
        "Secret"
    ])

    writer.writerows(rows)

print(f"Extracted {len(rows)} records")
print(f"Saved to {OUTPUT_FILE}")
