#!/usr/bin/env python3
"""
stdin から JSON を受け取り、data/article_log.csv に1行追記する。

JSON フォーマット:
{
  "slug": "...",
  "タイトル": "...",
  "概要": "...",
  "コンセプト": "...",
  "バズり具合": "...",
  "元ネタRedditタイトル": "...",
  "記事タイプ": "無料/無料(有料紹介)/有料",
  "作成日": "YYYY-MM-DD"
}
"""

import csv
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
CSV_PATH = os.path.join(PROJECT_ROOT, "data", "article_log.csv")

FIELDNAMES = ["slug", "タイトル", "概要", "コンセプト", "バズり具合", "元ネタRedditタイトル", "記事タイプ", "作成日"]


def main():
    raw = sys.stdin.read()
    entry = json.loads(raw)

    with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow({col: entry.get(col, "") for col in FIELDNAMES})

    print(f"Appended 1 row to {CSV_PATH}: {entry.get('slug', '')}")


if __name__ == "__main__":
    main()
