---
name: write-article
description: 選定済み素材から note.com 向けバズ記事を執筆する
allowed-tools: Read, Bash(ls *)
---

# 記事執筆スキル

`articles/<slug>/plan.md` の企画に基づき、note.com 向けの記事を執筆する。

## 手順

1. `$ARGUMENTS` から slug を取得する（例：`/write-article love-after-breakup`）。

2. `articles/<slug>/plan.md`（企画書）を読み込む。

3. 企画書に記載された元データの行を `data/reddit_master.csv` から読み込む。

4. 同ディレクトリの `guidelines.md` を参照し、**バズる記事の書き方ルール**に沿って記事を執筆する。

5. 同ディレクトリの `article-template.md` の構成に沿ってマークダウンで記事を書く。

6. `articles/<slug>/article.md` に出力する。

7. 記事の各セクションに合わせた**画像生成プロンプト**（日本語）を作成し、`articles/<slug>/image-prompts/` に保存する：
   - `01-header.txt`（ヘッダー画像用）
   - `02-<セクション名>.txt`（各セクション用、3〜5枚）
   - 各プロンプトには画像のスタイル、雰囲気、構図を具体的に記述する

## 重要な執筆ルール

- **元ネタの Reddit 投稿を直訳しない**。エッセンスを抽出し、日本の読者向けにローカライズする
- **個人情報は完全に匿名化**する（名前、地名、年齢等は変更）
- **一人称視点**で書く（「私」or 三人称の体験談風）
- `guidelines.md` の AI 臭い表現リストを必ず避ける
