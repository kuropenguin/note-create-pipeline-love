# reddit_collector.py 仕様書

## 概要

Reddit の恋愛系サブレディットから人気投稿を収集し、CSV に保存するスクリプト。
note 記事の素材収集を目的とする。

## 処理フロー

```
Step 1: top投稿取得（Reddit API）
  ↓
Step 2: フィルタリング（ups / upvote_ratio / NSFW除外）
  ↓
Step 3: 恋愛ネタ判定（キーワードマッチ）
  ↓
Step 4: 投稿詳細取得（.json エンドポイント → 本文・コメント・返信を再帰抽出）
  ↓
Step 5: コメント整形（スレッド構造をテキスト化）
  ↓
Step 6: CSV保存（日時付きファイル名で上書き防止）
```

## 対象サブレディット

| サブレディット | 内容 |
|---|---|
| r/relationships | 恋愛・人間関係の相談 |
| r/dating_advice | デート・恋愛のアドバイス |
| r/BreakUps | 別れ・失恋の体験談 |

## 設定値

| 項目 | 値 | 説明 |
|---|---|---|
| `UPS_THRESHOLD` | 100 | ups がこの値以上の投稿のみ対象 |
| `RATIO_THRESHOLD` | 0.8 | upvote_ratio がこの値以上の投稿のみ対象 |
| `limit`（top取得） | 25 | 各サブレディットから取得する投稿数 |
| `limit`（コメント） | 500 | 投稿詳細取得時のコメント上限 |

## 使用モデル

AI API は使用しない。恋愛判定はキーワードマッチで行う。

## 各ステップの詳細

### Step 1: top投稿取得 (`fetch_top_posts`)

- エンドポイント: `https://www.reddit.com/r/{subreddit}/top.json?t=week&limit=25`
- 各サブレディットの週間トップ25件を取得
- User-Agent: `note-article-collector/1.0`

### Step 2: フィルタリング (`filter_posts`)

以下すべてを満たす投稿のみ通過:
- `ups >= 100`
- `upvote_ratio >= 0.8`
- `over_18 == False`（NSFW除外）

### Step 3: 恋愛ネタ判定 (`is_love_topic`)

- キーワードマッチで判定
  - キーワード: boyfriend, girlfriend, partner, husband, wife, dating, ex, broke up, breakup, relationship, cheating, marriage, love, crush

### Step 4: 投稿詳細取得・抽出

#### `fetch_full_json(post_id, subreddit)`
- エンドポイント: `https://www.reddit.com/r/{subreddit}/comments/{post_id}.json?limit=500`
- Reddit のレスポンス全体を取得

#### `extract_content(full_json)`
記事執筆に必要な情報のみ抽出し、以下の構造で返す:

```json
{
  "author": "投稿者ユーザー名",
  "selftext": "投稿本文（全文）",
  "comments": [
    {
      "author": "コメント投稿者",
      "body": "コメント本文（全文）",
      "ups": 158,
      "replies": [
        {
          "author": "返信者",
          "body": "返信本文（全文）",
          "ups": 44,
          "replies": [...]
        }
      ]
    }
  ]
}
```

#### `extract_comments(node)`
- コメントツリーを再帰的に辿り、すべてのコメント・返信・返信の返信を取得
- 各コメントから `author`, `body`, `ups` を抽出

### Step 5: コメント整形 (`format_comments_text`)

- コメントツリーをテキスト形式に変換
- スレッド区切り（`━━━ コメント #N ━━━`）+ インデントで返信の深さを表現
- 各コメントに `[ユーザー名] (↑ups)` を表示

### Step 6: CSV保存 (`save_to_csv`)

- 保存先: `csv/YYYY-MM-DD-HH-MM.csv`（実行日時でファイル名を生成、上書きなし）
- `csv/` ディレクトリは自動作成
- エンコーディング: UTF-8

## CSVカラム定義

| カラム名 | 内容 | ソース |
|---|---|---|
| 収集日 | 実行日（YYYY-MM-DD） | システム |
| subreddit | サブレディット名 | Reddit API |
| タイトル | 投稿タイトル | Reddit API |
| 記事本文 | 投稿本文（selftext そのまま） | Reddit API |
| コメント | コメントツリーをスレッド構造テキストに整形 | Reddit API → `format_comments_text` |
| ups | 投稿のupvote数 | Reddit API |
| upvote_ratio | upvote比率 | Reddit API |
| コメント数 | コメント総数 | Reddit API |
| URL | 投稿のURL | Reddit API |
| サマリー | （現在空白、後日実装予定） | - |
| 想定読者 | （現在空白、後日実装予定） | - |
| タグ | （現在空白、後日実装予定） | - |
| バズり具合 | （現在空白、後日実装予定） | - |

## レートリミット対策

| タイミング | 待機時間 |
|---|---|
| 投稿詳細取得の前 | 1秒 |

## 環境変数

| 変数名 | 必須 | 説明 |
|---|---|---|
現在、環境変数の設定は不要。

`.env` ファイルを `python-dotenv` で自動読み込み（将来の拡張用に残置）。

## 実行方法

```bash
uv run python collectors/reddit_collector.py
```

## 重複排除

- 1回の実行内で `post_id` による重複排除を実施（`seen_ids` セット）
- 実行をまたいだ重複排除は未実装
