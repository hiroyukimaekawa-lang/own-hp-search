# テレアポ営業用施設判定アプリケーション

CSVで渡された施設名リストから、公式HPの有無・簡易HPかどうか・対象都道府県かを自動判定し、営業対象リストを作成するWebアプリケーションです。

## 📋 機能

- CSVファイルから施設名リストを読み込み
- Google Places APIを使用して各施設の情報を自動検索
- 公式HPの有無を自動判定
- 簡易HPサービス（Wix/WordPress/Canva/ペライチ等）の判定
- 都道府県の自動抽出
- 営業対象の自動判定（沖縄県・離島を除外）
- 結果をCSVファイルでダウンロード

## 🚀 セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. Google Places APIキーの取得

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを作成または選択
3. 「APIとサービス」→「ライブラリ」から「Places API」を有効化
4. 「認証情報」からAPIキーを作成
5. プロジェクトルートに `.env` ファイルを作成し、以下を記述：

```
GOOGLE_PLACES_API_KEY=あなたのAPIキー
```

### 3. アプリケーションの起動

```bash
python main.py
```

または

```bash
uvicorn main:app --reload
```

ブラウザで `http://localhost:8000` にアクセスしてください。

## 📖 使い方

### 入力CSVファイル形式

- **A列（1列目）: 施設名（屋号）** - 必須

**入力CSV例:**
```csv
施設名
民宿 やしろ
ペンション シーガル
リゾートホテル ABC
```

### 出力CSVファイル形式

- **A列: 施設名** - 元データ
- **B列: 公式HPのURL** - 存在しない場合は空欄
- **C列: 営業対象か** - 「はい」または「いいえ」
- **D列: 都道府県名** - 抽出された都道府県名

**出力CSV例:**
```csv
施設名,公式HPのURL,営業対象か,都道府県名
民宿 やしろ,,はい,東京都
ペンション シーガル,https://example.com,いいえ,神奈川県
リゾートホテル ABC,https://wixsite.com/example,はい,静岡県
```

## 🎯 営業対象の定義

以下すべてを満たす場合「はい」と判定されます：

1. **公式HPが存在しない** OR **簡易HPサービスを使用している**
   - WordPress
   - Wix
   - Canva
   - ペライチ
   - Jimdo
   - その他の簡易HPサービス

2. **都道府県が沖縄県ではない**

3. **離島ではない**（沖縄県の離島含む）

## 🔍 判定ロジック

1. **施設名でGoogle Places API検索**
   - Googleビジネスプロフィールから情報を取得

2. **以下の情報を取得**
   - `website`（公式HP URL）
   - `formatted_address`（住所）

3. **住所から都道府県を抽出**
   - 正規表現を使用して都道府県名を抽出

4. **ウェブサイト判定**
   - URLドメインを解析
   - HTMLのmeta情報を解析（必要に応じて）

5. **離島判定**
   - 住所に離島キーワードが含まれているかチェック

6. **営業対象判定**
   - 上記の条件をすべてチェックして判定

## ⚙️ 技術スタック

- **Python 3.8+**
- **FastAPI** - Webフレームワーク
- **Google Places API** - 施設情報検索
- **requests** - HTTPリクエスト
- **pandas** - データ処理（将来の拡張用）
- **python-dotenv** - 環境変数管理

## 📝 簡易モード

HP判定が難しい場合は、「Googleビジネスプロフィール上にwebサイトが登録されていない施設のみ抽出」という簡易モードも利用できます。

- チェックボックスで簡易モードを選択可能
- 簡易モードでは、websiteが空の施設のみを「はい」と判定

## ⚠️ 注意事項

- Google Places APIには利用制限があります。大量のデータを処理する場合は、APIの利用制限にご注意ください
- API呼び出しの間隔を100ms空けていますが、必要に応じて調整してください
- 離島の判定は住所のキーワードベースで行っています。完全ではない場合があります
- 簡易HPの判定は、ドメインとHTMLのmeta情報を基に行っています

## 📁 ファイル構成

```
.
├── main.py              # FastAPIアプリケーション
├── requirements.txt     # 依存パッケージ一覧
├── templates/           # HTMLテンプレート
│   └── index.html
├── static/              # 静的ファイル（CSS等）
│   └── style.css
├── .env                 # 環境変数ファイル（作成必要）
└── README.md           # このファイル

```

## 🔧 開発

### ローカル開発環境の起動

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 本番環境へのデプロイ

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 🆓 無料版アプリケーション（API不使用）

APIキー不要で利用できる無料版アプリケーションも用意しています。

### 無料版の特徴

- **APIキー不要** - Google Places APIの設定不要
- **完全無料** - すべて無料ライブラリのみを使用
- **Google検索ベース** - 施設名 + "Google マップ"でGoogle検索を実行
- **HTMLスクレイピング** - GoogleビジネスプロフィールのHTMLを解析

### 無料版の起動方法

```bash
python main_free.py
```

または

```bash
uvicorn main_free:app --reload --port 8001
```

ブラウザで `http://localhost:8001` にアクセスしてください。

### 無料版の判定方法

1. **施設名 + " Google マップ" でGoogle検索**
   - Google検索結果ページを取得
   - GoogleビジネスプロフィールのページURLを抽出

2. **GoogleビジネスプロフィールのHTMLを取得**
   - 「ウェブサイト」リンクを抽出
   - 住所を抽出

3. **HP判定**
   - HPが存在しない場合 → 営業対象「はい」
   - HPが存在する場合、以下URLを含めば簡易HPとして「はい」
     - wixsite.com
     - wordpress.com
     - canva.site
     - peraichi.com
     - jimdosite.com
   - HTML内に「wp-content」「WordPress」が含まれる場合も簡易HP扱い

4. **住所判定**
   - 住所に「沖縄県」が含まれる場合は無条件で「いいえ」

### 無料版の技術スタック

- **Python 3.8+**
- **FastAPI** - Webフレームワーク
- **requests** - HTTPリクエスト
- **BeautifulSoup4** - HTMLパース
- **pandas** - データ処理

### 無料版の注意事項

- Google検索結果の取得が不安定になる可能性があります
- Google検索のレート制限に引っかかる可能性があります（1秒以上の間隔を推奨）
- HTMLの構造変更により動作しなくなる可能性があります
- 検索結果が見つからない場合、判定できないことがあります

### 無料版のファイル構成

```
.
├── main_free.py           # 無料版FastAPIアプリケーション
├── templates_free/        # 無料版HTMLテンプレート
│   └── index.html
├── static_free/           # 無料版静的ファイル（CSS等）
│   └── style.css
└── requirements.txt      # 依存パッケージ（beautifulsoup4含む）

```

---

## 📄 ライセンス

このプロジェクトは内部使用を目的としています。
