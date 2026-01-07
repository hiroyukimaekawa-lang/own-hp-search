# 宿泊施設公式サイト検索ツール

Next.js + TypeScriptで実装された、宿泊施設の公式サイトURLを自動検索するWebアプリケーションです。

## 機能

- CSVファイル（屋号カラム）をアップロード
- Brave Search APIを使用して各屋号の公式サイトを自動検索
- 除外ドメイン（OTAサイト、SNS等）を自動フィルタリング
- 結果をCSV形式でダウンロード

## セットアップ

### 1. 依存パッケージのインストール

```bash
npm install
```

### 2. 環境変数の設定

`.env.local`ファイルを作成し、Brave Search APIキーを設定してください：

```
BRAVE_API_KEY=your_api_key_here
```

### 3. 開発サーバーの起動

```bash
npm run dev
```

ブラウザで `http://localhost:3000` にアクセスしてください。

## 使い方

1. Brave Search APIキーを入力（または`.env.local`に設定）
2. 「屋号」カラムを含むCSVファイルをアップロード
3. 「検索を開始」ボタンをクリック
4. 処理完了後、「結果をダウンロード」ボタンでCSVをダウンロード

## 入力CSV形式

```csv
屋号
民宿 やしろ
ペンション シーガル
```

## 出力CSV形式

```csv
屋号,公式サイトURL
民宿 やしろ,https://example.com
ペンション シーガル,
```

## 検索仕様

以下の順序で検索クエリを試行します：

1. 「屋号 公式サイト」
2. 「屋号 宿」
3. 「屋号 ホームページ」

## 除外ドメイン

以下のドメインを含むURLは除外されます：

- jalan.net
- rakuten.co.jp
- booking.com
- agoda.com
- instagram.com
- facebook.com
- ameblo.jp
- fc2.com
- jimdo.com
- wixsite.com
- google.com

## 技術スタック

- Next.js 16 (App Router)
- TypeScript
- Tailwind CSS
- csv-parser
- Brave Search API

## ビルド

```bash
npm run build
npm start
```
