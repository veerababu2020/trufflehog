import re
import csv

INPUT_FILE = "new.json"
OUTPUT_FILE = "hello.csv"

with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

detectors = re.findall(r'"DetectorName"\s*:\s*"([^"]*)"', content)
commits = re.findall(r'"commit"\s*:\s*"([^"]*)"', content)
repos = re.findall(r'"repository"\s*:\s*"([^"]*)"', content)
links = re.findall(r'"link"\s*:\s*"([^"]*)"', content)
files = re.findall(r'"file"\s*:\s*"([^"]*)"', content)
emails = re.findall(r'"email"\s*:\s*"([^"]*)"', content)
timestamps = re.findall(r'"timestamp"\s*:\s*"([^"]*)"', content)
raws = re.findall(r'"Raw"\s*:\s*"([^"]*)"', content, re.DOTALL)

max_len = max(
    len(detectors),
    len(commits),
    len(repos),
    len(links),
    len(files),
    len(emails),
    len(timestamps),
    len(raws),
)

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as out:
    writer = csv.writer(out)

    writer.writerow([
        "DetectorName",
        "Commit",
        "Repository",
        "Link",
        "File",
        "Email",
        "Timestamp",
        "Secret"
    ])

    for i in range(max_len):
        writer.writerow([
            detectors[i] if i < len(detectors) else "",
            commits[i] if i < len(commits) else "",
            repos[i] if i < len(repos) else "",
            links[i] if i < len(links) else "",
            files[i] if i < len(files) else "",
            emails[i] if i < len(emails) else "",
            timestamps[i] if i < len(timestamps) else "",
            raws[i] if i < len(raws) else "",
        ])

print(f"Saved {max_len} rows to {OUTPUT_FILE}")
