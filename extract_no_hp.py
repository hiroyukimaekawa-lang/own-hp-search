"""
宿泊施設向け営業リスト作成アプリ

CSVに記載された宿泊施設の屋号をもとに、
「自社HPが存在しない施設のみ」を抽出し、営業用リストとしてCSV出力する
"""

import os
import csv
import time
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv
from typing import Optional, List, Dict

# 環境変数の読み込み
load_dotenv()
API_KEY = os.getenv('BRAVE_API_KEY')
SEARCH_ENDPOINT = 'https://api.search.brave.com/res/v1/web/search'

# OTAドメインリスト
OTA_DOMAINS = [
    'rakuten.co.jp',
    'jalan.net',
    'booking.com',
    'agoda.com',
    'ikyu.com',
]

# SNSドメインリスト
SNS_DOMAINS = [
    'instagram.com',
    'facebook.com',
    'twitter.com',
    'x.com',
    'ameblo.jp',
    'fc2.com',
    'jimdo.com',
    'wixsite.com',
    'google.com',
]

# API呼び出し間隔（秒）
API_DELAY = 1.0


def search_official_site(facility_name: str) -> Optional[dict]:
    """
    Brave Search APIを使用して公式サイトを検索
    
    Args:
        facility_name: 施設名（屋号）
        
    Returns:
        APIレスポンスのJSONデータ、エラー時はNone
    """
    if not API_KEY:
        print("⚠️  APIキーが設定されていません")
        return None
    
    query = f"{facility_name} 公式サイト"
    
    headers = {
        'Accept': 'application/json',
        'X-Subscription-Token': API_KEY
    }
    params = {
        'q': query,
        'count': 10
    }
    
    try:
        response = requests.get(SEARCH_ENDPOINT, headers=headers, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"⚠️  APIエラー ({response.status_code}): {facility_name}")
            return None
        
        return response.json()
    except Exception as e:
        print(f"⚠️  検索エラー ({facility_name}): {e}")
        return None


def extract_domain(url: str) -> str:
    """
    URLからドメインを抽出
    
    Args:
        url: URL文字列
        
    Returns:
        ドメイン名（www.を除去、小文字化）
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '').lower()
        return domain
    except Exception:
        return ''


def is_ota_domain(url: str) -> bool:
    """
    OTAドメインかどうかを判定
    
    Args:
        url: URL文字列
        
    Returns:
        OTAドメインの場合True
    """
    domain = extract_domain(url)
    return any(ota_domain in domain for ota_domain in OTA_DOMAINS)


def is_sns_domain(url: str) -> bool:
    """
    SNSドメインかどうかを判定
    
    Args:
        url: URL文字列
        
    Returns:
        SNSドメインの場合True
    """
    domain = extract_domain(url)
    return any(sns_domain in domain for sns_domain in SNS_DOMAINS)


def judge_hp_existence(search_results: Optional[dict], website_url: str) -> str:
    """
    HP有無を判定
    
    判定ロジック:
    - 検索結果がOTAのみ → HPなし
    - Googleマップのwebsite_urlが空欄 → HPなし
    - SNSドメインのみ → HPなし
    - 上記以外の独自ドメインが存在 → HPあり
    
    Args:
        search_results: Brave Search APIのレスポンス
        website_url: Googleマップ掲載URL
        
    Returns:
        'あり' または 'なし'
    """
    # Googleマップのwebsite_urlが空欄の場合はHPなし
    if not website_url or website_url.strip() == '':
        return 'なし'
    
    # 検索結果がない場合は判定不能だが、website_urlが空欄なのでHPなし
    if not search_results:
        return 'なし'
    
    # APIレスポンス構造の確認
    if 'web' not in search_results:
        return 'なし'
    
    if 'results' not in search_results['web'] or not search_results['web']['results']:
        return 'なし'
    
    results = search_results['web']['results']
    
    # 検索結果を分類
    ota_only = True  # OTAのみかどうかのフラグ
    has_official_domain = False  # 独自ドメインが存在するか
    
    for result in results:
        url = result.get('url', '')
        if not url:
            continue
        
        # OTAドメインかチェック
        if is_ota_domain(url):
            continue  # OTAドメインはスキップ
        
        # SNSドメインかチェック
        if is_sns_domain(url):
            continue  # SNSドメインもスキップ
        
        # OTAでもSNSでもない独自ドメインが見つかった
        ota_only = False
        has_official_domain = True
        break  # 1つでも見つかれば十分
    
    # 判定結果
    if ota_only:
        # OTAのみの場合はHPなし
        return 'なし'
    elif has_official_domain:
        # 独自ドメインが存在する場合はHPあり
        return 'あり'
    else:
        # 検索結果がない場合もHPなし
        return 'なし'


def load_csv(input_file: str) -> List[Dict[str, str]]:
    """
    CSVファイルを読み込む
    
    Args:
        input_file: 入力CSVファイルのパス
        
    Returns:
        施設データのリスト
    """
    facilities = []
    
    try:
        with open(input_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                facilities.append({
                    'facility_name': row.get('facility_name', '').strip(),
                    'phone_number': row.get('phone_number', '').strip(),
                    'website_url': row.get('website_url', '').strip(),
                })
        
        print(f"✅ {len(facilities)}件の施設データを読み込みました")
        return facilities
    except FileNotFoundError:
        print(f"❌ エラー: ファイルが見つかりません: {input_file}")
        return []
    except Exception as e:
        print(f"❌ CSV読み込みエラー: {e}")
        return []


def save_csv(facilities: List[Dict[str, str]], output_file: str):
    """
    CSVファイルに保存
    
    Args:
        facilities: 施設データのリスト
        output_file: 出力CSVファイルのパス
    """
    try:
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = ['facility_name', 'phone_number', 'hp_status', 'memo']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for facility in facilities:
                writer.writerow({
                    'facility_name': facility['facility_name'],
                    'phone_number': facility['phone_number'],
                    'hp_status': 'なし',
                    'memo': '公式HP未保有'
                })
        
        print(f"✅ 結果を {output_file} に保存しました")
    except Exception as e:
        print(f"❌ CSV保存エラー: {e}")


def main():
    """メイン処理"""
    input_file = 'input.csv'
    output_file = 'output.csv'
    
    # APIキーの確認
    if not API_KEY:
        print("❌ エラー: BRAVE_API_KEYが設定されていません。.envファイルを確認してください。")
        return
    
    # CSVファイルの読み込み
    facilities = load_csv(input_file)
    if not facilities:
        return
    
    # HPなしの施設のみを抽出
    no_hp_facilities = []
    total_count = len(facilities)
    
    print(f"\n🔍 {total_count}件の施設についてHP有無を判定します...\n")
    
    for i, facility in enumerate(facilities, 1):
        facility_name = facility['facility_name']
        website_url = facility['website_url']
        
        print(f"[{i}/{total_count}] 処理中: {facility_name}")
        
        try:
            # 公式サイトを検索
            search_results = search_official_site(facility_name)
            
            # HP有無を判定
            hp_status = judge_hp_existence(search_results, website_url)
            
            # HPなしの施設のみを抽出
            if hp_status == 'なし':
                no_hp_facilities.append(facility)
                print(f"  → HPなし（抽出対象）")
            else:
                print(f"  → HPあり（スキップ）")
            
        except Exception as e:
            print(f"  ⚠️  エラー: {e}")
            # エラーが起きても処理を続ける（エラー時はHPなしとして扱う）
            no_hp_facilities.append(facility)
        
        # API呼び出し間隔を空ける（最後の1件は不要）
        if i < total_count:
            time.sleep(API_DELAY)
    
    print(f"\n📊 抽出結果:")
    print(f"   HPなし（抽出対象）: {len(no_hp_facilities)}件")
    print(f"   HPあり（除外）: {total_count - len(no_hp_facilities)}件")
    
    # 結果をCSVに保存
    if no_hp_facilities:
        save_csv(no_hp_facilities, output_file)
        print(f"\n✨ 処理が完了しました！")
        print(f"   入力: {input_file}")
        print(f"   出力: {output_file}")
    else:
        print(f"\n⚠️  HPなしの施設が見つかりませんでした")


if __name__ == '__main__':
    main()

