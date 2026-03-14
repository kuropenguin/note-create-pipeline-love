"""
Reddit 恋愛記事素材収集スクリプト
フロー: top取得 → 絞り込み → AI恋愛判定(haiku) → 全文取得 → AI要約・想定読者(sonnet) → CSV保存
"""

import requests
import json
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
MODEL_SONNET = "anthropic/claude-sonnet-4-6"


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
# Step 5: AI でサマリー・想定読者を生成（sonnet）
# ============================================================

def generate_summary(title, body):
    if not OPENROUTER_API_KEY:
        return {
            "summary": f"{title}についての投稿。{body[:100]}",
            "target_reader": "別れを経験した人",
        }

    prompt = f"""以下のReddit投稿（英語）を日本語で分析してください。

タイトル: {title}
本文: {body}

以下をJSON形式で返してください（他のテキストは不要）:
{{
  "summary": "ここの投稿とコメントを読んで、記事を書く人が背景・感情の核心・読者の反応まで一気に把握できるよう、日本語で5〜7文で詳しくまとめてください",
  "target_reader": "想定読者（例: 別れたばかりの20代女性）"
}}"""

    max_tokens = len(prompt) * 3
    text = call_openrouter(MODEL_SONNET, [{"role": "user", "content": prompt}], max_tokens=max_tokens)
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except (json.JSONDecodeError, ValueError):
        print(f"  ⚠ サマリーのパースに失敗、フォールバック使用")
        return {"summary": text[:300], "target_reader": ""}


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
        "収集日", "subreddit", "タイトル", "内容",
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

            # AI判定（haiku）
            if not is_love_topic(title, body):
                print(f"  ⏭ スキップ（恋愛外）: {title[:50]}")
                continue

            print(f"  ✓ 採用: [{ups} ups] {title[:50]}")

            # .json で全データ取得 → 記事に必要な情報だけ抽出
            time.sleep(1)  # レートリミット対策
            full_json = fetch_full_json(post_id, subreddit)
            content = extract_content(full_json)

            # AI要約・想定読者（sonnet）
            summary_data = generate_summary(title, content["selftext"])
            time.sleep(0.5)

            row = {
                "収集日": datetime.now().strftime("%Y-%m-%d"),
                "subreddit": subreddit,
                "タイトル": title,
                "内容": json.dumps(content, ensure_ascii=False),
                "ups": ups,
                "upvote_ratio": ratio,
                "コメント数": post.get("num_comments", 0),
                "URL": url,
                "サマリー": summary_data.get("summary", ""),
                "想定読者": summary_data.get("target_reader", ""),
                "タグ": "",
                "バズり具合": "",
            }
            all_rows.append(row)

    save_to_csv(all_rows)
    print(f"\n=== 完了 ===")
    print(f"合計 {len(all_rows)} 件の素材を収集しました")


if __name__ == "__main__":
    main()
