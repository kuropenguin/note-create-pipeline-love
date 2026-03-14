"""
Reddit 恋愛記事素材収集スクリプト
フロー: top取得 → 絞り込み → AI恋愛判定 → コメント取得 → AI要約 → CSV保存
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
TOP_COMMENTS = 5           # 取得するトップコメント数

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "anthropic/claude-sonnet-4-6"  # 好きなモデルに変更可
OUTPUT_CSV = "reddit_materials.csv"

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
# Step 3: AI で恋愛ネタか判定
# ============================================================

def is_love_topic(title, body):
    if not OPENROUTER_API_KEY:
        # APIキーなし → キーワードで簡易判定
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

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": OPENROUTER_MODEL,
            "max_tokens": 10,
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    answer = resp.json()["choices"][0]["message"]["content"].strip().upper()
    return "YES" in answer


# ============================================================
# Step 4: コメントを取得
# ============================================================

def fetch_comments(post_id, subreddit, limit=TOP_COMMENTS):
    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json?limit=20&sort=top"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()

    comments = []
    for item in data[1]["data"]["children"]:
        if item["kind"] == "t1":
            d = item["data"]
            comments.append({
                "body": d.get("body", ""),
                "ups": d.get("ups", 0)
            })
    # upsで並び替えてtop N件
    comments.sort(key=lambda x: x["ups"], reverse=True)
    return comments[:limit]


# ============================================================
# Step 5: AI でサマリー・タグ・想定読者を生成
# ============================================================

def generate_summary(title, body, comments):
    comments_text = "\n".join(
        [f"- [{c['ups']} ups] {c['body'][:150]}" for c in comments]
    )

    if not OPENROUTER_API_KEY:
        return {
            "summary": f"{title}についての投稿。{body[:100]}",
            "tags": "恋愛,別れ",
            "target_reader": "別れを経験した人",
            "buzz_potential": "中"
        }

    prompt = f"""以下のReddit投稿（英語）を日本語で分析してください。

タイトル: {title}
本文: {body[:500]}

トップコメント:
{comments_text}

以下をJSON形式で返してください（他のテキストは不要）:
{{
  "summary": "この投稿が何について書かれているか、日本語で2〜3文",
  "tags": "カンマ区切りのタグ（例: 別れ,未練,ボディイメージ）",
  "target_reader": "想定読者（例: 別れたばかりの20代女性）",
  "buzz_potential": "バズり具合の予測（高/中/低）とその理由"
}}"""

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": OPENROUTER_MODEL,
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}]
        }
    )

    text = resp.json()["choices"][0]["message"]["content"].strip()
    # JSON部分を抽出
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])


# ============================================================
# Step 6: CSV に保存
# ============================================================

def save_to_csv(rows, filename=OUTPUT_CSV):
    if not rows:
        print("保存するデータがありません")
        return

    fieldnames = [
        "収集日", "subreddit", "タイトル", "本文（先頭300文字）",
        "ups", "upvote_ratio", "コメント数", "URL",
        "トップコメント1", "トップコメント2", "トップコメント3",
        "サマリー", "タグ", "想定読者", "バズり具合", "使用回数"
    ]

    file_exists = os.path.exists(filename)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"✅ {len(rows)} 件を {filename} に保存しました")


# ============================================================
# メイン
# ============================================================

def main():
    print(f"=== Reddit 素材収集 開始 {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")

    all_rows = []
    seen_ids = set()  # 重複排除用（本来はDBやファイルに永続化）

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

            # AI判定
            if not is_love_topic(title, body):
                print(f"  ⏭ スキップ（恋愛外）: {title[:50]}")
                continue

            print(f"  ✓ 採用: [{ups} ups] {title[:50]}")

            # コメント取得
            time.sleep(1)  # レートリミット対策
            comments = fetch_comments(post_id, subreddit)

            # AI要約
            summary_data = generate_summary(title, body, comments)
            time.sleep(0.5)

            # 行を構築
            row = {
                "収集日": datetime.now().strftime("%Y-%m-%d"),
                "subreddit": subreddit,
                "タイトル": title,
                "本文（先頭300文字）": body[:300],
                "ups": ups,
                "upvote_ratio": ratio,
                "コメント数": post.get("num_comments", 0),
                "URL": url,
                "トップコメント1": comments[0]["body"][:200] if len(comments) > 0 else "",
                "トップコメント2": comments[1]["body"][:200] if len(comments) > 1 else "",
                "トップコメント3": comments[2]["body"][:200] if len(comments) > 2 else "",
                "サマリー": summary_data.get("summary", ""),
                "タグ": summary_data.get("tags", ""),
                "想定読者": summary_data.get("target_reader", ""),
                "バズり具合": summary_data.get("buzz_potential", ""),
                "使用回数": 0
            }
            all_rows.append(row)

    save_to_csv(all_rows)
    print(f"\n=== 完了 ===")
    print(f"合計 {len(all_rows)} 件の素材を収集しました")


if __name__ == "__main__":
    main()
