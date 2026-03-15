# マスターCSV集約 + クロスラン重複排除

## Context
毎回の収集で別々のCSVが生成されるが、全データを1つのCSVに集約してgit管理したい。また、既に収集済みの投稿はAPIを叩かずスキップしたい。

## 方針
- **マスターCSV**: `data/reddit_master.csv`（git追跡される。`data/`は`.gitignore`に含まれていない）
- **収集用CSV**: `csv/YYYY-MM-DD-HH-MM.csv`（従来通り、gitignored）
- **重複判定キー**: URL（各投稿に一意、CSVカラムに既存）

## 処理フロー（変更後）

```
マスターCSVからURL一覧を読み込み → seen URLs セット
  ↓
各subredditのtop投稿を取得・フィルタ
  ↓
URL が seen URLs に含まれる → スキップ（API呼び出し前に判定）
  ↓
恋愛判定 → 全文取得 → row構築
  ↓
収集用CSVに保存（従来通り）
  ↓
マスターCSVに追記
```

## 変更内容

### 1. `FIELDNAMES` 定数を抽出
`save_to_csv` 内のローカル変数 → モジュールレベル定数に昇格。`save_to_csv` と新関数 `append_to_master` で共有。

### 2. `MASTER_CSV` 定数を追加
```python
MASTER_CSV = "data/reddit_master.csv"
```

### 3. `load_master_urls()` 関数を追加
- `MASTER_CSV` が存在すれば `URL` カラムの値をsetで返す
- 存在しなければ空setを返す

### 4. `append_to_master(rows)` 関数を追加
- ファイルが存在しなければヘッダー付きで新規作成
- 存在すればヘッダーなしで追記（`mode="a"`）

### 5. `main()` の変更（3箇所）
1. `seen_ids` の後に `master_urls = load_master_urls()` を追加
2. URL構築の直後、`try:` ブロックの前に、`url in master_urls` なら「収集済み」でスキップ（AI判定の前に置き、API呼び出しを節約）
3. `save_to_csv(all_rows)` の後に `append_to_master(all_rows)` を追加

### 6. 仕様書更新
- 処理フローにマスターCSV読み込み・追記を追加
- 重複排除セクションにクロスラン重複排除（URL照合）を追記
- マスターCSVセクションを追加

## 対象ファイル
- `collectors/reddit_collector.py` — メイン改修
- `docs/reddit_collector_spec.md` — 仕様更新

## 検証
```bash
# 1回目: マスターCSVが新規作成される
uv run python collectors/reddit_collector.py
# data/reddit_master.csv が存在し、ヘッダー + データ行があること

# 2回目: 収集済みURLはスキップされる
uv run python collectors/reddit_collector.py
# 「スキップ（収集済み）」のログが出ること
# マスターCSVに重複行が増えていないこと
```
