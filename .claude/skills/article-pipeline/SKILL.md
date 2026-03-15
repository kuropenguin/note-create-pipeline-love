---
name: article-pipeline
description: 記事作成パイプラインをエンドツーエンドで実行する
allowed-tools: Read, Bash(ls *), Bash(mkdir *), Skill, Agent
---

# 記事作成パイプライン

素材選定 → 執筆 → AIレビューループ → 人間レビュー → 完了 の全フローを実行する。

## フロー

### ステップ1: 素材選定

`/select-material $ARGUMENTS` を実行する。
- ユーザーがキーワードや行番号を指定した場合はそれを渡す
- 実行後、slug を取得する

### ステップ2: 記事執筆

`/write-article <slug>` を実行する。
- `articles/<slug>/article.md` と画像プロンプトが生成される

### ステップ3: AIレビューループ（自動）

以下を**全レビュワーが PASS するまで**繰り返す：

1. `/review-article <slug>` を実行
2. `articles/<slug>/review.md` の総合判定を確認
3. **FAIL の場合**:
   - `/revise-article <slug>` を実行して修正
   - ステップ3の1に戻る（再レビュー）
4. **PASS の場合**:
   - ループ終了、ステップ4へ

**注意**: 無限ループ防止のため、最大3回までのリトライとする。3回 FAIL した場合は現状の記事と review.md をユーザーに提示し、判断を仰ぐ。

### ステップ4: 人間レビュー

AIレビューが全て PASS したら：

1. 以下を表示する：
   ```
   ✅ AIレビュー全パスしました。

   記事: articles/<slug>/article.md
   レビュー結果: articles/<slug>/review.md
   画像プロンプト: articles/<slug>/image-prompts/

   記事を確認してください。
   ```
2. ユーザーの返答を待つ（ここで停止する）

3. ユーザーの返答に応じて：
   - **「OK」「完了」「LGTM」等** → ステップ5（完了）へ
   - **フィードバックあり** → フィードバックに基づき記事を修正 → ステップ3（AIレビューループ）に戻る

### ステップ5: 完了

1. `articles/<slug>/plan.md` と `articles/<slug>/article.md` から情報を読み取り、`data/article_log.csv` に記録する：
   ```bash
   echo '<JSON>' | python3 .claude/skills/article-pipeline/update_article_log.py
   ```
   JSON フォーマット:
   ```json
   {
     "slug": "<slug>",
     "タイトル": "記事の最終タイトル",
     "概要": "1行の記事概要",
     "コンセプト": "記事の切り口・テーマ",
     "バズり具合": "◎/○/△",
     "元ネタRedditタイトル": "reddit_master.csv の元タイトル",
     "作成日": "YYYY-MM-DD"
   }
   ```
2. 最終版の記事情報を表示
3. commit & push する

## 各ステップの単独実行

各スキルは単独でも呼び出せる：
- `/select-material` — 素材選定のみ
- `/write-article <slug>` — 執筆のみ
- `/review-article <slug>` — レビューのみ
- `/revise-article <slug>` — 修正のみ
