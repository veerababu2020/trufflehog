import re
import csv
import json

INPUT_FILE  = "new.json"
OUTPUT_FILE = "hello.csv"

with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

def deep_clean(val):
    """
    Iteratively unescape JSON string escapes until stable (handles double/triple escaping).
    Then remove any remaining stray backslashes and collapse embedded newlines.
    """
    prev = None
    current = val
    for _ in range(10):
        prev = current
        try:
            current = json.loads(f'"{current}"')
        except Exception:
            current = (current
                       .replace('\\\\"', '"')
                       .replace('\\"', '"')
                       .replace('\\\\', '\\'))
        if prev == current:
            break
    # Remove stray backslashes before non-backslash chars (e.g. \a -> a)
    current = re.sub(r'\\([^\\])', r'\1', current)
    # Collapse embedded newlines / carriage returns
    current = re.sub(r'[\r\n]+', ' ', current).strip()
    return current

def extract(key, text, flags=0):
    """Standard field extractor — handles escaped quotes inside values."""
    pattern = rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"'
    return re.findall(pattern, text, flags)

def extract_rawv2(text):
    """
    Smart RawV2 extractor that handles two formats:
      Format 1 — plain string : "RawV2": "abc-def-123"
      Format 2 — embedded JSON: "RawV2": "{\"accountName\":\"...\",\"accountKey\":\"...\"}"

    For Format 2 (starts with '{'), reads until the closing '}"' sequence
    to avoid being tripped up by unescaped quotes inside the value.
    For Format 1, uses standard char-by-char escaped-string parsing.
    """
    results = []
    for m in re.finditer(r'"RawV2"\s*:\s*"', text):
        i = m.end()
        if i < len(text) and text[i] == '{':
            # JSON object format — seek to closing }"
            end = text.find('}"', i)
            if end == -1:
                end = text.find('"', i)  # fallback
            results.append(text[i:end + 1])  # include the closing }
        else:
            # Plain string format — char-by-char until unescaped "
            val_chars = []
            while i < len(text):
                ch = text[i]
                if ch == '\\' and i + 1 < len(text):
                    val_chars.append(ch)
                    val_chars.append(text[i + 1])
                    i += 2
                elif ch == '"':
                    break
                else:
                    val_chars.append(ch)
                    i += 1
            results.append(''.join(val_chars))
    return results

# Extract all fields
detectors  = extract("DetectorName", content)
commits    = extract("commit",        content)
repos      = extract("repository",   content)
links      = extract("link",         content)
files      = extract("file",         content)
emails     = extract("email",        content)
timestamps = extract("timestamp",    content)
raws       = extract("Raw",          content, re.DOTALL)
rawv2s     = extract_rawv2(content)   # smart extractor for RawV2

# Deep clean all extracted values
detectors  = [deep_clean(v) for v in detectors]
commits    = [deep_clean(v) for v in commits]
repos      = [deep_clean(v) for v in repos]
links      = [deep_clean(v) for v in links]
files      = [deep_clean(v) for v in files]
emails     = [deep_clean(v) for v in emails]
timestamps = [deep_clean(v) for v in timestamps]
raws       = [deep_clean(v) for v in raws]
rawv2s     = [deep_clean(v) for v in rawv2s]

# Determine row count
max_len = max(
    len(detectors),
    len(commits),
    len(repos),
    len(links),
    len(files),
    len(emails),
    len(timestamps),
    len(raws),
    len(rawv2s),
)

# Write CSV
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
        "Raw",
        "RawV2",
    ])
    for i in range(max_len):
        writer.writerow([
            detectors[i]  if i < len(detectors)  else "",
            commits[i]    if i < len(commits)     else "",
            repos[i]      if i < len(repos)       else "",
            links[i]      if i < len(links)       else "",
            files[i]      if i < len(files)       else "",
            emails[i]     if i < len(emails)      else "",
            timestamps[i] if i < len(timestamps)  else "",
            raws[i]       if i < len(raws)        else "",
            rawv2s[i]     if i < len(rawv2s)      else "",
        ])

print(f"Saved {max_len} rows to {OUTPUT_FILE}")
