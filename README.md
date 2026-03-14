# koi-flow

Reddit の恋愛系サブレディットから記事素材を自動収集し、note 記事作成に活用するためのパイプラインです。

## 概要

毎週月曜日に GitHub Actions が自動実行され、以下の流れで素材を収集します。

1. **収集** - Reddit の r/relationships, r/dating_advice, r/BreakUps から人気投稿を取得
2. **フィルタリング** - ups・upvote_ratio でバズった投稿を絞り込み
3. **AI 判定** - OpenRouter API (Claude Haiku) で恋愛ネタかどうかを判定
4. **コメント取得** - トップコメントを収集して読者の反応を把握
5. **AI 要約** - サマリー・タグ・想定読者・バズり予測を日本語で生成
6. **CSV 保存** - 結果を CSV に追記保存

## セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/kuropenguin/koi-flow.git
cd koi-flow

# 依存パッケージをインストール
pip install -r requirements.txt

# 環境変数を設定
cp .env.example .env
# .env を編集して OPENROUTER_API_KEY を設定
```

## 使い方

```bash
# 手動実行
python collectors/reddit_collector.py
```

GitHub Actions による自動実行は毎週月曜 UTC 0:00 に行われます。
リポジトリの Settings > Secrets に `OPENROUTER_API_KEY` を登録してください。

## ディレクトリ構成

```
koi-flow/
├── collectors/          # データ収集スクリプト
│   └── reddit_collector.py
├── pipeline/            # 記事生成パイプライン（今後実装）
│   ├── selector.py      # 素材選択
│   ├── writer.py        # 記事執筆
│   └── reviewer.py      # レビュー・校正
├── data/                # 収集データ保存先
├── .github/workflows/   # GitHub Actions 定義
│   └── weekly.yml
└── requirements.txt
```
