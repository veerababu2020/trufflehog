
#key points to find duplication
#"DetectorName",
#   "Commit",
#  "File"
# "Raw",
#  "Rawv2"


import pandas as pd
from pathlib import Path

# ==========================
# CONFIGURATION
# ==========================
INPUT_CSV = "testing.csv"

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

UNIQUE_CSV = OUTPUT_DIR / "unique.csv"
DUPLICATES_CSV = OUTPUT_DIR / "duplicates.csv"
REPORT_CSV = OUTPUT_DIR / "duplicate_report.csv"

# ==========================
# LOAD CSV
# ==========================
df = pd.read_csv(INPUT_CSV, dtype=str).fillna("")

# Columns used ONLY for duplicate detection
KEY_COLUMNS = [
    "DetectorName",
    "Commit",
    "File",
    "Raw",
    "Rawv2"
]

# Verify required columns exist
missing = [c for c in KEY_COLUMNS if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

# ==========================
# NORMALIZE DATA
# ==========================
for col in KEY_COLUMNS:
    df[col] = (
        df[col]
        .astype(str)
        .str.replace("\n", "", regex=False)
        .str.replace("\r", "", regex=False)
        .str.strip()
    )

# ==========================
# DUPLICATE CHECK
# ==========================
seen = {}
unique_rows = []
duplicate_rows = []
report_rows = []

for idx, row in df.iterrows():

    # Ignore empty values when building comparison key
    key_parts = []

    for col in KEY_COLUMNS:
        value = str(row[col]).strip()

        if value:
            key_parts.append(f"{col}={value}")

    key = tuple(sorted(key_parts))

    csv_row_number = idx + 2  # header = row 1

    if key not in seen:

        seen[key] = csv_row_number
        unique_rows.append(row)

    else:

        duplicate_rows.append(row)

        report_rows.append({
            "Original_Row": seen[key],
            "Duplicate_Row": csv_row_number,
            "DetectorName": row.get("DetectorName", ""),
            "Commit": row.get("Commit", ""),
            "File": row.get("File", ""),
            "Raw": row.get("Raw", ""),
            "Rawv2": row.get("Rawv2", "")
        })

# ==========================
# SAVE FILES
# ==========================
unique_df = pd.DataFrame(unique_rows)
duplicates_df = pd.DataFrame(duplicate_rows)
report_df = pd.DataFrame(report_rows)

unique_df.to_csv(UNIQUE_CSV, index=False)
duplicates_df.to_csv(DUPLICATES_CSV, index=False)
report_df.to_csv(REPORT_CSV, index=False)

# ==========================
# SUMMARY
# ==========================
print("\n" + "=" * 60)
print("DEDUPLICATION COMPLETE")
print("=" * 60)

print(f"Input Rows           : {len(df):,}")
print(f"Unique Rows          : {len(unique_df):,}")
print(f"Duplicate Rows       : {len(duplicates_df):,}")

print("\nFiles Generated:")
print(f"  {UNIQUE_CSV}")
print(f"  {DUPLICATES_CSV}")
print(f"  {REPORT_CSV}")

print("=" * 60)
