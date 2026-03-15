"""
Reddit 恋愛記事素材収集スクリプト
フロー: top取得 → 絞り込み → 恋愛判定(キーワード) → 全文取得 → CSV保存
"""

import requests
import csv
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 設定
# ============================================================

SUBREDDITS = ["relationships", "dating_advice", "BreakUps"]
HEADERS = {"User-Agent": "note-article-collector/1.0"}

UPS_THRESHOLD = 100        # ups がこれ以上のものだけ
RATIO_THRESHOLD = 0.8      # upvote_ratio がこれ以上のものだけ


# ============================================================
# Step 1: Reddit top投稿を取得
# ============================================================

def fetch_top_posts(subreddit, period="week", limit=25):
    url = f"https://www.reddit.com/r/{subreddit}/top.json?t={period}&limit={limit}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    posts = resp.json()["data"]["children"]
    return [p["data"] for p in posts]


# ============================================================
# Step 2: 絞り込み（ups + ratio）
# ============================================================

def filter_posts(posts):
    return [
        p for p in posts
        if p.get("ups", 0) >= UPS_THRESHOLD
        and p.get("upvote_ratio", 0) >= RATIO_THRESHOLD
        and not p.get("over_18", False)   # NSFW除外
    ]


# ============================================================
# Step 3: 恋愛ネタか判定（キーワードマッチ）
# ============================================================

def is_love_topic(title, body):
    keywords = [
        "boyfriend", "girlfriend", "partner", "husband", "wife",
        "dating", "ex", "broke up", "breakup", "relationship",
        "cheating", "marriage", "love", "crush"
    ]
    text = (title + " " + body).lower()
    return any(k in text for k in keywords)


# ============================================================
# Step 4: 投稿の全文を .json で取得
# ============================================================

def fetch_full_json(post_id, subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json?limit=500"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def extract_comments(node):
    """コメントツリーを再帰的に抽出する"""
    result = []
    if not isinstance(node, dict) or node.get("kind") != "t1":
        return result
    d = node["data"]
    comment = {
        "author": d.get("author", ""),
        "body": d.get("body", ""),
        "ups": d.get("ups", 0),
        "replies": []
    }
    replies = d.get("replies")
    if isinstance(replies, dict):
        for child in replies["data"]["children"]:
            comment["replies"].extend(extract_comments(child))
    result.append(comment)
    return result


def extract_content(full_json):
    """記事執筆に必要な情報だけ抽出する"""
    post_data = full_json[0]["data"]["children"][0]["data"]
    content = {
        "author": post_data.get("author", ""),
        "selftext": post_data.get("selftext", ""),
        "comments": []
    }
    for child in full_json[1]["data"]["children"]:
        content["comments"].extend(extract_comments(child))
    return content


# ============================================================
# Step 5: コメント整形
# ============================================================

def _format_comment_tree(comment, depth=0):
    """1つのコメントとその返信を再帰的にテキスト化する"""
    lines = []
    indent = "  " * depth
    prefix = f"{indent}└ " if depth > 0 else ""
    lines.append(f"{prefix}[{comment['author']}] (↑{comment['ups']})")
    body = comment["body"].strip()
    for line in body.split("\n"):
        lines.append(f"{indent}{'  ' if depth > 0 else ''}{line}")
    lines.append("")
    for reply in comment.get("replies", []):
        lines.extend(_format_comment_tree(reply, depth + 1))
    return lines


def format_comments_text(comments):
    """コメントリストをスレッド構造がわかるテキストに変換する"""
    if not comments:
        return ""
    sections = []
    for i, comment in enumerate(comments, 1):
        section_lines = [f"━━━ コメント #{i} ━━━"]
        section_lines.extend(_format_comment_tree(comment))
        sections.append("\n".join(section_lines))
    return "\n".join(sections)


# ============================================================
# Step 6: CSV に保存
# ============================================================

def save_to_csv(rows):
    if not rows:
        print("保存するデータがありません")
        return

    os.makedirs("csv", exist_ok=True)
    filename = f"csv/{datetime.now().strftime('%Y-%m-%d-%H-%M')}.csv"

    fieldnames = [
        "収集日", "subreddit", "タイトル", "記事本文", "コメント",
        "ups", "upvote_ratio", "コメント数", "URL",
        "サマリー", "想定読者", "タグ", "バズり具合"
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ {len(rows)} 件を {filename} に保存しました")


# ============================================================
# メイン
# ============================================================

def main():
    print(f"=== Reddit 素材収集 開始 {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")

    all_rows = []
    seen_ids = set()

    for subreddit in SUBREDDITS:
        print(f"📡 r/{subreddit} を取得中...")
        posts = fetch_top_posts(subreddit, period="week", limit=25)
        filtered = filter_posts(posts)
        print(f"  → {len(posts)} 件中 {len(filtered)} 件がフィルター通過")

        for post in filtered:
            post_id = post["id"]
            if post_id in seen_ids:
                continue
            seen_ids.add(post_id)

            title = post["title"]
            body = post.get("selftext", "")
            ups = post["ups"]
            ratio = post["upvote_ratio"]
            url = f"https://www.reddit.com{post['permalink']}"

            try:
                # 恋愛判定（キーワードマッチ）
                if not is_love_topic(title, body):
                    print(f"  ⏭ スキップ（恋愛外）: {title[:50]}")
                    continue

                print(f"  ✓ 採用: [{ups} ups] {title[:50]}")

                # .json で全データ取得 → 記事に必要な情報だけ抽出
                time.sleep(1)  # レートリミット対策
                full_json = fetch_full_json(post_id, subreddit)
                content = extract_content(full_json)

                row = {
                    "収集日": datetime.now().strftime("%Y-%m-%d"),
                    "subreddit": subreddit,
                    "タイトル": title,
                    "記事本文": content["selftext"],
                    "コメント": format_comments_text(content["comments"]),
                    "ups": ups,
                    "upvote_ratio": ratio,
                    "コメント数": post.get("num_comments", 0),
                    "URL": url,
                    "サマリー": "",
                    "想定読者": "",
                    "タグ": "",
                    "バズり具合": "",
                }
                all_rows.append(row)
            except Exception as e:
                print(f"  ⚠ エラーでスキップ: {title[:50]} - {e}")
                continue

    save_to_csv(all_rows)
    print(f"\n=== 完了 ===")
    print(f"合計 {len(all_rows)} 件の素材を収集しました")


if __name__ == "__main__":
    main()
