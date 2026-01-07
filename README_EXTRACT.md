# 宿泊施設向け営業リスト作成アプリ

CSVに記載された宿泊施設の屋号をもとに、「自社HPが存在しない施設のみ」を抽出し、営業用リストとしてCSV出力するPythonアプリケーションです。

## 機能

- CSVファイルから宿泊施設情報を読み込み
- Brave Search APIを使用して各施設の公式HPを自動検索
- HP有無を自動判定（OTAサイト、SNSサイトを除外）
- HPなしの施設のみを抽出してCSV出力

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

必要なパッケージ：
- requests
- python-dotenv

### 2. 環境変数の設定

プロジェクトルートに `.env` ファイルを作成し、Brave Search APIキーを設定してください：

```
BRAVE_API_KEY=your_api_key_here
```

### 3. 入力CSVファイルの準備

プロジェクトルートに `input.csv` を配置してください。

**必須カラム:**
- `facility_name`: 施設名（屋号）
- `phone_number`: 電話番号
- `website_url`: Googleマップ掲載URL（空欄可）

**入力CSV例:**
```csv
facility_name,phone_number,website_url
民宿 やしろ,090-1234-5678,
ペンション シーガル,080-9876-5432,https://example.com
```

## 使い方

```bash
python extract_no_hp.py
```

実行すると、以下の処理が行われます：

1. `input.csv` を読み込み
2. 各施設についてBrave Search APIで「{facility_name} 公式サイト」を検索
3. HP有無を判定
4. HPなしの施設のみを抽出
5. `output.csv` に結果を出力

## 出力CSV形式

**出力ファイル:** `output.csv`

**カラム構成:**
- `facility_name`: 施設名（屋号）
- `phone_number`: 電話番号
- `hp_status`: HP有無（必ず「なし」）
- `memo`: メモ（「公式HP未保有」）

**出力CSV例:**
```csv
facility_name,phone_number,hp_status,memo
民宿 やしろ,090-1234-5678,なし,公式HP未保有
```

## HP有無の判定ロジック

### HPなしと判定する条件

1. **検索結果がOTAのみの場合**
   - rakuten.co.jp
   - jalan.net
   - booking.com
   - agoda.com
   - ikyu.com

2. **Googleマップのwebsite_urlが空欄**

3. **SNSドメインのみ**
   - instagram.com
   - facebook.com
   - twitter.com
   - x.com
   - ameblo.jp
   - fc2.com
   - jimdo.com
   - wixsite.com
   - google.com

### HPありと判定する条件

- 上記以外の独自ドメインが存在する場合

## 処理フロー

1. CSVファイルを読み込み
2. 各施設についてBrave Search APIで検索
3. 検索結果からHP有無を判定
4. HPなしの施設のみを抽出
5. 結果をCSVファイルに出力

## 注意事項

- API呼び出しにはレート制限があるため、各検索の間に1秒の待機時間を設けています
- 大量のデータを処理する場合は、APIの利用制限にご注意ください
- エラーが発生しても処理は継続され、該当施設はHPなしとして扱われます

## ファイル構成

```
.
├── extract_no_hp.py      # メインスクリプト
├── input.csv            # 入力CSVファイル（ユーザーが準備）
├── output.csv           # 出力CSVファイル（自動生成）
├── .env                 # 環境変数ファイル（ユーザーが作成）
└── requirements.txt     # 依存パッケージ一覧
```

