#!/usr/bin/env python3

import pandas as pd
import sys
from pathlib import Path


def find_commit_column(df, possible_names):
    """
    Find commit SHA column from a list of possible names.
    """
    for col in possible_names:
        if col in df.columns:
            return col
    return None


def main():

    # Input files
    findings_file = "trufflehog.csv"
    metadata_file = "commit_scan.csv"

    # Output file
    output_file = "merged_commit_results.csv"

    print("[+] Loading CSV files...")

    try:
        findings_df = pd.read_csv(findings_file, dtype=str)
        metadata_df = pd.read_csv(metadata_file, dtype=str)
    except Exception as e:
        print(f"[ERROR] Failed to read CSV files: {e}")
        sys.exit(1)

    print(f"[+] Findings rows : {len(findings_df)}")
    print(f"[+] Metadata rows : {len(metadata_df)}")

    # Possible commit column names
    findings_commit_candidates = [
        "commit",
        "Commit",
        "commit_sha",
        "sha",
        "commitHash"
    ]

    metadata_commit_candidates = [
        "commit_sha",
        "Commit_SHA",
        "sha",
        "commit",
        "commitHash"
    ]

    findings_commit_col = find_commit_column(
        findings_df,
        findings_commit_candidates
    )

    metadata_commit_col = find_commit_column(
        metadata_df,
        metadata_commit_candidates
    )

    if not findings_commit_col:
        print("[ERROR] Commit column not found in findings file.")
        print(f"Columns: {list(findings_df.columns)}")
        sys.exit(1)

    if not metadata_commit_col:
        print("[ERROR] Commit column not found in metadata file.")
        print(f"Columns: {list(metadata_df.columns)}")
        sys.exit(1)

    print(f"[+] Findings commit column : {findings_commit_col}")
    print(f"[+] Metadata commit column : {metadata_commit_col}")

    # Clean commit values
    findings_df[findings_commit_col] = (
        findings_df[findings_commit_col]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    metadata_df[metadata_commit_col] = (
        metadata_df[metadata_commit_col]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    print("[+] Merging data...")

    merged_df = findings_df.merge(
        metadata_df,
        left_on=findings_commit_col,
        right_on=metadata_commit_col,
        how="left",
        indicator=True,
        suffixes=("", "_metadata")
    )

    # Statistics
    matched = len(merged_df[merged_df["_merge"] == "both"])
    unmatched = len(merged_df[merged_df["_merge"] == "left_only"])

    print("\n========== MERGE SUMMARY ==========")
    print(f"Total Findings Records : {len(findings_df)}")
    print(f"Matched Records        : {matched}")
    print(f"Unmatched Records      : {unmatched}")
    print("===================================\n")

    # Save unmatched separately
    unmatched_df = merged_df[merged_df["_merge"] == "left_only"]

    unmatched_file = "unmatched_commits.csv"
    unmatched_df.to_csv(unmatched_file, index=False)

    # Remove merge helper column
    merged_df.drop(columns=["_merge"], inplace=True)

    # Save merged results
    merged_df.to_csv(output_file, index=False)

    print(f"[+] Merged file saved: {output_file}")
    print(f"[+] Unmatched file saved: {unmatched_file}")

    # Show sample
    print("\n[+] Sample merged rows:")
    print(merged_df.head(5))

    print("\n[+] Done.")


if __name__ == "__main__":
    main()
