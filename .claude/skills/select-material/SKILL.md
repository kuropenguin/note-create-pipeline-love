---
name: select-material
description: reddit_master.csv から記事素材を選定し、記事企画書を作成する
allowed-tools: Read, Bash(python3 *), Bash(head *), Bash(wc *), Bash(mkdir *), Bash(ls *)
---

# 素材選定スキル

`data/reddit_master.csv` のサマリー済み記事から、note.com 記事にしやすい素材を選定し、企画書を作成する。

## 手順

1. `data/reddit_master.csv` を読み込み、**サマリーが入っている行のみ**を対象とする。

2. `data/article_log.csv` を読み込み、`元ネタRedditタイトル` カラムに記載済みのタイトルと一致する行を候補から除外する（同じ素材の重複記事化を防止）。

3. `$ARGUMENTS` の扱い：
   - キーワード指定あり → そのキーワードに関連する素材をフィルタ
   - 行番号指定あり → その行を直接使用
   - 指定なし → 記事化のしやすさ（◎ > ○ > △）と ups × upvote_ratio の複合スコアで上位5件を提示し、ユーザーに選択させる

4. 素材決定後、以下を含む**企画書**を作成する：
   - 元ネタの Reddit 投稿サマリー
   - 記事の切り口・テーマ
   - ターゲット読者
   - 提案タイトル（候補3つ）
   - slug（URL用の短い英語 or ローマ字）
   - 無料/有料の提案
   - 必要な画像の概要（3〜5枚）

5. フォルダ構成を作成：
   ```
   articles/<slug>/
   articles/<slug>/images/
   articles/<slug>/image-prompts/
   ```

6. 企画書を `articles/<slug>/plan.md` に保存する。

## 注意事項

- 元ネタの個人情報（ユーザー名、具体的な地名等）は企画書の段階から匿名化する
- slug は英数字とハイフンのみ（例：`love-after-breakup`）
- 既に `articles/` に同名フォルダがある場合は末尾に連番を付ける
- `data/article_log.csv` に記載済みの素材は自動的にスキップされる
