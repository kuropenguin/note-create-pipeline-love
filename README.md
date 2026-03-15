# note-create-pipeline-love

Reddit の恋愛系サブレディットから記事素材を収集し、Claude Code で note.com 向けの記事を作成するパイプラインです。

## ワークフロー全体像

```
Phase 1: 素材収集          Phase 2: 記事分析           Phase 3: 記事作成
─────────────────        ─────────────────         ─────────────────
reddit_collector.py  →   /analyze-articles    →    /article-pipeline
                                                     ├─ 素材選定
Reddit から                サマリー・想定読者・         ├─ 執筆
人気投稿を収集             タグを自動付与              ├─ AIレビュー（8人並列）
→ reddit_master.csv       → reddit_master.csv        ├─ 人間レビュー
                           を更新                     └─ 完了・記録
```

すべてのフェーズは**手動実行**です。Claude Code のスキル（スラッシュコマンド）で実行します。

## Phase 1: 素材収集（Reddit）

Reddit の r/relationships, r/dating_advice, r/BreakUps から人気投稿を取得します。

```bash
uv run python collectors/reddit_collector.py
```

処理の流れ：
1. 各サブレディットの週間トップ投稿を取得
2. ups・upvote_ratio でフィルタリング
3. Claude Haiku で恋愛ネタかどうかを AI 判定
4. トップコメントを収集
5. `data/reddit_master.csv` に追記

## Phase 2: 記事分析

`reddit_master.csv` の未分析行にサマリー・想定読者・タグを付与します。

```
/analyze-articles
```

- 1回の実行で最大5行を処理（新しい順）
- サマリーには元ネタ概要、日米格差、記事化しやすさ、候補タイトル等を含む

## Phase 3: 記事作成パイプライン

分析済みの素材から note.com 向け記事を一気通貫で作成します。

```
/article-pipeline
```

内部ステップ：
1. **素材選定** — サマリー済み素材から記事にする素材を選び、企画書を作成
2. **執筆** — 企画書に基づき記事を執筆（ガイドラインに沿ったバズ記事）
3. **AIレビュー** — 8人のAIレビュワーが並列でレビュー（全員PASSまで自動修正ループ）
4. **人間レビュー** — ユーザーが最終確認・フィードバック
5. **完了** — `data/article_log.csv` に記録、commit & push

各ステップは単独でも実行可能（下記スキル一覧参照）。

## セットアップ

```bash
git clone https://github.com/kuropenguin/note-create-pipeline-love.git
cd note-create-pipeline-love

# 依存パッケージをインストール
pip install -r requirements.txt

# 環境変数を設定
cp .env.example .env
# .env を編集して OPENROUTER_API_KEY を設定
```

## Claude Code スキル一覧

| スキル | 説明 |
|---|---|
| `/analyze-articles` | reddit_master.csv の未分析記事にサマリー・想定読者・タグを付与 |
| `/article-pipeline` | 記事作成パイプラインをエンドツーエンドで実行 |
| `/select-material` | reddit_master.csv から記事素材を選定し、企画書を作成 |
| `/write-article <slug>` | 選定済み素材から note.com 向け記事を執筆 |
| `/review-article <slug>` | 8人のAIレビュワーが並列で記事をレビュー |
| `/revise-article <slug>` | レビュー結果に基づき記事を修正 |

## ディレクトリ構成

```
note-create-pipeline-love/
├── collectors/              # データ収集スクリプト
│   └── reddit_collector.py
├── data/                    # 収集・記録データ
│   ├── reddit_master.csv    #   全収集データ（git管理）
│   └── article_log.csv      #   記事作成ログ
├── articles/                # 記事ごとのフォルダ
│   └── <slug>/
│       ├── plan.md          #   企画書
│       ├── article.md       #   記事本文
│       ├── review.md        #   レビュー結果
│       └── image-prompts/   #   画像生成プロンプト
├── .claude/skills/          # Claude Code スキル定義
│   ├── analyze-articles/
│   ├── article-pipeline/
│   ├── select-material/
│   ├── write-article/
│   ├── review-article/
│   └── revise-article/
├── pipeline/                # パイプラインモジュール
├── csv/                     # 収集結果CSV（gitignored）
├── docs/                    # 仕様書
├── pyproject.toml
└── requirements.txt
```
