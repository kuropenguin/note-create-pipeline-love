#!/usr/bin/env python3
"""
stdin から JSON を受け取り、data/reddit_master.csv の指定行を更新する。

JSON フォーマット:
[
  {
    "row_index": 0,
    "サマリー": "...",
    "想定読者": "...",
    "タグ": "..."
  }
]

既存カラム（記事本文・コメント等）は一切変更しない。
一時ファイル経由で安全に書き込む。
"""

import csv
import json
import os
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
CSV_PATH = os.path.join(PROJECT_ROOT, "data", "reddit_master.csv")

UPDATE_COLUMNS = ("サマリー", "想定読者", "タグ")


def main():
    raw = sys.stdin.read()
    updates = json.loads(raw)

    # Build a lookup: row_index -> update dict
    update_map = {}
    for entry in updates:
        idx = entry["row_index"]
        update_map[idx] = {col: entry.get(col, "") for col in UPDATE_COLUMNS}

    # Read existing CSV
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Apply updates
    applied = 0
    for idx, patch in update_map.items():
        if idx < 0 or idx >= len(rows):
            print(f"Warning: row_index {idx} is out of range, skipping.", file=sys.stderr)
            continue
        for col in UPDATE_COLUMNS:
            if col in patch and patch[col]:
                rows[idx][col] = patch[col]
        applied += 1

    # Write to temp file then atomically replace
    fd, tmp_path = tempfile.mkstemp(
        suffix=".csv", dir=os.path.dirname(CSV_PATH)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as tmp_f:
            writer = csv.DictWriter(tmp_f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp_path, CSV_PATH)
    except Exception:
        os.unlink(tmp_path)
        raise

    print(f"Updated {applied} row(s) in {CSV_PATH}")


if __name__ == "__main__":
    main()
