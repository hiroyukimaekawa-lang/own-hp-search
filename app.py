"""
テレアポ営業用施設判定アプリケーション（SerpAPI版）
Streamlit版
"""

import streamlit as st
import os
import re
import csv
import io
from typing import List, Dict, Optional
from dotenv import load_dotenv
import requests
from urllib.parse import urlparse
import time
from serpapi import GoogleSearch

# 環境変数の読み込み
load_dotenv()

# ページ設定
st.set_page_config(
    page_title="テレアポ営業対象リスト作成ツール",
    page_icon="🏨",
    layout="wide"
)

# API設定
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# 簡易HPサービスのドメインリスト
SIMPLE_HP_DOMAINS_FREE = [
    "wixsite.com",
    "wordpress.com",
    "canva.site",
    "peraichi.com",
    "jimdosite.com",
]

# 離島のキーワードリスト
ISLAND_KEYWORDS = [
    "離島", "島", "奄美", "沖永良部", "与論", "久米島", "宮古島", "石垣島",
    "西表島", "竹富島", "小浜島", "波照間島", "与那国島", "伊江島", "座間味島",
    "渡嘉敷島", "粟国島", "伊平屋島", "伊是名島", "北大東島", "南大東島",
    "多良間島", "水納島", "古宇利島", "瀬底島", "伊計島", "宮城島", "平安座島",
    "浜比嘉島", "津堅島", "久高島", "奥武島", "瀬長島",
]


def extract_prefecture(address: str) -> str:
    """住所から都道府県を抽出"""
    if not address:
        return ""
    
    prefecture_pattern = r"(北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県)"
    
    match = re.search(prefecture_pattern, address)
    if match:
        return match.group(1)
    
    return ""


def is_island(address: str) -> bool:
    """住所から離島かどうかを判定"""
    if not address:
        return False
    
    address_lower = address.lower()
    for keyword in ISLAND_KEYWORDS:
        if keyword in address_lower:
            return True
    
    return False


def is_simple_hp_free(url: str) -> bool:
    """URLが簡易HPサービスかどうかを判定"""
    if not url:
        return False

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")
        for simple_domain in SIMPLE_HP_DOMAINS_FREE:
            if simple_domain in domain:
                return True
        return False
    except Exception:
        return False


def check_website_technology_free(url: str) -> bool:
    """URLのHTMLを取得して、簡易HPサービスかどうかを判定"""
    if not url:
        return False

    if is_simple_hp_free(url):
        return True

    try:
        response = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        if response.status_code == 200:
            html_content = response.text.lower()

            if "wp-content" in html_content or "wordpress" in html_content:
                return True
            if "wixsite.com" in html_content or "wixstatic.com" in html_content:
                return True
            if "canva.site" in html_content or "canva.com" in html_content:
                return True
            if "peraichi.com" in html_content:
                return True
            if "jimdosite.com" in html_content or "jimdo" in html_content:
                return True

    except Exception:
        pass

    return False


def search_serpapi(facility_name: str, api_key: str) -> Optional[Dict]:
    """SerpAPIを使用して施設情報を取得"""
    if not api_key:
        return None
    
    query = f"{facility_name}"
    
    try:
        params = {
            "q": query,
            "api_key": api_key,
            "engine": "google",
            "hl": "ja",
            "gl": "jp",
            "location": "Japan",
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        website = ""
        address = ""
        
        # 検索結果からGoogleビジネスプロフィールの情報を取得
        if "local_results" in results:
            local_results = results["local_results"]
            if local_results and len(local_results) > 0:
                local_result = local_results[0]
                if "website" in local_result:
                    website = local_result["website"]
                if "address" in local_result:
                    address = local_result["address"]
        
        # ローカル結果がない場合、通常の検索結果から探す
        if not website and "organic_results" in results:
            organic_results = results["organic_results"]
            for result in organic_results:
                link = result.get("link", "")
                snippet = result.get("snippet", "")
                
                if "maps.google.com" in link or "google.com/maps" in link:
                    if snippet:
                        prefecture_match = re.search(r"([都道府県].*?[市区町村].*?[0-9])", snippet)
                        if prefecture_match:
                            address = prefecture_match.group(1)
                    break
        
        return {"website": website, "address": address}
    
    except Exception as e:
        st.error(f"SerpAPI検索エラー ({facility_name}): {e}")
        return None


def judge_target_serpapi(facility_name: str, website: str, address: str) -> Dict:
    """施設が営業対象かどうかを判定"""
    prefecture = extract_prefecture(address)
    
    # 沖縄県チェック
    if prefecture == "沖縄県":
        return {
            "facility_name": facility_name,
            "website": "",
            "is_target": "いいえ",
            "prefecture": prefecture,
            "reason": "沖縄県のため除外",
        }
    
    # 離島チェック
    if is_island(address):
        return {
            "facility_name": facility_name,
            "website": "",
            "is_target": "いいえ",
            "prefecture": prefecture,
            "reason": "離島のため除外",
        }
    
    # ウェブサイトが存在しない場合
    if not website or website.strip() == "":
        return {
            "facility_name": facility_name,
            "website": "",
            "is_target": "はい",
            "prefecture": prefecture,
            "reason": "公式HPなし",
        }
    
    # ウェブサイトが存在する場合、簡易HPかどうかをチェック
    is_simple = check_website_technology_free(website)
    
    if is_simple:
        return {
            "facility_name": facility_name,
            "website": website,
            "is_target": "はい",
            "prefecture": prefecture,
            "reason": "簡易HP使用",
        }
    else:
        return {
            "facility_name": facility_name,
            "website": website,
            "is_target": "いいえ",
            "prefecture": prefecture,
            "reason": "公式HPあり",
        }


def process_csv_file(uploaded_file, api_key: str):
    """CSVファイルを処理して結果を返す"""
    # CSVファイルを読み込み
    try:
        csv_content = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        csv_content = uploaded_file.read().decode("shift_jis")
    
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    
    if len(rows) < 1:
        st.error("CSVファイルが空です")
        return None
    
    # ヘッダー行をスキップ
    data_rows = rows[1:] if len(rows) > 1 else []
    
    # A列（施設名）を抽出
    facilities = []
    for row in data_rows:
        if len(row) > 0 and row[0].strip():
            facilities.append(row[0].strip())
    
    if not facilities:
        st.error("施設名が見つかりません")
        return None
    
    return facilities


# メインUI
st.title("🏨 テレアポ営業対象リスト作成ツール")
st.markdown("### 施設名リストから営業対象を自動判定")

# サイドバー
with st.sidebar:
    st.header("⚙️ 設定")
    serpapi_key = st.text_input(
        "SerpAPIキー",
        value=SERPAPI_KEY or "7f319edbccde7eaa91d73398346def20ddb65e7f0f13cedc32ba60b4b7ba762f",
        type="password",
        help="SerpAPIを使用するために必要です（無料プラン: 月100回まで利用可能）"
    )
    
    st.markdown("---")
    st.markdown("### 📋 使い方")
    st.markdown("""
    1. SerpAPIキーを入力（デフォルトで設定済み）
    2. CSVファイルをアップロード
    3. 「処理を開始」ボタンをクリック
    4. 結果をCSVファイルでダウンロード
    """)
    
    st.markdown("---")
    st.markdown("### 📝 CSV形式")
    st.markdown("**入力:** A列に施設名（屋号）")
    st.markdown("**出力:** 施設名、HP URL、営業対象、都道府県")

# メインコンテンツ
st.markdown("---")

# ファイルアップロード
uploaded_file = st.file_uploader(
    "CSVファイルをアップロード",
    type=["csv"],
    help="A列に施設名（屋号）が含まれているCSVファイルをアップロードしてください"
)

if uploaded_file is not None:
    if st.button("🚀 処理を開始", type="primary", use_container_width=True):
        # APIキーのチェック
        if not serpapi_key:
            st.error("SerpAPIキーを入力してください")
            st.stop()
        
        # CSVファイルを処理
        facilities = process_csv_file(uploaded_file, serpapi_key)
        
        if facilities:
            # 進捗バー
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 結果格納用
            results = []
            total = len(facilities)
            
            # 各施設について処理
            for idx, facility_name in enumerate(facilities):
                status_text.text(f"処理中: {idx + 1}/{total} - {facility_name}")
                progress_bar.progress((idx + 1) / total)
                
                # SerpAPIで検索実行
                place_info = search_serpapi(facility_name, serpapi_key)
                website = place_info.get("website", "") if place_info else ""
                address = place_info.get("address", "") if place_info else ""
                
                # 判定実行
                result = judge_target_serpapi(facility_name, website, address)
                results.append(result)
                
                # API制限対策
                if idx < total - 1:
                    time.sleep(1.0)
            
            # 結果を集計
            total_count = len(results)
            target_count = sum(1 for result in results if result.get("is_target") == "はい")
            non_target_count = total_count - target_count
            
            # 結果表示
            st.success(f"✅ 処理が完了しました！")
            
            # サマリー表示
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("総件数", f"{total_count}件")
            with col2:
                st.metric("営業対象", f"{target_count}件", delta=f"{target_count/total_count*100:.1f}%")
            with col3:
                st.metric("非対象", f"{non_target_count}件")
            
            # CSVを生成
            output = io.StringIO()
            writer = csv.writer(output)
            
            # ヘッダー
            writer.writerow(["施設名", "公式HPのURL", "営業対象か", "都道府県名"])
            
            # データ
            for result in results:
                writer.writerow([
                    result["facility_name"],
                    result.get("website", ""),
                    result.get("is_target", ""),
                    result.get("prefecture", ""),
                ])
            
            csv_content = output.getvalue()
            
            # ダウンロードボタン
            st.download_button(
                label="📥 結果をCSVダウンロード",
                data=csv_content.encode("utf-8-sig"),
                file_name="営業対象リスト.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            # 結果テーブル表示
            st.markdown("---")
            st.markdown("### 📊 処理結果")
            
            # データフレームに変換して表示
            import pandas as pd
            df = pd.DataFrame(results)
            df_display = df[["facility_name", "website", "is_target", "prefecture"]]
            df_display.columns = ["施設名", "公式HPのURL", "営業対象か", "都道府県名"]
            st.dataframe(df_display, use_container_width=True, height=400)
            
            # セッション状態に保存
            st.session_state['results'] = results
            st.session_state['csv_content'] = csv_content

# フッター
st.markdown("---")
st.markdown("### 📖 営業対象の判定条件")
st.markdown("""
- ✅ **営業対象「はい」**: 公式HPが存在しない、または簡易HPサービス（WordPress/Wix/Canva/ペライチ/Jimdo）を使用している
- ❌ **営業対象「いいえ」**: 公式HPがあり、かつ沖縄県・離島ではない
- 🚫 **除外**: 沖縄県または離島の施設は自動的に除外されます
""")

