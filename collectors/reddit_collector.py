"""
Reddit 恋愛記事素材収集スクリプト
フロー: top取得 → 絞り込み → AI恋愛判定(haiku) → 全文取得 → CSV保存
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

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL_HAIKU = "anthropic/claude-haiku-4-5"

MASTER_CSV = "data/reddit_master.csv"
FIELDNAMES = [
    "収集日", "subreddit", "タイトル", "記事本文", "コメント",
    "ups", "upvote_ratio", "コメント数", "URL",
    "サマリー", "想定読者", "タグ", "バズり具合"
]


# ============================================================
# OpenRouter API 共通
# ============================================================

def call_openrouter(model, messages, max_tokens=500):
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages
        }
    )
    return resp.json()["choices"][0]["message"]["content"].strip()


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
# Step 3: AI で恋愛ネタか判定（haiku）
# ============================================================

def is_love_topic(title, body):
    if not OPENROUTER_API_KEY:
        keywords = [
            "boyfriend", "girlfriend", "partner", "husband", "wife",
            "dating", "ex", "broke up", "breakup", "relationship",
            "cheating", "marriage", "love", "crush"
        ]
        text = (title + " " + body).lower()
        return any(k in text for k in keywords)

    prompt = f"""以下のReddit投稿が「恋愛・別れ・人間関係」に関するネタかどうか判断してください。
タイトル: {title}
本文（先頭200文字）: {body[:200]}

恋愛・別れ・パートナーシップ・浮気・結婚・片思いに関する内容であれば YES、それ以外は NO と1単語で答えてください。"""

    answer = call_openrouter(MODEL_HAIKU, [{"role": "user", "content": prompt}], max_tokens=10)
    return "YES" in answer.upper()


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

def load_master_urls():
    """マスターCSVから収集済みURLの一覧を返す"""
    if not os.path.exists(MASTER_CSV):
        return set()
    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["URL"] for row in reader}


def save_to_csv(rows):
    if not rows:
        print("保存するデータがありません")
        return

    os.makedirs("csv", exist_ok=True)
    filename = f"csv/{datetime.now().strftime('%Y-%m-%d-%H-%M')}.csv"

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ {len(rows)} 件を {filename} に保存しました")


def append_to_master(rows):
    """マスターCSVに新規行を追記する"""
    if not rows:
        return
    file_exists = os.path.exists(MASTER_CSV)
    with open(MASTER_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)
    print(f"📋 {len(rows)} 件をマスターCSVに追記しました ({MASTER_CSV})")


# ============================================================
# メイン
# ============================================================

def main():
    print(f"=== Reddit 素材収集 開始 {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")

    all_rows = []
    seen_ids = set()
    master_urls = load_master_urls()
    print(f"📋 マスターCSVに {len(master_urls)} 件の収集済みURLあり\n")

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

            if url in master_urls:
                print(f"  ⏭ スキップ（収集済み）: {title[:50]}")
                continue

            try:
                # AI判定（haiku）
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
    append_to_master(all_rows)
    print(f"\n=== 完了 ===")
    print(f"合計 {len(all_rows)} 件の素材を収集しました")


if __name__ == "__main__":
    main()
