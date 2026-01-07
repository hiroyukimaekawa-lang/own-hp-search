# 宿泊施設公式HP判定ツール

宿泊施設リストから公式ホームページの有無を自動判定し、テレアポ用リストの優先順位付けを行うPythonアプリケーションです。

## 📋 機能

- Excel/CSVファイルから宿泊施設情報を読み込み
- Brave Search APIを使用して各施設の公式HPを自動検索
- OTAサイトと公式サイトを自動判別
- 判定結果をExcelファイルに出力

## 🚀 セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. Brave Search APIキーの取得

1. [Brave Search API](https://brave.com/search/api/) にアクセス
2. APIキーを取得
3. プロジェクトルートに `.env` ファイルを作成し、以下を記述：

```
BRAVE_API_KEY=あなたのAPIキー
```

### 3. 入力ファイルの準備

プロジェクトルートに `facilities.xlsx` を配置してください。

**必須カラム:**
- `施設名`: 宿泊施設の名前
- `地域`: 都道府県または市区町村
- `電話番号`: 施設の電話番号

## 📖 使い方

```bash
python main.py
```

実行すると、`facilities.xlsx` を読み込み、各施設について公式HPの有無を判定し、結果を `facilities_checked.xlsx` に保存します。

## 📤 出力ファイル

`facilities_checked.xlsx` には以下のカラムが追加されます：

- **HP有無**: `あり` / `なし` / `不明`
- **判定理由**: `公式サイト検出` / `OTAのみ` / `検索結果なし` / `不明`
- **検出URL**: 判定に使用したURL（見つからない場合は空欄）

## 🔍 判定ロジック

1. 検索クエリを生成: `{施設名} {地域} 公式サイト`
2. Brave Search APIで検索を実行
3. 検索結果を以下のルールで分類：
   - **OTAサイト**: rakuten.co.jp, jalan.net, booking.com, expedia.*, ikyu.com, agoda.com
   - **公式サイト**: 独自ドメインで、タイトルや説明に「公式」「オフィシャル」が含まれる
4. 判定結果を決定：
   - 独自ドメインが1つでも見つかれば「HPあり」
   - OTAのみの場合は「HPなし」
   - 検索結果がない場合は「不明」

## ⚙️ 技術スタック

- Python 3.8+
- pandas: Excelファイルの読み書き
- requests: HTTPリクエスト
- python-dotenv: 環境変数管理
- Brave Search API: Web検索

## 📝 注意事項

- API呼び出しにはレート制限があるため、各検索の間に1秒の待機時間を設けています
- 大量のデータを処理する場合は、APIの利用制限にご注意ください
- エラーが発生しても処理は継続され、該当施設の判定結果は「不明」となります

