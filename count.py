import re

INPUT_FILE = "new.json"

with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

count = len(re.findall(r'SourceMetadata', content, re.IGNORECASE))

print(f"SourceMetadata Count: {count}")
