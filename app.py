"""
Streamlitアプリ: 宿泊施設の公式ホームページ検索ツール
"""

import os
import time
import pandas as pd
import requests
from urllib.parse import urlparse
import streamlit as st
from io import BytesIO
import csv

# ページ設定
st.set_page_config(
    page_title="宿泊施設HP検索ツール",
    page_icon="🏨",
    layout="wide"
)

# OTAドメインリスト
OTA_DOMAINS = [
    'jalan.net',
    'rakuten.co.jp',
    'booking.com',
    'agoda.com',
    'ikyu.com',
    'expedia.com',
    'expedia.co.jp',
]

# SNS・その他除外ドメインリスト（航空会社、予約サイトなど）
EXCLUDED_DOMAINS = [
    'instagram.com',
    'facebook.com',
    'twitter.com',
    'x.com',
    'ameblo.jp',
    'fc2.com',
    'jimdo.com',
    'wixsite.com',
    'google.com',
    'jal.co.jp',  # JAL予約サイト
    'ana.co.jp',  # ANA予約サイト
    'japanican.com',  # ジャパニカン
    'relux.com',  # るるぶトラベル
    'yadoplace.com',  # やどぷら
]

# 検索クエリのパターン
SEARCH_QUERIES = [
    lambda name: f"{name} 公式サイト",
    lambda name: f"{name} 宿",
    lambda name: f"{name} ホームページ",
]


def extract_domain(url: str) -> str:
    """URLからドメインを抽出"""
    try:
        parsed = urlparse(url)
        return parsed.netloc.replace('www.', '').lower()
    except Exception:
        return ''


def is_ota_domain(url: str) -> bool:
    """OTAドメインかどうかを判定"""
    domain = extract_domain(url)
    return any(ota_domain in domain for ota_domain in OTA_DOMAINS)


def is_excluded_domain(url: str) -> bool:
    """除外ドメインかどうかを判定"""
    domain = extract_domain(url)
    return any(excluded in domain for excluded in EXCLUDED_DOMAINS)


def search_brave_api(query: str, api_key: str):
    """Brave Search APIで検索を実行"""
    headers = {
        'Accept': 'application/json',
        'X-Subscription-Token': api_key
    }
    params = {
        'q': query,
        'count': 10
    }
    
    try:
        response = requests.get(
            'https://api.search.brave.com/res/v1/web/search',
            headers=headers,
            params=params,
            timeout=10
        )
        
        if response.status_code != 200:
            return None
        
        return response.json()
    except Exception:
        return None


def extract_sites(search_results, facility_name: str = ''):
    """検索結果から自社HPとOTAサイトを分けて抽出（厳格な判定）"""
    result = {
        'official_site': None,
        'ota_sites': []
    }
    
    if not search_results or 'web' not in search_results:
        return result
    
    if 'results' not in search_results['web'] or not search_results['web']['results']:
        return result
    
    results = search_results['web']['results']
    facility_name_lower = facility_name.lower().replace(' ', '').replace('　', '')
    
    for item in results:
        url = item.get('url', '')
        title = item.get('title', '')
        description = item.get('description', '')
        
        if not url:
            continue
        
        # SNS・その他除外ドメインをスキップ
        if is_excluded_domain(url):
            continue
        
        # OTAドメインかチェック
        if is_ota_domain(url):
            if url not in result['ota_sites']:
                result['ota_sites'].append(url)
            continue
        
        # 自社HPの厳格な判定
        # 1. タイトルや説明文に「公式」「オフィシャル」が含まれるか
        text_to_check = (title + ' ' + description).lower()
        has_official_keyword = (
            '公式' in text_to_check or 
            'オフィシャル' in text_to_check or 
            'official' in text_to_check
        )
        
        # 2. 施設名がドメインやURLに含まれているか（簡易チェック）
        domain = extract_domain(url)
        url_lower = url.lower()
        has_facility_name = False
        if facility_name_lower:
            # 施設名の主要部分（最初の3文字以上）がドメインに含まれるか
            facility_keywords = [
                facility_name_lower[:min(5, len(facility_name_lower))],
                facility_name_lower.replace('ペンション', '').replace('民宿', '').replace('ホテル', '').strip()[:min(5, len(facility_name_lower))]
            ]
            for keyword in facility_keywords:
                if len(keyword) >= 3 and keyword in domain:
                    has_facility_name = True
                    break
        
        # 自社HPとして採用する条件（厳格）
        # 条件1: 「公式」「オフィシャル」キーワードがある
        # 条件2: 施設名がドメインに含まれている
        # どちらか一方でも満たせば自社HPと判定（ただし、より厳格にする場合は両方を満たす必要がある）
        if has_official_keyword or has_facility_name:
            if not result['official_site']:
                result['official_site'] = url
        # どちらの条件も満たさない場合は、OTAサイトとして扱わずにスキップ
        # （自社HPとして採用しない）
    
    return result


def search_sites(facility_name: str, api_key: str):
    """屋号から自社HPとOTAサイトを検索"""
    best_result = {
        'official_site': None,
        'ota_sites': []
    }
    
    # 各検索クエリを順番に試す
    for query_func in SEARCH_QUERIES:
        query = query_func(facility_name)
        search_results = search_brave_api(query, api_key)
        extracted = extract_sites(search_results, facility_name)
        
        # 自社HPが見つかった場合は終了
        if extracted['official_site']:
            return {
                'official_site': extracted['official_site'],
                'ota_sites': list(set(best_result['ota_sites'] + extracted['ota_sites']))
            }
        
        # OTAサイトを蓄積
        best_result['ota_sites'].extend(extracted['ota_sites'])
        
        # API制限を考慮して少し待機
        time.sleep(1.0)
    
    # OTAサイトの重複を除去
    best_result['ota_sites'] = list(set(best_result['ota_sites']))
    
    return best_result


def main():
    st.title("🏨 宿泊施設公式サイト検索ツール")
    st.markdown("---")
    
    # サイドバー: 設定
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # APIキー入力
        api_key = st.text_input(
            "Brave Search APIキー",
            type="password",
            help="Brave Search APIのキーを入力してください"
        )
        
        # 環境変数からも取得を試みる
        if not api_key:
            api_key = os.getenv('BRAVE_API_KEY', '')
        
        # 処理件数制限
        limit_count = st.number_input(
            "処理件数（テスト用）",
            min_value=1,
            max_value=1000,
            value=10,
            help="処理する件数を指定してください（テスト時は少なめに設定）"
        )
        
        # API呼び出し間隔
        api_delay = st.slider(
            "API呼び出し間隔（秒）",
            min_value=0.5,
            max_value=5.0,
            value=1.0,
            step=0.5,
            help="API呼び出しの間隔を設定（レート制限対策）"
        )
    
    # メインエリア
    st.header("📤 CSVファイルアップロード")
    
    # CSV形式の説明
    with st.expander("📋 CSVファイル形式について", expanded=False):
        st.markdown("""
        **入力CSVファイル形式:**
        - **A列（1列目）: 屋号** - 宿泊施設の名前（必須）
        - 他のカラム（電話番号、website_urlなど）は任意です
        
        **出力CSVファイル形式:**
        - **A列: 屋号** - 施設名
        - **B列: 自社HP** - 見つかった自社の公式サイトURL（見つからない場合は空欄）
        - **C列: 他OTAなどのサイト** - OTAサイトなどのURL（見つからない場合は空欄、複数ある場合はセミコロン区切り）
        """)
    
    uploaded_file = st.file_uploader(
        "CSVファイルをアップロードしてください",
        type=['csv'],
        help="必須カラム: 屋号（A列）"
    )
    
    if uploaded_file is not None:
        try:
            # CSVファイルの読み込み
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            
            # 必須カラムの確認（A列目を確認）
            first_column = df.columns[0]
            if '屋号' not in first_column and '屋号' not in df.columns:
                # A列の値を「屋号」として扱う
                df = df.rename(columns={first_column: '屋号'})
            
            # 屋号カラムの確認
            if '屋号' not in df.columns:
                st.error("❌ CSVファイルのA列（1列目）に「屋号」カラムが必要です")
                st.info("現在のカラム: " + ", ".join(df.columns.tolist()))
            else:
                st.success(f"✅ {len(df)}件の施設データを読み込みました")
                
                # データプレビュー
                with st.expander("📊 データプレビュー", expanded=False):
                    st.dataframe(df.head(10))
                
                # 実行ボタン
                if not api_key or api_key == "":
                    st.warning("⚠️ APIキーを入力してください（サイドバーで設定）")
                else:
                    if st.button("🚀 検索処理を開始", type="primary", use_container_width=True):
                        # 処理件数を制限
                        df_processed = df.head(limit_count).copy()
                        
                        # 結果カラムの初期化
                        if '自社HP' in df_processed.columns:
                            df_processed = df_processed.drop(columns=['自社HP'])
                        if '他OTAなどのサイト' in df_processed.columns:
                            df_processed = df_processed.drop(columns=['他OTAなどのサイト'])
                        
                        df_processed['自社HP'] = ''
                        df_processed['他OTAなどのサイト'] = ''
                        
                        # プログレスバー
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        total_count = len(df_processed)
                        
                        # 各施設について検索・判定を実行
                        for idx, (index, row) in enumerate(df_processed.iterrows()):
                            facility_name = str(row['屋号'])
                            
                            # 進捗表示
                            progress = (idx + 1) / total_count
                            progress_bar.progress(progress)
                            status_text.text(f"処理中: {idx + 1}/{total_count} - {facility_name}")
                            
                            try:
                                # 検索実行
                                sites = search_sites(facility_name, api_key)
                                
                                # 結果を記録
                                df_processed.at[index, '自社HP'] = sites['official_site'] or ''
                                df_processed.at[index, '他OTAなどのサイト'] = '; '.join(sites['ota_sites']) if sites['ota_sites'] else ''
                                
                            except Exception as e:
                                st.warning(f"⚠️ エラー ({facility_name}): {e}")
                                df_processed.at[index, '自社HP'] = ''
                                df_processed.at[index, '他OTAなどのサイト'] = ''
                            
                            # API呼び出し間隔
                            if idx < total_count - 1:
                                time.sleep(api_delay)
                        
                        # 完了メッセージ
                        progress_bar.progress(1.0)
                        status_text.text("✅ 処理が完了しました！")
                        
                        # 結果表示
                        st.header("📊 検索結果")
                        
                        # サマリー
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            hp_count = (df_processed['自社HP'] != '').sum()
                            st.metric("自社HPあり", hp_count)
                        with col2:
                            ota_count = (df_processed['他OTAなどのサイト'] != '').sum()
                            st.metric("OTAサイトあり", ota_count)
                        with col3:
                            no_site = ((df_processed['自社HP'] == '') & (df_processed['他OTAなどのサイト'] == '')).sum()
                            st.metric("サイトなし", no_site)
                        
                        # 結果テーブル（A列: 屋号、B列: 自社HP、C列: 他OTAなどのサイトのみ表示）
                        result_df = df_processed[['屋号', '自社HP', '他OTAなどのサイト']].copy()
                        st.dataframe(result_df, use_container_width=True)
                        
                        # CSVダウンロードボタン
                        csv_output = result_df.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📥 結果をCSVダウンロード",
                            data=csv_output,
                            file_name="検索結果.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        
        except Exception as e:
            st.error(f"❌ エラーが発生しました: {e}")
            st.exception(e)


if __name__ == '__main__':
    main()
