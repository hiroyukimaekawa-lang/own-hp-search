"""
テレアポ営業用施設判定アプリケーション（無料版）
Google検索 + HTMLスクレイピングを使用して施設情報を判定
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
import requests
from urllib.parse import urlparse, quote
import time
from bs4 import BeautifulSoup

app = FastAPI(title="テレアポ営業用施設判定アプリ（無料版）")

# 静的ファイルとテンプレートの設定
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 簡易HPサービスのドメインリスト（無料版用）
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


def is_simple_hp_free(url: str) -> bool:
    """
    URLが簡易HPサービスかどうかを判定（無料版用）
    
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
    URLのHTMLを取得して、簡易HPサービスかどうかを判定（無料版用）
    
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


def search_google_maps(facility_name: str) -> Optional[str]:
    """
    Google検索で「施設名 Google マップ」を検索し、GoogleビジネスプロフィールのURLを取得
    
    Args:
        facility_name: 施設名
        
    Returns:
        GoogleビジネスプロフィールのURLまたはNone
    """
    query = f"{facility_name} Google マップ"
    search_url = f"https://www.google.com/search?q={quote(query)}&hl=ja"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Googleマップのリンクを探す
        # 検索結果からmaps.google.comまたはビジネスプロフィールのURLを探す
        links = soup.find_all("a", href=True)
        
        for link in links:
            href = link.get("href", "")
            if "maps.google.com" in href or "google.com/maps" in href:
                # URLを正規化
                if href.startswith("/url?q="):
                    href = href.split("/url?q=")[1].split("&")[0]
                elif href.startswith("/search?q="):
                    continue
                
                # ビジネスプロフィールのURLかチェック
                if "/maps/place/" in href or "/maps/search/" in href:
                    return href
        
        return None
    
    except Exception as e:
        print(f"Google検索エラー ({facility_name}): {e}")
        return None


def extract_info_from_google_business(url: str) -> Dict:
    """
    Googleビジネスプロフィールのページからウェブサイトリンクと住所を抽出
    
    Args:
        url: GoogleビジネスプロフィールのURL
        
    Returns:
        施設情報の辞書（website, address）
    """
    website = ""
    address = ""
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {"website": website, "address": address}
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # ウェブサイトリンクを探す
        # 「ウェブサイト」というテキストを含むリンクを探す
        links = soup.find_all("a", href=True)
        for link in links:
            link_text = link.get_text(strip=True)
            href = link.get("href", "")
            
            if "ウェブサイト" in link_text or "website" in link_text.lower():
                if href.startswith("http"):
                    website = href
                    break
                elif href.startswith("/url?q="):
                    website = href.split("/url?q=")[1].split("&")[0]
                    break
        
        # 住所を探す
        # 「住所」というテキストの後に続くテキストを探す
        address_elements = soup.find_all(text=re.compile(r"住所|Address"))
        for elem in address_elements:
            parent = elem.parent
            if parent:
                # 次の要素を探す
                next_sibling = parent.find_next_sibling()
                if next_sibling:
                    address_text = next_sibling.get_text(strip=True)
                    if address_text:
                        address = address_text
                        break
        
        # 住所が見つからない場合、data属性から探す
        if not address:
            address_divs = soup.find_all(attrs={"data-value": re.compile(r"^[^0-9]*[都道府県]")})
            for div in address_divs:
                address_text = div.get_text(strip=True)
                if address_text:
                    address = address_text
                    break
        
        # 住所が見つからない場合、class名から探す
        if not address:
            address_elements = soup.find_all(class_=re.compile(r"address|住所|location"))
            for elem in address_elements:
                address_text = elem.get_text(strip=True)
                if address_text and ("都" in address_text or "府" in address_text or "県" in address_text or "道" in address_text):
                    address = address_text
                    break
    
    except Exception as e:
        print(f"Googleビジネスプロフィール抽出エラー: {e}")
    
    return {"website": website, "address": address}


def judge_target_free(facility_name: str, website: str, address: str) -> Dict:
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


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """メインページ"""
    return templates.TemplateResponse("index_free.html", {"request": request})


@app.post("/api/process")
async def process_csv(
    file: UploadFile = File(...),
):
    """
    CSVファイルを処理して結果を返す（無料版）
    
    Args:
        file: アップロードされたCSVファイル
    """
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
        
        # Google検索でGoogleマップのURLを取得
        maps_url = search_google_maps(facility_name)
        
        if maps_url:
            # Googleビジネスプロフィールから情報を抽出
            place_info = extract_info_from_google_business(maps_url)
            website = place_info.get("website", "")
            address = place_info.get("address", "")
        else:
            website = ""
            address = ""
        
        # 判定実行
        result = judge_target_free(facility_name, website, address)
        results.append(result)
        
        # レート制限対策（最後の1件は待機不要）
        if idx < total - 1:
            time.sleep(1.0)  # 1秒待機
    
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
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=result.csv"},
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8001)

