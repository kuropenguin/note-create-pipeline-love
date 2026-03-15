---
name: review-article
description: 4人のAIレビュワーが並列で記事をレビューする
allowed-tools: Read, Agent
---

# 記事レビュースキル

`articles/<slug>/article.md` を8人のAIレビュワーが並列でレビューし、結果を統合する。

## 手順

1. `$ARGUMENTS` から slug を取得する（例：`/review-article love-after-breakup`）。

2. `articles/<slug>/article.md` を読み込む。

3. 以下の6つのレビュワーペルソナファイルを読み込む：
   - `.claude/skills/review-article/reviewers/note-guidelines.md`
   - `.claude/skills/review-article/reviewers/ai-detection.md`
   - `.claude/skills/review-article/reviewers/reader-perspective.md`
   - `.claude/skills/review-article/reviewers/female-empathy.md`
   - `.claude/skills/review-article/reviewers/persona-consistency.md`
   - `.claude/skills/review-article/reviewers/note-editor.md`
   - `.claude/skills/review-article/reviewers/image-reviewer.md`
   - `.claude/skills/review-article/reviewers/title-reviewer.md`

4. **Agent ツールで8つのサブエージェントを並列起動する**（1つのレスポンスで8つの Agent 呼び出しを行う）。各エージェントには以下を渡す：
   - 記事の全文
   - 記事タイプ（無料 / 有料 / 無料(有料紹介)）— 各レビュワーが記事タイプ別チェック項目を適用するために必要
   - そのレビュワーのペルソナと評価基準（ペルソナファイルの内容をそのまま含める）
   - 以下のフォーマットでフィードバックを返すよう指示する

### レビューフィードバックフォーマット

```
## {レビュワー名}

### 総合評価
{PASS / FAIL}

### 必須修正（MUST FIX）
- {犯罪的内容、公序良俗違反、個人情報露出など — なければ「なし」}

### 推奨修正（SHOULD FIX）
- {読みやすさ、AI臭さ、バズパターン準拠など — なければ「なし」}

### 提案（SUGGESTION）
- {あると良い改善 — なければ「なし」}

### 詳細コメント
{具体的な箇所を引用しながらのコメント}
```

5. 8人全員のフィードバックを受け取ったら、`articles/<slug>/review.md` に**追記**する（上書きしない。ログとして蓄積する）。

6. 追記するブロックの先頭に日時と総合判定を記載する：
   ```markdown
   ---

   ## AIレビュー（YYYY-MM-DD HH:MM）

   ### 総合判定: PASS / FAIL

   {各レビュワーのフィードバック}
   ```
   - 全員 PASS → `### 総合判定: PASS`
   - 1人でも FAIL → `### 総合判定: FAIL`
   - FAIL の場合、必須修正と推奨修正をまとめた「修正アクションリスト」も追記する

## 注意事項

- 8つの Agent は**必ず並列**で起動すること（1つのレスポンスで8つの Agent tool call）
- 各 Agent には `subagent_type` は指定せず、デフォルトの general-purpose を使う
- 各 Agent の prompt に記事全文とペルソナの内容を直接埋め込むこと（Agent はファイルを読めない前提で）
