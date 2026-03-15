# note 記事作成パイプライン

## Context

Reddit の恋愛投稿データ（24,000件超）を元ネタに、note.com 向けの記事を自動生成するパイプラインを構築する。記事執筆・並列レビュー・修正・人間レビューの一連の流れを Claude Code のスキルとサブエージェントで実装する。

## フォルダ構成

```
articles/                          # 記事格納ディレクトリ（新規作成）
  <slug>/
    article.md                     # 記事本文
    plan.md                        # 記事企画（素材・方向性）
    review.md                      # レビュー結果
    revision-log.md                # 修正履歴
    images/                        # 記事画像（後で配置）
    image-prompts/                 # 画像生成プロンプト
      01-header.txt
      02-xxx.txt
      ...

.claude/skills/
  select-material/SKILL.md         # 素材選定スキル
  write-article/
    SKILL.md                       # 記事執筆スキル
    guidelines.md                  # バズる記事の書き方ガイドライン
    article-template.md            # 記事テンプレート
  review-article/
    SKILL.md                       # 並列レビュースキル
    reviewers/
      note-guidelines.md           # noteガイドライン準拠チェッカー
      ai-detection.md              # AI検出チェッカー
      reader-perspective.md        # 読者目線レビュワー
      female-empathy.md            # 女性共感レビュワー
  revise-article/SKILL.md          # 修正スキル
  article-pipeline/SKILL.md        # 全体オーケストレーター
```

## スキル一覧と責務

### 1. `/select-material` — 素材選定

- `data/reddit_master.csv` からサマリー済みの行を読み、記事にしやすい素材を提示
- `$ARGUMENTS` でキーワードや行番号を指定可能
- 選定後 `articles/<slug>/plan.md` に企画書を出力
- フォルダ構成（`images/`, `image-prompts/`）も同時に作成

### 2. `/write-article <slug>` — 記事執筆

- `articles/<slug>/plan.md` と元データを読み、`guidelines.md` に沿って記事を執筆
- `articles/<slug>/article.md` に出力
- 画像プロンプト（日本語）を `articles/<slug>/image-prompts/` に出力（3〜5枚分）

**`guidelines.md` に含めるバズ記事の書き方ルール：**

- タイトル：30文字以内、好奇心ギャップ、感情フック
- 冒頭：シーンか問いかけから始める（要約NG）
- 構成：問題→発見→気づき パターン
- 段落：短く（2〜3文）、スマホ読みを意識した改行
- 語調：会話的・体験談風（講義調NG）
- 避ける表現：「いかがでしたか」「〜と言えるでしょう」等の AI 臭い定型句
- 締め：スキ/フォローの CTA、1つの持ち帰りメッセージ
- 有料記事：無料部分で価値をチラ見せ、有料部分でユニークな洞察
- 文字数：無料 2,000〜4,000字、有料 3,000〜6,000字

### 3. `/review-article <slug>` — 並列レビュー（4人のAIレビュワー）

**Agent ツールで4つのサブエージェントを並列起動し、それぞれ異なる観点でレビュー：**

| レビュワー           | 観点                                                                  |
| -------------------- | --------------------------------------------------------------------- |
| noteガイドライン準拠 | 利用規約違反、差別、個人情報、出典の匿名化                            |
| AI検出チェッカー     | AI臭い表現、文体の単調さ、不自然な段落バランス（1-10スコア）          |
| 読者目線             | タイトルクリック率、冒頭のフック、最後まで読めるか、スキ/課金したいか |
| 女性共感             | 20-30代女性が共感できるか、上から目線でないか、友人にシェアしたいか   |

**フィードバック分類：**

- **必須修正**: 犯罪的内容、公序良俗違反、個人情報露出
- **推奨修正**: 読みやすさ、AI臭さ、バズパターン準拠
- **提案**: あると良い改善

結果を `articles/<slug>/review.md` に統合出力。

### 4. `/revise-article <slug>` — 修正

- `article.md` と `review.md` を読み、フィードバックを反映
- 必須修正は全て対応、推奨修正は判断して対応、提案は可能な範囲で
- `articles/<slug>/article.md` を上書き更新
- `articles/<slug>/revision-log.md` に変更内容を記録

### 5. `/article-pipeline` — 全体オーケストレーター

フロー：

```
素材選定 → 執筆 → [AIレビューループ] → [人間レビューループ] → 完了
```

1. `/select-material` で素材選定
2. `/write-article <slug>` で執筆
3. **AIレビューループ（自動）：**
   a. `/review-article <slug>` で並列レビュー
   b. 指摘あり → `/revise-article <slug>` で修正 → 3a に戻る
   c. 全レビュワーがパス → ループ終了
4. **人間レビュー：**
   a. 「AIレビュー全パスしました。記事を確認してください」と表示して停止
   b. ユーザーが「OK」→ commit & push して完了
   c. ユーザーがフィードバック → フィードバックに基づき修正 → 3a（AIレビュー）に戻る

**ポイント：人間レビューは AI レビューが全て通った後にのみ実施。人間の修正後も必ず AI レビューを再通過させる。**

各スキルは単独でも呼び出し可能。

## 実装順序

| Phase | 内容                                             | 作成ファイル                                                     |
| ----- | ------------------------------------------------ | ---------------------------------------------------------------- |
| 1     | `articles/` ディレクトリ作成、`.gitkeep` 配置    | `articles/.gitkeep`                                              |
| 2     | 執筆スキル作成（ガイドライン・テンプレート含む） | `write-article/SKILL.md`, `guidelines.md`, `article-template.md` |
| 3     | 素材選定スキル作成                               | `select-material/SKILL.md`                                       |
| 4     | レビュースキル作成（4つのペルソナファイル含む）  | `review-article/SKILL.md`, `reviewers/*.md`                      |
| 5     | 修正スキル作成                                   | `revise-article/SKILL.md`                                        |
| 6     | オーケストレータースキル作成                     | `article-pipeline/SKILL.md`                                      |
| 7     | `settings.local.json` 更新、動作確認             | `settings.local.json`                                            |

## 並列レビューの実装方法

`/review-article` の SKILL.md 内で Agent ツールを4回並列に呼び出す指示を記載：

```
4つの Agent を並列に起動し、それぞれのレビュワーペルソナで記事をレビューする。
各 Agent には記事本文とレビュー基準を渡し、構造化されたフィードバックを返させる。
全員の結果を review.md に統合する。
```

## 検証方法

1. `/select-material` を実行 → `articles/<slug>/plan.md` が生成されることを確認
2. `/write-article <slug>` を実行 → `article.md` と `image-prompts/*.txt` が生成されることを確認
3. `/review-article <slug>` を実行 → 4人のレビュー結果が `review.md` に統合されることを確認
4. `/revise-article <slug>` を実行 → 修正版 `article.md` と `revision-log.md` が生成されることを確認
5. `/article-pipeline` でエンドツーエンドの流れを確認

## 備考

- 画像の実際の生成は本パイプラインのスコープ外（プロンプトテキストの生成まで）
- `articles/` ディレクトリは git 追跡対象とする
