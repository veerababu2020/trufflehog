import re
from pathlib import Path

INPUT_FILE = "new.json"

try:
    with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Count occurrences of SourceMetadata
    count = len(re.findall(r'"?SourceMetadata"?', content, re.IGNORECASE))

    print("=" * 50)
    print(f"File: {Path(INPUT_FILE).name}")
    print("=" * 50)
    print(f"SourceMetadata Count: {count}")
    print("=" * 50)

    if count > 0:
        print(f"Estimated Findings: {count}")
    else:
        print("No SourceMetadata entries found.")

except FileNotFoundError:
    print(f"ERROR: File not found -> {INPUT_FILE}")

except Exception as e:
    print(f"ERROR: {e}")
