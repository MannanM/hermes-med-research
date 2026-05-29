"""Collect *-summary.md files for a date range and print them to stdout.

Usage via execute_code (inline, works regardless of CWD):
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, skill_path, "MECFS", "2026-05-25", "2026-05-27"],
        capture_output=True, text=True, cwd="/opt/data"
    )
    print(result.stdout)

Usage via terminal (must be in /opt/data/):
    python3 scripts/collect_summaries.py MECFS 2026-05-25 2026-05-27
"""

import os
import sys
from datetime import datetime, timedelta

WORKSPACE_ROOT = "/opt/data/workspace"


def collect_summaries(report_type, start_date_str, end_date_str=None):
    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    end = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else start
    dates = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((end - start).days + 1)]

    collected = []
    for d in dates:
        dir_path = os.path.join(WORKSPACE_ROOT, f"articles-{report_type}", d)
        if not os.path.isdir(dir_path):
            continue
        for fname in os.listdir(dir_path):
            if not fname.endswith("-summary.md"):
                continue
            fpath = os.path.join(dir_path, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            pmid = fname.replace("-summary.md", "")
            collected.append({"date": d, "pmid": pmid, "summary_content": content})
    return collected


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} REPORT_TYPE START_DATE [END_DATE]")
        sys.exit(1)

    report_type = sys.argv[1]
    start_date = sys.argv[2]
    end_date = sys.argv[3] if len(sys.argv) > 3 else None

    summaries = collect_summaries(report_type, start_date, end_date)
    print(f"Collected {len(summaries)} summaries for post synthesis.")
    for s in summaries:
        print(f"--- Article {s['pmid']} ({s['date']}) ---")
        print(s["summary_content"])
