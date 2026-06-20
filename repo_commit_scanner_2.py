#!/usr/bin/env python3
"""
GitHub Commit Scanner
-----------------------
Reads a CSV with two columns: repo, commit
  - repo   : GitHub URL or owner/name
  - commit : full commit SHA

For each unique repo+commit pair fetches:
  1. Repo metadata   (cached — fetched once per unique repo)
  2. Owner metadata  (cached — fetched once per unique owner)
  3. Commit metadata (fetched per unique SHA via /repos/{owner}/{repo}/commits/{sha})

Output fields (exactly as requested):
  repo_full_name, repo_html_url, repo_description, repo_forks, repo_size_kb,
  repo_language, repo_default_branch, repo_visibility, repo_is_archived,
  repo_created_at, repo_updated_at, repo_pushed_at, repo_error,
  owner_login, owner_type, owner_name, owner_email,
  owner_created_at, owner_updated_at, owner_error,
  commit_sha, commit_short_sha, commit_message, commit_author_name,
  commit_author_email, commit_author_date, commit_committer_name,
  commit_committer_email, commit_committer_date, commit_html_url, commit_verified

All output files saved to OUTPUT_DIR folder.

Setup:
    pip install requests
    python github_commit_scanner.py
"""

import csv
import json
import time
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import requests

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

PAT_TOKEN  = ""                      # leave empty for public repos (60 req/hr)
                                     # paste your PAT here for 5000 req/hr

INPUT_CSV  = "input.csv"       # columns: repo, commit
OUTPUT_DIR = "github_scan_reports"   # all outputs saved here (auto-created)

REQUEST_TIMEOUT     = 15
RETRY_ON_RATE_LIMIT = True
MAX_RETRIES         = 3

GITHUB_API_BASE = "https://api.github.com"

# exact output column order
OUTPUT_FIELDS = [
    "repo_full_name", "repo_html_url", "repo_description", "repo_forks",
    "repo_size_kb", "repo_language", "repo_default_branch", "repo_visibility",
    "repo_is_archived", "repo_created_at", "repo_updated_at", "repo_pushed_at",
    "repo_error",
    "owner_login", "owner_type", "owner_name", "owner_email",
    "owner_created_at", "owner_updated_at", "owner_error",
    "commit_sha", "commit_short_sha", "commit_message", "commit_author_name",
    "commit_author_email", "commit_author_date", "commit_committer_name",
    "commit_committer_email", "commit_committer_date", "commit_html_url",
    "commit_verified",
]

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def build_headers() -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if PAT_TOKEN:
        h["Authorization"] = f"Bearer {PAT_TOKEN}"
    return h


def api_get(url: str, headers: dict) -> requests.Response:
    attempt = 0
    while True:
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 403 and RETRY_ON_RATE_LIMIT and attempt < MAX_RETRIES:
            reset = resp.headers.get("X-RateLimit-Reset")
            wait  = max(int(reset) - int(time.time()) + 2, 5) if reset else 10
            print(f"      [rate limit] waiting {wait}s ...")
            time.sleep(wait)
            attempt += 1
            continue
        return resp


def parse_repo_url(raw: str) -> tuple:
    """
    Handles all these formats:
      owner/name
      https://github.com/owner/name
      https://github.com/owner/name.git
      https://github.com/owner/name/subpath/anything.git  <- subpath ignored
      git@github.com:owner/name.git
    Always returns only (owner, repo_name) — subpaths are ignored.
    """
    raw = raw.strip().rstrip("/")
    # SSH format
    raw = raw.replace("git@github.com:", "https://github.com/")
    # strip protocol + domain
    raw = raw.replace("https://github.com/", "").replace("http://github.com/", "")
    # split into parts, skip empty
    parts = [p.strip() for p in raw.split("/") if p.strip()]
    if len(parts) < 2:
        return None, None
    owner     = parts[0]
    repo_name = parts[1].replace(".git", "")  # strip .git suffix
    return owner, repo_name


def empty_row() -> dict:
    return {f: "" for f in OUTPUT_FIELDS}


# ---------------------------------------------------------------------------
# READ CSV
# ---------------------------------------------------------------------------

def read_csv(path: str) -> list:
    """
    Reads CSV with columns: repo, commit
    Returns deduplicated list of (owner, repo_name, commit_sha).
    """
    fp = Path(path)
    if not fp.exists():
        print(f"[!] Input file not found: {path}")
        sys.exit(1)

    rows = []
    seen = set()

    with open(fp, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = [c.strip().lower() for c in (reader.fieldnames or [])]

        # flexible column name matching
        repo_col   = next((c for c in (reader.fieldnames or [])
                           if c.strip().lower() in ("repo", "repository", "repo_url", "url")), None)
        commit_col = next((c for c in (reader.fieldnames or [])
                           if c.strip().lower() in ("commit", "commit_sha", "sha", "hash")), None)

        if not repo_col or not commit_col:
            print(f"[!] Could not find repo/commit columns in: {reader.fieldnames}")
            print("[!] Accepted repo columns   : repo, repository, repo_url, url")
            print("[!] Accepted commit columns : commit, commit_sha, sha, hash")
            sys.exit(1)

        print(f"[*] Using columns: repo='{repo_col}', commit='{commit_col}'")

        for row in reader:
            repo_raw   = (row.get(repo_col)   or "").strip()
            commit_sha = (row.get(commit_col) or "").strip()

            if not repo_raw or not commit_sha or commit_sha.startswith("#"):
                continue

            owner, repo_name = parse_repo_url(repo_raw)
            if not owner or not repo_name:
                print(f"[!] Skipping malformed repo: {repo_raw}")
                continue

            key = (owner, repo_name, commit_sha)
            if key in seen:
                continue
            seen.add(key)
            rows.append(key)

    return rows


# ---------------------------------------------------------------------------
# SECTION 1 — REPO METADATA
# ---------------------------------------------------------------------------

_repo_cache: dict = {}

def fetch_repo(owner: str, repo: str, headers: dict) -> dict:
    key = f"{owner}/{repo}"
    if key in _repo_cache:
        return _repo_cache[key]

    resp = api_get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}", headers)
    out  = empty_row()
    out["repo_full_name"] = key

    if resp.status_code == 200:
        d = resp.json()
        out.update({
            "repo_html_url"      : d.get("html_url", ""),
            "repo_description"   : d.get("description") or "",
            "repo_forks"         : d.get("forks_count", ""),
            "repo_size_kb"       : d.get("size", ""),
            "repo_language"      : d.get("language") or "",
            "repo_default_branch": d.get("default_branch", ""),
            "repo_visibility"    : d.get("visibility", ""),
            "repo_is_archived"   : d.get("archived", ""),
            "repo_created_at"    : d.get("created_at", ""),
            "repo_updated_at"    : d.get("updated_at", ""),
            "repo_pushed_at"     : d.get("pushed_at", ""),
            "repo_error"         : "",
        })
    elif resp.status_code == 401:
        out["repo_error"] = "Unauthorized — check PAT_TOKEN"
    elif resp.status_code == 404:
        out["repo_error"] = "Repo not found"
    elif resp.status_code == 403:
        out["repo_error"] = "Forbidden / rate-limited"
    else:
        out["repo_error"] = f"HTTP {resp.status_code}"

    _repo_cache[key] = out
    return out


# ---------------------------------------------------------------------------
# SECTION 2 — OWNER METADATA
# ---------------------------------------------------------------------------

_owner_cache: dict = {}

def fetch_owner(owner: str, headers: dict) -> dict:
    if owner in _owner_cache:
        return _owner_cache[owner]

    resp = api_get(f"{GITHUB_API_BASE}/users/{owner}", headers)
    out  = empty_row()
    out["owner_login"] = owner

    if resp.status_code == 200:
        d = resp.json()
        out.update({
            "owner_type"      : d.get("type", ""),
            "owner_name"      : d.get("name") or "",
            "owner_email"     : d.get("email") or "",
            "owner_created_at": d.get("created_at", ""),
            "owner_updated_at": d.get("updated_at", ""),
            "owner_error"     : "",
        })
    elif resp.status_code == 401:
        out["owner_error"] = "Unauthorized — check PAT_TOKEN"
    elif resp.status_code == 404:
        out["owner_error"] = "User/Org not found"
    else:
        out["owner_error"] = f"HTTP {resp.status_code}"

    _owner_cache[owner] = out
    return out


# ---------------------------------------------------------------------------
# SECTION 3 — COMMIT METADATA
# ---------------------------------------------------------------------------

_commit_cache: dict = {}

def fetch_commit(owner: str, repo: str, sha: str, headers: dict) -> dict:
    cache_key = f"{owner}/{repo}@{sha}"
    if cache_key in _commit_cache:
        return _commit_cache[cache_key]

    resp = api_get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits/{sha}", headers)
    out  = empty_row()
    out["commit_sha"]       = sha
    out["commit_short_sha"] = sha[:7]

    if resp.status_code == 200:
        d    = resp.json()
        c    = d.get("commit", {})
        auth = c.get("author")       or {}
        comm = c.get("committer")    or {}
        ver  = c.get("verification") or {}

        out.update({
            "commit_sha"            : d.get("sha", sha),
            "commit_short_sha"      : (d.get("sha") or sha)[:7],
            "commit_message"        : (c.get("message") or "").split("\n")[0][:200],
            "commit_author_name"    : auth.get("name", ""),
            "commit_author_email"   : auth.get("email", ""),
            "commit_author_date"    : auth.get("date", ""),
            "commit_committer_name" : comm.get("name", ""),
            "commit_committer_email": comm.get("email", ""),
            "commit_committer_date" : comm.get("date", ""),
            "commit_html_url"       : d.get("html_url", ""),
            "commit_verified"       : ver.get("verified", ""),
        })
    elif resp.status_code == 401:
        out["commit_message"] = "ERROR: Unauthorized — check PAT_TOKEN"
    elif resp.status_code == 404:
        out["commit_message"] = "ERROR: Commit SHA not found"
    elif resp.status_code == 403:
        out["commit_message"] = "ERROR: Forbidden / rate-limited"
    else:
        out["commit_message"] = f"ERROR: HTTP {resp.status_code}"

    _commit_cache[cache_key] = out
    return out


# ---------------------------------------------------------------------------
# OUTPUT WRITERS
# ---------------------------------------------------------------------------

def write_csv(rows: list, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"[+] CSV  → {path}  ({len(rows)} rows)")


def write_json(rows: list, path: str) -> None:
    clean = [{k: r.get(k, "") for k in OUTPUT_FIELDS} for r in rows]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2)
    print(f"[+] JSON → {path}")


def write_markdown(rows: list, path: str) -> None:
    ts     = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    errors = sum(1 for r in rows if r.get("repo_error") or
                 (r.get("commit_message") or "").startswith("ERROR"))

    lines = [
        "# GitHub Commit Scan Report",
        f"Generated : {ts}",
        f"Total unique commits : {len(rows)}  |  Errors : {errors}",
        "",
        "---",
        "",
    ]

    grouped = defaultdict(list)
    for r in rows:
        grouped[r["repo_full_name"]].append(r)

    for repo_name, repo_rows in grouped.items():
        r0 = repo_rows[0]
        repo_url = r0.get("repo_html_url") or "#"

        lines += [
            f"## [{repo_name}]({repo_url})",
            "",
            "### Repository",
            "| Field | Value |",
            "|-------|-------|",
            f"| Description    | {r0.get('repo_description','')} |",
            f"| Language       | {r0.get('repo_language','')} |",
            f"| Forks          | {r0.get('repo_forks','')} |",
            f"| Size           | {r0.get('repo_size_kb','')} KB |",
            f"| Visibility     | {r0.get('repo_visibility','')} |",
            f"| Default Branch | {r0.get('repo_default_branch','')} |",
            f"| Archived       | {r0.get('repo_is_archived','')} |",
            f"| Created        | {r0.get('repo_created_at','')} |",
            f"| Updated        | {r0.get('repo_updated_at','')} |",
            f"| Last Push      | {r0.get('repo_pushed_at','')} |",
            "",
            "### Owner",
            "| Field | Value |",
            "|-------|-------|",
            f"| Login    | {r0.get('owner_login','')} |",
            f"| Type     | {r0.get('owner_type','')} |",
            f"| Name     | {r0.get('owner_name','')} |",
            f"| Email    | {r0.get('owner_email','')} |",
            f"| Created  | {r0.get('owner_created_at','')} |",
            f"| Updated  | {r0.get('owner_updated_at','')} |",
            "",
            f"### Commits ({len(repo_rows)})",
            "| # | Short SHA | Author | Email | Date | Message | Verified |",
            "|---|-----------|--------|-------|------|---------|----------|",
        ]

        for i, r in enumerate(repo_rows, 1):
            commit_url   = r.get("commit_html_url", "")
            short_sha    = r.get("commit_short_sha", "")
            sha_display  = f"[{short_sha}]({commit_url})" if commit_url else short_sha
            date         = (r.get("commit_author_date") or "")[:10]
            msg          = (r.get("commit_message") or "")[:70]
            lines.append(
                f"| {i} | {sha_display} | {r.get('commit_author_name','')} | "
                f"{r.get('commit_author_email','')} | {date} | {msg} | "
                f"{r.get('commit_verified','')} |"
            )

        lines += ["", "---", ""]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[+] MD   → {path}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    if not PAT_TOKEN:
        print("[!] No PAT_TOKEN — unauthenticated (60 req/hr, public repos only).")
        print("    Set PAT_TOKEN for 5000 req/hr.\n")

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    print(f"[*] Output directory : {OUTPUT_DIR}/")

    headers = build_headers()
    entries = read_csv(INPUT_CSV)
    print(f"[*] Unique repo+commit pairs loaded : {len(entries)}\n")

    rows = []
    for i, (owner, repo, sha) in enumerate(entries, 1):
        print(f"[{i:>3}/{len(entries)}] {owner}/{repo}  →  {sha[:12]}...")

        repo_data   = fetch_repo(owner, repo, headers)
        owner_data  = fetch_owner(owner, headers)
        commit_data = fetch_commit(owner, repo, sha, headers)

        if repo_data.get("repo_error"):
            print(f"         [!] repo   : {repo_data['repo_error']}")
        if owner_data.get("owner_error"):
            print(f"         [!] owner  : {owner_data['owner_error']}")
        if (commit_data.get("commit_message") or "").startswith("ERROR"):
            print(f"         [!] commit : {commit_data['commit_message']}")

        row = empty_row()
        # merge — order matters: repo → owner → commit (commit fields win on overlap)
        for src in (repo_data, owner_data, commit_data):
            for k, v in src.items():
                if k in OUTPUT_FIELDS and v != "":
                    row[k] = v

        rows.append(row)

    print()
    write_csv(rows,  f"{OUTPUT_DIR}/commit_scan.csv")
    write_json(rows, f"{OUTPUT_DIR}/commit_scan.json")
    write_markdown(rows, f"{OUTPUT_DIR}/commit_scan.md")

    ok     = sum(1 for r in rows if not r.get("repo_error") and
                 not (r.get("commit_message") or "").startswith("ERROR"))
    errors = len(rows) - ok
    print(f"\n[*] Done — {ok} OK  |  {errors} errors  |  {len(rows)} total rows")
    print(f"[*] All reports saved to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
