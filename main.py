"""
宿泊施設の公式ホームページ有無を自動判定するアプリケーション

入力: 無題のスプレッドシート (14).xlsx（屋号、電話番号）
出力: 無題のスプレッドシート (14).xlsx（一番右の列に判定結果を追記）
"""

import os
import time
import pandas as pd
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()
API_KEY = os.getenv('BRAVE_API_KEY')
SEARCH_ENDPOINT = 'https://api.search.brave.com/res/v1/web/search'

# OTAドメインリスト（公式HPなしと判定するドメイン）
OTA_DOMAINS = [
    'rakuten.co.jp',
    'jalan.net',
    'booking.com',
    'expedia.com',
    'expedia.co.jp',
    'ikyu.com',
    'agoda.com'
]

# API呼び出し間隔（秒） - レート制限を避けるため
API_DELAY = 1.0


def load_excel(file_path):
    """
    Excelファイルを読み込む
    
    Args:
        file_path (str): 読み込むExcelファイルのパス
        
    Returns:
        pd.DataFrame: 読み込んだデータフレーム、エラー時はNone
    """
    try:
        print(f"📂 Excelファイルを読み込み中: {file_path}")
        df = pd.read_excel(file_path)
        
        # 必須カラムの存在確認
        required_columns = ['屋号', '電話番号']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"❌ エラー: 必須カラムが見つかりません: {missing_columns}")
            return None
        
        print(f"✅ {len(df)}件の施設データを読み込みました")
        return df
        
    except FileNotFoundError:
        print(f"❌ エラー: ファイルが見つかりません: {file_path}")
        return None
    except Exception as e:
        print(f"❌ Excelファイルの読み込み中にエラーが発生しました: {e}")
        return None


def search_official_site(query):
    """
    Brave Search APIを使用して検索を実行
    
    Args:
        query (str): 検索クエリ
        
    Returns:
        dict: APIレスポンスのJSONデータ、エラー時はNone
        
    Brave Search APIレスポンス構造:
        {
            "web": {
                "results": [
                    {
                        "url": "https://example.com",
                        "title": "ページタイトル",
                        "description": "ページの説明文"
                    },
                    ...
                ]
            }
        }
    """
    headers = {
        'Accept': 'application/json',
        'X-Subscription-Token': API_KEY
    }
    params = {
        'q': query,
        'count': 10  # 最大10件の検索結果を取得
    }
    
    try:
        response = requests.get(SEARCH_ENDPOINT, headers=headers, params=params, timeout=10)
        
        # エラーレスポンスの詳細を確認
        if response.status_code != 200:
            error_detail = response.text
            print(f"⚠️  APIエラー ({response.status_code}): {error_detail[:200]}")
            return None
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️  検索API呼び出しエラー: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   レスポンス: {e.response.text[:200]}")
        return None
    except Exception as e:
        print(f"⚠️  検索中に予期しないエラーが発生しました: {e}")
        return None


def judge_hp_existence(search_results):
    """
    検索結果から公式HPの有無を判定
    
    判定ロジック:
    1. 独自ドメイン（OTA以外）で「公式」「オフィシャル」を含む → HPあり
    2. 独自ドメインが1つでも見つかれば → HPあり
    3. OTAのみの場合は → HPなし
    4. 検索結果がない場合は → 不明
    
    Args:
        search_results (dict): Brave Search APIのレスポンス
        
    Returns:
        tuple: (HP有無, 判定理由, 検出URL)
            - HP有無: 'あり' / 'なし' / '不明'
            - 判定理由: '公式サイト検出' / 'OTAのみ' / '検索結果なし' / '不明'
            - 検出URL: 判定に使用したURL（見つからない場合はNone）
    """
    if not search_results:
        return '不明', '検索結果なし', None
    
    # APIレスポンス構造の確認
    if 'web' not in search_results:
        return '不明', '検索結果なし', None
    
    if 'results' not in search_results['web'] or not search_results['web']['results']:
        return '不明', '検索結果なし', None
    
    results = search_results['web']['results']
    ota_only = True  # OTAのみかどうかのフラグ
    official_domain_found = None  # 見つかった独自ドメインのURL
    
    for result in results:
        url = result.get('url', '')
        title = result.get('title', '')
        description = result.get('description', '')
        
        if not url:
            continue
        
        # URLからドメインを抽出
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace('www.', '').lower()
        except Exception:
            continue
        
        # OTAドメインかどうかをチェック
        is_ota = False
        for ota_domain in OTA_DOMAINS:
            if ota_domain in domain:
                is_ota = True
                break
        
        if is_ota:
            continue  # OTAドメインはスキップ
        
        # OTA以外のドメインが見つかった
        ota_only = False
        
        # タイトルや説明文に「公式」「オフィシャル」が含まれるかチェック
        text_to_check = (title + ' ' + description).lower()
        if '公式' in text_to_check or 'オフィシャル' in text_to_check or 'official' in text_to_check:
            return 'あり', '公式サイト検出', url
        
        # 独自ドメインが見つかったが、まだ公式キーワードは見つかっていない
        if official_domain_found is None:
            official_domain_found = url
    
    # 判定結果の決定
    if ota_only:
        return 'なし', 'OTAのみ', None
    elif official_domain_found:
        return 'あり', '公式サイト検出', official_domain_found
    else:
        return '不明', '不明', None


def save_excel(df, file_path):
    """
    結果をExcelファイルに保存
    
    Args:
        df (pd.DataFrame): 保存するデータフレーム
        file_path (str): 保存先のファイルパス
        
    Returns:
        bool: 保存成功時True、失敗時False
    """
    try:
        df.to_excel(file_path, index=False)
        print(f"✅ 結果を {file_path} に保存しました。")
        return True
    except Exception as e:
        print(f"❌ Excelファイルの保存中にエラーが発生しました: {e}")
        return False


def main():
    """メイン処理"""
    input_file = '無題のスプレッドシート (14).xlsx'
    output_file = '無題のスプレッドシート (14).xlsx'
    
    # APIキーの確認
    if not API_KEY:
        print("❌ エラー: BRAVE_API_KEYが設定されていません。.envファイルを確認してください。")
        return
    
    # Excelファイルの読み込み
    df = load_excel(input_file)
    if df is None:
        return
    
    # テスト用: 最初の10件のみ処理
    TEST_MODE = True
    TEST_LIMIT = 10
    
    if TEST_MODE:
        df = df.head(TEST_LIMIT)
        print(f"⚠️  テストモード: 最初の{TEST_LIMIT}件のみ処理します\n")
    
    # 結果カラム名を決定（一番右の列に追加）
    result_column = '公式HP有無'
    
    # 既に結果カラムが存在する場合は削除して再作成
    if result_column in df.columns:
        df = df.drop(columns=[result_column])
    
    # 結果カラムの初期化（一番右に追加）
    df[result_column] = ''
    
    total_count = len(df)
    print(f"\n🔍 {total_count}件の施設について検索を開始します...\n")
    
    # 各施設について検索・判定を実行
    for index, row in df.iterrows():
        facility_name = str(row['屋号'])
        
        # 検索クエリの生成（地域情報なしで検索）
        query = f"{facility_name} 公式サイト"
        
        print(f"[{index + 1}/{total_count}] 検索中: {query}")
        
        # 検索実行
        search_results = search_official_site(query)
        
        # 判定実行
        hp_existence, reason, detected_url = judge_hp_existence(search_results)
        
        # 結果を一番右の列に記録（「⇨はい」または「なし⇨いいえ」の形式）
        if hp_existence == 'あり':
            result_text = '⇨はい'
        elif hp_existence == 'なし':
            result_text = 'なし⇨いいえ'
        else:
            result_text = ''  # 不明の場合は空欄
        
        df.at[index, result_column] = result_text
        
        print(f"  → 判定結果: {result_text} ({reason})")
        
        # API呼び出し間隔を空ける（レート制限対策）
        if index < total_count - 1:  # 最後の1件は待機不要
            time.sleep(API_DELAY)
    
    print(f"\n💾 結果を保存中...")
    
    # 結果の保存（元のファイルを上書き）
    if save_excel(df, output_file):
        print(f"\n✨ 処理が完了しました！")
        print(f"   入力: {input_file}")
        print(f"   出力: {output_file}")
        
        # 結果のサマリーを表示
        summary = df[result_column].value_counts()
        print(f"\n📊 判定結果サマリー:")
        for status, count in summary.items():
            if status:  # 空欄以外のみ表示
                print(f"   {status}: {count}件")
        if '' in summary:
            print(f"   不明: {summary['']}件")


if __name__ == '__main__':
    main()

