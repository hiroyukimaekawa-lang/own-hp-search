"""
テレアポ営業用施設判定アプリケーション（SerpAPI版）
SerpAPIを使用してGoogle検索結果を取得し、施設情報を判定
"""

import os
import re
import csv
import io
from typing import List, Dict, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from dotenv import load_dotenv
import requests
from urllib.parse import urlparse
import time
from serpapi import GoogleSearch

# 環境変数の読み込み
load_dotenv()

app = FastAPI(title="テレアポ営業用施設判定アプリ（SerpAPI版）")

# 静的ファイルとテンプレートの設定
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# API設定
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# 簡易HPサービスのドメインリスト（SerpAPI版）
SIMPLE_HP_DOMAINS_FREE = [
    "wixsite.com",
    "wordpress.com",
    "canva.site",
    "peraichi.com",
    "jimdosite.com",
]

# 離島のキーワードリスト
ISLAND_KEYWORDS = [
    "離島",
    "島",
    "奄美",
    "沖永良部",
    "与論",
    "久米島",
    "宮古島",
    "石垣島",
    "西表島",
    "竹富島",
    "小浜島",
    "波照間島",
    "与那国島",
    "伊江島",
    "座間味島",
    "渡嘉敷島",
    "粟国島",
    "伊平屋島",
    "伊是名島",
    "北大東島",
    "南大東島",
    "多良間島",
    "水納島",
    "古宇利島",
    "瀬底島",
    "伊計島",
    "宮城島",
    "平安座島",
    "浜比嘉島",
    "津堅島",
    "久高島",
    "奥武島",
    "瀬長島",
]


def extract_prefecture(address: str) -> str:
    """
    住所から都道府県を抽出
    
    Args:
        address: 住所文字列
        
    Returns:
        都道府県名（見つからない場合は空文字）
    """
    if not address:
        return ""
    
    # 都道府県のパターン
    prefecture_pattern = r"(北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県)"
    
    match = re.search(prefecture_pattern, address)
    if match:
        return match.group(1)
    
    return ""


def is_island(address: str) -> bool:
    """
    住所から離島かどうかを判定
    
    Args:
        address: 住所文字列
        
    Returns:
        離島の場合True
    """
    if not address:
        return False
    
    address_lower = address.lower()
    
    # 離島キーワードが含まれているかチェック
    for keyword in ISLAND_KEYWORDS:
        if keyword in address_lower:
            return True
    
    return False


def is_simple_hp(url: str) -> bool:
    """
    URLが簡易HPサービスかどうかを判定（Google Places API版）

    Args:
        url: ウェブサイトURL

    Returns:
        簡易HPサービスの場合True
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")

        # 簡易HPサービスのドメインかチェック
        for simple_domain in SIMPLE_HP_DOMAINS:
            if simple_domain in domain:
                return True

        return False
    except Exception:
        return False


def is_simple_hp_free(url: str) -> bool:
    """
    URLが簡易HPサービスかどうかを判定

    Args:
        url: ウェブサイトURL

    Returns:
        簡易HPサービスの場合True
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")

        # 簡易HPサービスのドメインかチェック
        for simple_domain in SIMPLE_HP_DOMAINS_FREE:
            if simple_domain in domain:
                return True

        return False
    except Exception:
        return False


def check_website_technology_free(url: str) -> bool:
    """
    URLのHTMLを取得して、簡易HPサービスかどうかを判定

    Args:
        url: ウェブサイトURL

    Returns:
        簡易HPサービスの場合True
    """
    if not url:
        return False

    # まずドメインベースの判定
    if is_simple_hp_free(url):
        return True

    # HTMLを取得してmeta情報をチェック
    try:
        response = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        if response.status_code == 200:
            html_content = response.text.lower()

            # WordPress判定（wp-contentまたはWordPressが含まれる）
            if "wp-content" in html_content or "wordpress" in html_content:
                return True

            # Wix判定
            if "wixsite.com" in html_content or "wixstatic.com" in html_content:
                return True

            # Canva判定
            if "canva.site" in html_content or "canva.com" in html_content:
                return True

            # ペライチ判定
            if "peraichi.com" in html_content:
                return True

            # Jimdo判定
            if "jimdosite.com" in html_content or "jimdo" in html_content:
                return True

    except Exception:
        # エラーが発生した場合は、ドメインベースの判定結果を返す
        pass

    return False


    """
    無料版：Google検索を使用して施設情報を取得（簡易版）

    Args:
        facility_name: 施設名

    Returns:
        施設情報の辞書（website, address）またはNone
    """
    query = f"{facility_name} 施設"

    try:
        # Google検索を実行
        response = requests.get(
            "https://www.google.com/search",
            params={"q": query, "hl": "ja", "gl": "jp"},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            timeout=10
        )

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        website = ""
        address = ""

        # 検索結果から情報を抽出（簡易版）
        # 実際のGoogle検索結果から施設情報を抽出するのは複雑なので、
        # 基本的にwebsiteは空、addressも限定的な情報のみとする
        # より正確な情報が必要な場合はSerpAPI版を推奨

        # 検索スニペットから住所を抽出
        snippets = soup.find_all('span', class_=re.compile(r'.*'))
        for snippet in snippets:
            text = snippet.get_text()
            # 都道府県を含む住所パターンを探す
            prefecture_match = re.search(r"([都道府県].*?[市区町村].*?[0-9])", text)
            if prefecture_match:
                address = prefecture_match.group(1)
                break

        # ウェブサイト情報は取得しにくいので空とする
        # （実際の運用では手動で確認する必要がある）

        return {"website": website, "address": address}

    except Exception as e:
        print(f"無料版検索エラー ({facility_name}): {e}")
        return None


def search_serpapi(facility_name: str, api_key: str) -> Optional[Dict]:
    """
    SerpAPIを使用して施設情報を取得

    Args:
        facility_name: 施設名
        api_key: SerpAPIキー

    Returns:
        施設情報の辞書（website, address）またはNone
    """
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="SerpAPIキーが設定されていません。"
        )
    
    # 施設名で直接検索（Googleマップ検索）
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
            # ローカル検索結果がある場合
            local_results = results["local_results"]
            if local_results and len(local_results) > 0:
                local_result = local_results[0]
                
                # ウェブサイトURLを取得
                if "website" in local_result:
                    website = local_result["website"]
                
                # 住所を取得
                if "address" in local_result:
                    address = local_result["address"]
                elif "gps_coordinates" in local_result:
                    # GPS座標がある場合、住所を取得できない可能性がある
                    pass
        
        # ローカル結果がない場合、通常の検索結果から探す
        if not website and "organic_results" in results:
            organic_results = results["organic_results"]
            for result in organic_results:
                link = result.get("link", "")
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                
                # Googleマップのリンクを探す
                if "maps.google.com" in link or "google.com/maps" in link:
                    # Googleマップのリンクが見つかった場合
                    # スニペットから住所を抽出
                    if snippet:
                        # 住所パターンを探す
                        prefecture_match = re.search(r"([都道府県].*?[市区町村].*?[0-9])", snippet)
                        if prefecture_match:
                            address = prefecture_match.group(1)
                    break
        
        return {"website": website, "address": address}
    
    except Exception as e:
        print(f"SerpAPI検索エラー ({facility_name}): {e}")
        return None


    """
    施設が営業対象かどうかを判定（無料版）

    Args:
        facility_name: 施設名
        website: ウェブサイトURL
        address: 住所

    Returns:
        判定結果の辞書
    """
    # 都道府県を抽出
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


def judge_target_serpapi(facility_name: str, website: str, address: str) -> Dict:
    """
    施設が営業対象かどうかを判定

    Args:
        facility_name: 施設名
        website: ウェブサイトURL
        address: 住所

    Returns:
        判定結果の辞書
    """
    # 都道府県を抽出
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


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """メインページ"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/process")
async def process_csv(
    file: UploadFile = File(...),
    serpapi_key: str = Form(""),
):
    """
    CSVファイルを処理して結果を返す

    Args:
        file: アップロードされたCSVファイル
        serpapi_key: SerpAPIキー
    """
    # APIキーのチェック（SerpAPIのみ）
    api_key = serpapi_key or SERPAPI_KEY
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="SerpAPIキーが設定されていません。画面上でSerpAPIキーを入力するか、環境変数SERPAPI_KEYを設定してください。"
        )
    
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSVファイルをアップロードしてください")
    
    # CSVファイルを読み込み
    contents = await file.read()
    try:
        csv_content = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        csv_content = contents.decode("shift_jis")
    
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    
    if len(rows) < 1:
        raise HTTPException(status_code=400, detail="CSVファイルが空です")
    
    # ヘッダー行をスキップ（最初の行がヘッダーの場合）
    header = rows[0]
    data_rows = rows[1:] if len(rows) > 1 else []
    
    # A列（施設名）を抽出
    facilities = []
    for row in data_rows:
        if len(row) > 0 and row[0].strip():
            facilities.append(row[0].strip())
    
    if not facilities:
        raise HTTPException(status_code=400, detail="施設名が見つかりません")
    
    # 各施設について処理
    results = []
    total = len(facilities)
    
    for idx, facility_name in enumerate(facilities):
        print(f"処理中: {idx + 1}/{total} - {facility_name}")
        
        # SerpAPIで検索実行
        place_info = search_serpapi(facility_name, api_key)
        website = place_info.get("website", "") if place_info else ""
        address = place_info.get("address", "") if place_info else ""
        
        # SerpAPI判定実行
        result = judge_target_serpapi(facility_name, website, address)
        results.append(result)
        
        # API制限対策（最後の1件は待機不要）
        if idx < total - 1:
            time.sleep(1.0)  # 1秒待機（SerpAPIのレート制限対策）
    
    # 結果を集計
    total_count = len(results)
    target_count = sum(1 for result in results if result.get("is_target") == "はい")
    non_target_count = total_count - target_count

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

    output.seek(0)
    csv_content = output.getvalue()

    # JSONレスポンスを返す
    return {
        "csv": csv_content,
        "total_count": total_count,
        "target_count": target_count,
        "non_target_count": non_target_count,
        "summary": {
            "total_count": total_count,
            "target_count": target_count,
            "non_target_count": non_target_count
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

