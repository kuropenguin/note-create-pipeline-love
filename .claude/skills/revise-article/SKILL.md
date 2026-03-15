---
name: revise-article
description: レビュー結果に基づき記事を修正する
allowed-tools: Read
---

# 記事修正スキル

`articles/<slug>/review.md` のフィードバックに基づき、記事を修正する。

## 手順

1. `$ARGUMENTS` から slug を取得する（例：`/revise-article love-after-breakup`）。

2. 以下のファイルを読み込む：
   - `articles/<slug>/article.md`（現在の記事）
   - `articles/<slug>/review.md`（レビュー結果）
   - `.claude/skills/write-article/guidelines.md`（執筆ガイドライン — 修正時も参照）

3. `review.md` の総合判定を確認する：
   - `PASS` の場合：推奨修正・提案のみ対応。軽微な修正で済む。
   - `FAIL` の場合：必須修正を**全て**対応する。推奨修正も積極的に対応する。

4. 修正方針：
   - **必須修正（MUST FIX）**: 全て対応する。対応しないという選択肢はない。
   - **推奨修正（SHOULD FIX）**: 記事の品質向上に寄与するものは対応する。ただし過度な修正で記事の個性を消さない。
   - **提案（SUGGESTION）**: 記事を改善するものは取り入れる。無理に全部取り入れない。

5. 修正後の記事を `articles/<slug>/article.md` に上書き保存する。

6. `articles/<slug>/revision-log.md` に修正内容を追記する：

```markdown
## 修正 {日時}

### 対応した指摘
- [{レビュワー名}] {指摘内容} → {どう修正したか}

### 対応しなかった指摘（理由付き）
- [{レビュワー名}] {指摘内容} → {対応しなかった理由}
```

7. 修正完了を報告する。修正箇所の概要を簡潔に述べる。

## 注意事項

- 修正で新たな問題を生まないこと（AI 臭い表現を増やさない等）
- 修正は最小限に。記事全体を書き直さず、指摘された箇所をピンポイントで修正する
- 画像プロンプトの修正が必要な場合は `image-prompts/` 内のファイルも更新する
