import os
import re
import html
import json
import sqlite3
import logging
import asyncio
import requests
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple, Set
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# תמיכה בטעינת קובץ .env אם מותקנת ספריית python-dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ======================= הגדרות חיבור ובוט =======================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
YAD2_COOKIE = os.getenv("YAD2_COOKIE", "")
YAD2_USER_AGENT = os.getenv("YAD2_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

DB_FILE = os.getenv("DB_FILE", "bot_database.db")
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "1800"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# שלבי השיחה
(
    STATE_CATEGORY,
    STATE_CHANNEL,
    STATE_MAKES_MULTI,
    STATE_AREAS_MULTI,
    STATE_MAX_PRICE,
    STATE_YEAR_OR_ROOMS,
    STATE_GEARBOX,
    STATE_FUEL_TYPE,
    STATE_MAX_HAND,
    STATE_MAX_KM,
) = range(10)

ALL_MANUFACTURERS_MAP = {
    "אאודי": "1", "audi": "1",
    "אבארט": "53", "abarth": "53",
    "אווטאר": "338", "avatr": "338",
    "אוטוביאנקי": "96",
    "אומודה": "369", "omoda": "369",
    "אופל": "2", "opel": "2",
    "אורה": "224", "ora": "224",
    "אי.וי איזי": "323",
    "איוויס": "288", "aiways": "288",
    "איווקו": "85", "iveco": "85",
    "איון": "379", "aion": "379",
    "איי אם": "374",
    "אינאוס": "310", "ineos": "310",
    "אינפיניטי": "3", "infiniti": "3",
    "איסוזו": "4", "isuzu": "4",
    "אלפא רומיאו": "5", "alfa": "5",
    "אלפין": "115", "alpine": "115",
    "אם ג'י": "6", "mg": "6",
    "אסטון מרטין": "54", "aston martin": "54",
    "אקורה": "111", "acura": "111",
    "אקסיד": "349", "exeed": "349",
    "אקספנג": "290", "xpeng": "290",
    "ב מ וו": "7", "bmw": "7",
    "בי.ווי.די": "141", "byd": "141",
    "ביואיק": "8", "buick": "8",
    "בנטלי": "55", "bentley": "55",
    "ג'אקו": "355", "jaecoo": "355",
    "ג'י.אם.סי": "9", "gmc": "9",
    "ג'יפ": "10", "jeep": "10",
    "ג'נסיס": "93", "genesis": "93",
    "ג׳ילי": "177", "geely": "177",
    "דאצ'יה": "12", "dacia": "12",
    "דודג'": "13", "dodge": "13",
    "די.אס": "14", "ds": "14",
    "דייהטסו": "15", "daihatsu": "15",
    "דיפאל": "362", "deepal": "362",
    "הונדה": "17", "honda": "17",
    "וולוו": "18", "volvo": "18",
    "ויי": "284", "wey": "284",
    "זיקר": "333", "zeekr": "333",
    "טויוטה": "19", "toyota": "19",
    "טסלה": "62", "tesla": "62",
    "יגואר": "20", "jaguar": "20",
    "יונדאי": "21", "hyundai": "21",
    "לינק אנד קו": "321", "lynk": "321",
    "לינקולן": "23", "lincoln": "23",
    "ליפמוטור": "320", "leapmotor": "320",
    "למבורגיני": "63", "lamborghini": "63",
    "לנד רובר": "24", "land rover": "24",
    "לקסוס": "26", "lexus": "26",
    "מאזדה": "27", "mazda": "27",
    "מזראטי": "28", "maserati": "28",
    "מיני": "29", "mini": "29",
    "מיצובישי": "30", "mitsubishi": "30",
    "מקלארן": "73", "mclaren": "73",
    "מקסוס": "89", "maxus": "89",
    "מרצדס-בנץ": "31", "מרצדס": "31", "mercedes": "31",
    "נטע": "348", "neta": "348",
    "ניאו": "289", "nio": "289",
    "ניסאן": "32", "nissan": "32",
    "סובארו": "35", "subaru": "35",
    "סוזוקי": "36", "suzuki": "36",
    "סיאט": "37", "seat": "37",
    "סיטרואן": "38", "citroen": "38",
    "סמארט": "39", "smart": "39",
    "סקודה": "40", "skoda": "40",
    "סרס": "287", "seres": "287",
    "פולסטאר": "231", "polestar": "231",
    "פולקסווגן": "41", "volkswagen": "41",
    "פורד": "43", "ford": "43",
    "פורשה": "44", "porsche": "44",
    "פיאט": "45", "fiat": "45",
    "פיג'ו": "46", "peugeot": "46",
    "פרארי": "57", "ferrari": "57",
    "צ׳רי": "147", "chery": "147",
    "קאדילק": "47", "cadillac": "47",
    "קופרה": "92", "cupra": "92",
    "קיה": "48", "kia": "48",
    "קיי גי אם": "344", "kgm": "344",
    "קרייזלר": "49", "chrysler": "49",
    "ראם": "91", "ram": "91",
    "רובר": "50", "rover": "50",
    "רולס רויס": "58", "rolls royce": "58",
    "רנו": "51", "renault": "51",
    "שברולט": "52", "chevrolet": "52",
}

TOP_AREA_MAP = {
    "ירושלים": "1",
    "מרכז": "2",
    "צפון": "3",
    "שרון": "4",
    "שפלה": "5",
    "דרום": "6",
}

POPULAR_MAKES_BUTTONS = [
    "טויוטה", "הונדה", "יונדאי", "מאזדה",
    "קיה", "סקודה", "סיאט", "פולקסווגן",
    "סוזוקי", "רנו", "פיג'ו", "שברולט",
    "ניסאן", "מרצדס", "ב מ וו", "בי.ווי.די",
    "ג׳ילי", "צ׳רי", "טסלה", "קופרה"
]

POPULAR_AREAS = ["מרכז", "שרון", "שפלה", "ירושלים", "צפון", "דרום"]

DEALER_PATTERNS = [
    r'אפשרות\s+(?:ל)?מימון',
    r'100%\s*מימון',
    r'מימון\s+(?:מלא|בנקאי|חוץ\s+בנקאי)',
    r'הוראת\s+קבע\s+ללא\s+תפיסת',
    r'פריסת\s+תשלומים\s+בצ\'קים',
    r'אפשרות\s+(?:ל)?טרייד\s*אין',
    r'מקבלים\s+טרייד\s*אין',
    r'טרייד\s*אין\s+במקום',
    r'סוכנות\s+רכב',
    r'מגרש\s+רכב',
    r'אולם\s+תצוגה',
    r'אוטו\s+דיל',
    r'אלבר',
    r'שלמה\s+סיקסט',
    r'כלמוביל',
    r'אוטו\s+סנטר'
]


# ======================= מסד נתונים =======================
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_id TEXT,
                category TEXT,
                filters_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seen_ads (
                search_id INTEGER,
                ad_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (search_id, ad_id)
            )
        """)
        conn.commit()


def add_search_to_db(user_id: int, channel_id: str, category: str, filters_dict: dict) -> int:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO searches (user_id, channel_id, category, filters_json) VALUES (?, ?, ?, ?)",
            (user_id, str(channel_id), category, json.dumps(filters_dict, ensure_ascii=False))
        )
        conn.commit()
        return cursor.lastrowid


def get_user_searches(user_id: int) -> List[tuple]:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, channel_id, category, filters_json FROM searches WHERE user_id = ?", (user_id,))
        return cursor.fetchall()


def delete_search_from_db(search_id: int, user_id: int) -> bool:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM searches WHERE id = ? AND user_id = ?", (search_id, user_id))
        cursor.execute("DELETE FROM seen_ads WHERE search_id = ?", (search_id,))
        conn.commit()
        return cursor.rowcount > 0


def clear_seen_history(user_id: Optional[int] = None):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("DELETE FROM seen_ads WHERE search_id IN (SELECT id FROM searches WHERE user_id = ?)", (user_id,))
        else:
            cursor.execute("DELETE FROM seen_ads")
        conn.commit()


def get_all_active_searches() -> List[tuple]:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, channel_id, category, filters_json FROM searches")
        return cursor.fetchall()


def is_ad_seen(search_id: int, ad_id: str) -> bool:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM seen_ads WHERE search_id = ? AND ad_id = ?", (search_id, str(ad_id)))
        return cursor.fetchone() is not None


def mark_ad_seen(search_id: int, ad_id: str):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO seen_ads (search_id, ad_id) VALUES (?, ?)", (search_id, str(ad_id)))
        conn.commit()


# ======================= בניית כתובת חיפוש וחילוץ =======================
def clean_numeric(val: Any) -> Optional[int]:
    if val is None:
        return None
    digits = re.sub(r"[^\d]", "", str(val))
    return int(digits) if digits else None


def clean_image_url(url_str: Any) -> Optional[str]:
    if not url_str or not isinstance(url_str, str):
        return None
    url_str = url_str.strip()

    if "url=" in url_str:
        try:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(url_str).query)
            if "url" in qs and qs["url"]:
                url_str = qs["url"][0]
        except Exception:
            pass

    if url_str.startswith("//"):
        return "https:" + url_str
    elif url_str.startswith("http://") or url_str.startswith("https://"):
        return url_str
    elif url_str.startswith("/"):
        return "https://www.yad2.co.il" + url_str
    else:
        return "https://img.yad2.co.il/" + url_str


def find_image_recursively(obj: Any, depth: int = 0) -> Optional[str]:
    if depth > 7 or obj is None:
        return None
    if isinstance(obj, str):
        s = obj.strip()
        if any(ext in s.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", "img.yad2.co.il", "/pic/", "pictures/"]):
            return clean_image_url(s)
    elif isinstance(obj, dict):
        for k in ["large", "detail", "src", "main", "primary", "original", "url", "image", "photo", "img"]:
            if k in obj:
                res = find_image_recursively(obj[k], depth + 1)
                if res:
                    return res
        for v in obj.values():
            res = find_image_recursively(v, depth + 1)
            if res:
                return res
    elif isinstance(obj, list):
        for elem in obj:
            res = find_image_recursively(elem, depth + 1)
            if res:
                return res
    return None


def get_item_price(item: dict) -> Optional[int]:
    for k in ["price", "Price", "price_raw", "price_text", "cost", "amount"]:
        if k in item:
            val = clean_numeric(item[k])
            if val and val > 0:
                return val
    return None


def build_filtered_search_url(category: str, filters_dict: dict) -> str:
    if category == "cars":
        base = "https://www.yad2.co.il/vehicles/cars?feed_source=private&ownership=1&priceOnly=1&imgOnly=1"
        params = []

        makes = filters_dict.get("makes", [])
        if makes and "כל היצרנים" not in makes:
            make_codes = [ALL_MANUFACTURERS_MAP[m.strip().lower()] for m in makes if m.strip().lower() in ALL_MANUFACTURERS_MAP]
            if make_codes:
                params.append("manufacturer=" + ",".join(make_codes))

        areas = filters_dict.get("areas", [])
        if areas and "כל הארץ" not in areas:
            area_codes = [TOP_AREA_MAP[a.strip()] for a in areas if a.strip() in TOP_AREA_MAP]
            if area_codes:
                params.append("topArea=" + ",".join(area_codes))

        max_p = filters_dict.get("max_price")
        if max_p:
            params.append(f"price=-1-{max_p}")

        min_y = filters_dict.get("min_year")
        if min_y:
            params.append(f"year={min_y}--1")

        gear = filters_dict.get("gearbox")
        if gear == "manual":
            params.append("gearBox=101")
        elif gear == "auto":
            params.append("gearBox=102")

        max_h = filters_dict.get("max_hand")
        if max_h:
            params.append(f"hand=0-{max_h}")

        max_k = filters_dict.get("max_km")
        if max_k:
            params.append(f"km=-1-{max_k}")

        if params:
            return base + "&" + "&".join(params)
        return base
    else:
        base = f"https://www.yad2.co.il/realestate/{category}?feed_source=private"
        params = []
        max_p = filters_dict.get("max_price")
        if max_p:
            params.append(f"price=-1-{max_p}")
        min_r = filters_dict.get("min_rooms")
        if min_r:
            params.append(f"rooms={min_r}--1")
        if params:
            return base + "&" + "&".join(params)
        return base


def find_feed_items_recursively(obj: Any, depth: int = 0) -> List[dict]:
    if depth > 10:
        return []
    if isinstance(obj, list):
        if len(obj) > 0 and isinstance(obj[0], dict):
            sample = obj[0]
            if any(k in sample for k in ["id", "token", "link_token", "price", "title", "heading", "feed_source", "year", "line_1"]):
                return [x for x in obj if isinstance(x, dict)]
        for item in obj:
            res = find_feed_items_recursively(item, depth + 1)
            if res:
                return res
    elif isinstance(obj, dict):
        for k in ["feed_items", "feedItems", "items", "results", "feed", "data"]:
            if k in obj:
                res = find_feed_items_recursively(obj[k], depth + 1)
                if res:
                    return res
        for v in obj.values():
            if isinstance(v, (dict, list)):
                res = find_feed_items_recursively(v, depth + 1)
                if res:
                    return res
    return []


def parse_ads_from_html(html_text: str) -> List[dict]:
    items = []
    seen_ids = set()

    item_blocks = re.findall(r'<a[^>]*href=["\'](?:/vehicles)?/item/([a-zA-Z0-9_-]+)["\'][^>]*>(.*?)</a>', html_text, re.DOTALL)
    for ad_id, block in item_blocks:
        if ad_id in seen_ids:
            continue
        seen_ids.add(ad_id)

        title_m = re.search(r'<[^>]*class=["\'][^"\']*title[^"\']*["\'][^>]*>([^<]+)<', block)
        title = title_m.group(1).strip() if title_m else "רכב ביד 2"

        price_m = re.search(r'([\d,]+)\s*₪', block)
        price = price_m.group(1).replace(",", "") if price_m else None

        img_m = re.search(r'<img[^>]+(?:src|data-src|srcset)=["\']([^"\']+)["\']', block)
        raw_img = img_m.group(1) if img_m else None
        img_url = clean_image_url(raw_img)

        year_m = re.search(r'\b(20\d\d|19\d\d)\b', block)
        year = year_m.group(1) if year_m else None

        hand_m = re.search(r'יד\s*(\d+)', block)
        hand = hand_m.group(1) if hand_m else None

        km_m = re.search(r'([\d,]+)\s*ק"מ', block)
        km = km_m.group(1).replace(",", "") if km_m else None

        items.append({
            "id": ad_id,
            "title": title,
            "price": price,
            "images": [img_url] if img_url else [],
            "year": year,
            "hand": hand,
            "km": km,
            "info_text": re.sub(r'<[^>]+>', ' ', block),
        })

    return items


def fetch_yad2_feed(category: str, filters_dict: dict) -> Tuple[int, List[dict]]:
    headers = {
        "User-Agent": YAD2_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/json",
        "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.yad2.co.il/",
        "Cookie": YAD2_COOKIE
    }

    target_url = build_filtered_search_url(category, filters_dict)
    logging.info(f"פונה ל-Yad2 עם כתובת מסוננת: {target_url}")

    try:
        res = requests.get(target_url, headers=headers, timeout=12)
        if res.status_code == 200 and res.text:
            if "__NEXT_DATA__" in res.text:
                match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', res.text, re.DOTALL)
                if match:
                    try:
                        items = find_feed_items_recursively(json.loads(match.group(1)))
                        if items:
                            logging.info(f"חולצו {len(items)} מודעות מסוננות מ-Yad2")
                            return 200, items
                    except Exception:
                        pass

            html_items = parse_ads_from_html(res.text)
            if html_items:
                logging.info(f"חולצו {len(html_items)} מודעות מסוננות מ-HTML")
                return 200, html_items
        return res.status_code, []
    except Exception as e:
        logging.error(f"שגיאה בשליפת יד 2: {e}")
        return 0, []


def fetch_item_details(item_id: str, category: str = "cars") -> dict:
    """שליפה עמוקה ומלאה של כל פרטי הרכב מדף המודעה הישיר"""
    url = f"https://www.yad2.co.il/vehicles/item/{item_id}" if category == "cars" else f"https://www.yad2.co.il/realestate/item/{item_id}"
    headers = {
        "User-Agent": YAD2_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.yad2.co.il/",
        "Cookie": YAD2_COOKIE
    }
    extracted_data = {}
    try:
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200 and res.text:
            # 1. סריקה רקורסיבית של עץ ה-JSON ב-Next.js
            if "__NEXT_DATA__" in res.text:
                match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', res.text, re.DOTALL)
                if match:
                    try:
                        json_tree = json.loads(match.group(1))
                        def extract_all(obj, depth=0):
                            if depth > 10 or obj is None:
                                return
                            if isinstance(obj, dict):
                                for k, v in obj.items():
                                    if isinstance(v, (str, int, float)):
                                        extracted_data[str(k)] = str(v)
                                    elif isinstance(v, dict):
                                        extract_all(v, depth + 1)
                                    elif isinstance(v, list):
                                        for elem in v:
                                            if isinstance(elem, dict):
                                                k_name = elem.get("key") or elem.get("title") or elem.get("name")
                                                v_val = elem.get("value") or elem.get("text") or elem.get("val")
                                                if k_name and v_val is not None:
                                                    extracted_data[str(k_name)] = str(v_val)
                                                extract_all(elem, depth + 1)
                        extract_all(json_tree)
                    except Exception:
                        pass

            # 2. חילוץ שדות ותוויות מתוך ה-HTML
            patterns = [
                r"<(?:span|div|p|dt|b|strong)[^>]*>([^<:]+)[:]?\s*</(?:span|div|p|dt|b|strong)>\s*<(?:span|div|p|dd|b|strong)[^>]*>([^<]+)</(?:span|div|p|dd|b|strong)>",
                r"<dt[^>]*>([^<:]+)[:]?\s*</dt>\s*<dd[^>]*>([^<]+)</dd>"
            ]
            for p in patterns:
                for k_html, v_html in re.findall(p, res.text):
                    k_c = k_html.strip().replace(":", "")
                    v_c = v_html.strip()
                    if len(k_c) < 30 and len(v_c) < 100:
                        if k_c not in extracted_data:
                            extracted_data[k_c] = v_c

            # 3. חילוץ ישיר של ביטויים מרכזיים
            if "טסט עד" not in extracted_data:
                test_m = re.search(r"טסט(?:\s*עד|\s*בתוקף)?\s*[:\-]?\s*([0-9/.]+)", res.text)
                if test_m:
                    extracted_data["טסט עד"] = test_m.group(1)

            if "חודש עלייה לכביש" not in extracted_data:
                road_m = re.search(r"עלייה לכביש\s*[:\-]?\s*([0-9/.]+)", res.text)
                if road_m:
                    extracted_data["חודש עלייה לכביש"] = road_m.group(1)

            if "טלפון" not in extracted_data:
                phone_m = re.search(r"\b(05\d[\-]?\d{7})\b", res.text)
                if phone_m:
                    extracted_data["טלפון"] = phone_m.group(1)

            if "איש קשר" not in extracted_data:
                contact_m = re.search(r"איש קשר\s*[:\-]?\s*([^\n<]+)", res.text)
                if contact_m:
                    extracted_data["איש קשר"] = contact_m.group(1).strip()

            if "ציון בטיחות" not in extracted_data:
                rating_m = re.search(r"(?:ציון בטיחות|דירוג בטיחות|ציון רכב)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)", res.text)
                if rating_m:
                    extracted_data["ציון בטיחות"] = rating_m.group(1)

    except Exception as e:
        logging.warning(f"שגיאה בשליפת פירוט מודעה {item_id}: {e}")
    return extracted_data


def is_dealer_ad(text: str) -> bool:
    text_clean = text.lower()
    for pattern in DEALER_PATTERNS:
        match = re.search(pattern, text_clean)
        if match:
            start_pos = max(0, match.start() - 20)
            prefix = text_clean[start_pos:match.start()]
            if any(neg in prefix for neg in ["לא ", "בלי ", "ללא ", "אין "]):
                continue
            return True
    return False


def is_valid_private_ad(item: dict, category: str, filters_dict: dict) -> Tuple[bool, str]:
    if not isinstance(item, dict):
        return False, "לא מילון"

    ad_id = str(item.get("id") or item.get("token") or item.get("link_token") or "")
    if not ad_id or len(ad_id) < 3:
        return False, "אין מזהה מודעה"

    if item.get("merchant") == 1 or item.get("is_merchant") is True:
        return False, "סוחר במטא-דאטה"
    if item.get("order_type") in ["agency", "commercial", "trade_in"]:
        return False, "סוג הזמנה מסחרי"
    if item.get("feed_source") == "commercial":
        return False, "מקור מודעה מסחרי"

    img_url = find_image_recursively(item)
    if not img_url:
        return False, "אין תמונה במודעה"

    price_val = get_item_price(item)
    if not price_val or price_val <= 0:
        return False, "אין מחיר נקוב"

    max_price = filters_dict.get("max_price")
    if max_price and price_val > max_price:
        return False, f"מחיר {price_val} מעל התקציב"

    title = str(item.get("title") or item.get("heading") or item.get("line_1") or "")
    sub_title = str(item.get("sub_title") or item.get("sub_heading") or item.get("line_2") or "")
    description = str(item.get("info_text") or item.get("description") or "")
    full_text = f"{title} {sub_title} {description}".lower()

    if is_dealer_ad(full_text):
        return False, "זוהה טקסט סוכנות/מימון"

    return True, "תקין"


def clean_field(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ["none", "null", "לא צוין", "undefined", "0", "false"]:
        return ""
    return s


def format_ad_message(item: dict, category: str) -> str:
    """עיצוב מדויק, עשיר ויפה בטלגרם עם כל השדות שהוגדרו"""
    item_id = str(item.get("id") or item.get("token") or item.get("link_token") or "")
    ad_url = f"https://www.yad2.co.il/item/{item_id}"

    title = clean_field(item.get("title") or item.get("heading") or item.get("line_1") or "רכב למכירה")
    sub_title = clean_field(item.get("sub_title") or item.get("sub_heading") or item.get("line_2") or item.get("version") or item.get("sub_model"))

    # מחיר
    raw_price = item.get("price") or item.get("Price") or item.get("price_text")
    digits = "".join(c for c in str(raw_price) if c.isdigit()) if raw_price else ""
    price_str = f"{int(digits):,} ₪" if digits else "לא צוין"

    # שנתון ותאריך עלייה לכביש
    year = clean_field(item.get("year") or item.get("Year") or item.get("model_year") or item.get("שנה"))
    month = clean_field(item.get("month") or item.get("registration_date") or item.get("car_month") or item.get("date_of_rise_to_road") or item.get("חודש עלייה לכביש") or item.get("עלייה לכביש"))
    if not month and item.get("road_date"):
        month = clean_field(item.get("road_date"))
    if month and len(month) == 1:
        month = f"0{month}"

    if year and month and ("/" in month or len(month) <= 2):
        month_clean = month if "/" in month else f"{month}/{year}"
        year_line = f"{year} (עלייה לכביש: {month_clean})"
    elif year:
        year_line = f"{year}"
    else:
        year_line = "לא צוין"

    # תאריך טסט
    test_date = clean_field(item.get("test_date") or item.get("testMonth") or item.get("test_until") or item.get("test") or item.get("טסט עד") or item.get("תוקף טסט") or item.get("טסט"))

    # יד ובעלות - נקי ללא כפילויות וללא שבירות
    raw_hand = item.get("hand") or item.get("Hand") or item.get("יד") or item.get("Hand_text")
    raw_ownership = item.get("previous_ownership") or item.get("ownership") or item.get("owner_type") or item.get("בעלות") or item.get("בעלות קודמת") or item.get("בעלות נוכחית")

    full_text_search = f"{title} {sub_title} {item.get('info_text', '')}".lower()

    hand_num = None
    if raw_hand:
        m = re.search(r"\b([0-9]+)\b", str(raw_hand))
        if m:
            hand_num = m.group(1)
    if not hand_num:
        m = re.search(r"יד\s*([0-9]+)", full_text_search)
        if m:
            hand_num = m.group(1)

    ownership = None
    own_str = str(raw_ownership or "").strip()
    for o in ["פרטית", "חברה", "ליסינג", "השכרה", "מונית", "ייבוא אישי", "ייבוא מקביל", "ממשלתי"]:
        if o in own_str or o in str(raw_hand or ""):
            ownership = o
            break
    if not ownership:
        for o in ["פרטית", "חברה", "ליסינג", "השכרה", "מונית", "ייבוא אישי"]:
            if o in full_text_search:
                ownership = o
                break
    if not ownership:
        ownership = "פרטית"

    if hand_num:
        hand_display = f"יד {hand_num} ({ownership})"
    else:
        hand_display = f"בעלות: {ownership}"

    # קילומטראז'
    raw_km = item.get("km") or item.get("Kilometer") or item.get("mileage") or item.get("קילומטראז'") or item.get("ק\"מ")
    km_digits = "".join(c for c in str(raw_km) if c.isdigit()) if raw_km else ""
    km_str = f"{int(km_digits):,} ק\"מ" if km_digits else "לא צוין"

    # גיר
    gear = clean_field(item.get("gearBox") or item.get("gear_box") or item.get("gearbox") or item.get("תיבת הילוכים") or item.get("גיר"))
    if gear == "101" or "ידנ" in gear:
        gear = "ידני"
    elif gear == "102" or "אוטומט" in gear:
        gear = "אוטומט"
    else:
        gear = gear or "אוטומט"

    # מנוע, כוחות סוס ודלק
    engine_size = clean_field(item.get("engine_size") or item.get("engineSize") or item.get("engine_volume") or item.get("נפח מנוע") or item.get("נפח"))
    fuel = clean_field(item.get("engine_type") or item.get("fuel_type") or item.get("fuelType") or item.get("סוג דלק") or item.get("דלק") or "בנזין")
    hp = clean_field(item.get("horse_power") or item.get("hp") or item.get("כ\"ס") or item.get("כוחות סוס"))

    engine_parts = []
    if engine_size:
        engine_parts.append(f"{engine_size} סמ\"ק")
    if hp:
        engine_parts.append(f"{hp} כ\"ס")
    if fuel:
        engine_parts.append(fuel)
    engine_line = f"{gear} | " + " | ".join(engine_parts)

    # מיקום
    city = clean_field(item.get("city") or item.get("City") or item.get("settlement") or item.get("יישוב") or item.get("עיר"))
    neighborhood = clean_field(item.get("neighborhood") or item.get("שכונה") or item.get("אזור"))
    loc_line = f"{city}" + (f" ({neighborhood})" if neighborhood else "") if city else "לא צוין"

    # יצירת קשר וטלפון
    contact_name = clean_field(item.get("contact_name") or item.get("seller_name") or item.get("user_name") or item.get("שם איש קשר") or item.get("שם המוכר"))
    phone = clean_field(item.get("phone") or item.get("contact_phone") or item.get("mobile") or item.get("טלפון") or item.get("מספר טלפון") or item.get("נייד"))

    # דירוג, תאריך פרסום ותיאור
    rating = clean_field(item.get("safety_rating") or item.get("rating") or item.get("car_rating") or item.get("score") or item.get("ציון בטיחות") or item.get("דירוג"))
    pub_date = clean_field(item.get("date") or item.get("date_added") or item.get("date_updated") or item.get("publish_date") or item.get("תאריך יצירה") or item.get("תאריך פרסום"))
    description = clean_field(item.get("info_text") or item.get("description") or item.get("body"))

    lines = [
        f"🚗 <b>{html.escape(title)}</b>"
    ]
    if sub_title:
        lines.append(f"🔹 <i>{html.escape(sub_title)}</i>")

    lines.extend([
        "",
        f"💰 <b>מחיר:</b> {html.escape(price_str)}",
        f"📅 <b>שנתון:</b> {html.escape(year_line)}",
        f"👤 <b>יד ובעלות:</b> {html.escape(hand_display)}",
        f"🛣️ <b>קילומטראז':</b> {html.escape(km_str)}",
        f"⚙️ <b>מפרט:</b> {html.escape(engine_line)}",
    ])

    if test_date:
        lines.append(f"🛡️ <b>טסט בתוקף עד:</b> {html.escape(test_date)}")
    if rating:
        lines.append(f"⭐ <b>ציון ודירוג הרכב:</b> {html.escape(rating)} / 10")
    lines.append(f"📍 <b>מיקום:</b> {html.escape(loc_line)}")

    if contact_name or phone:
        contact_parts = []
        if contact_name:
            contact_parts.append(f"<b>איש קשר:</b> {html.escape(contact_name)}")
        if phone:
            clean_p = "".join(c for c in phone if c.isdigit())
            contact_parts.append(f"<b>טלפון:</b> <a href='tel:{clean_p}'>{html.escape(phone)}</a>")
        lines.append("📞 " + " | ".join(contact_parts))

    if pub_date:
        lines.append(f"🕒 <b>פורסם בתאריך:</b> {html.escape(pub_date)}")

    if description:
        max_desc_len = 180
        desc_snippet = description[:max_desc_len] + ("..." if len(description) > max_desc_len else "")
        lines.append(f"\n📝 <b>תיאור המוכר:</b>\n{html.escape(desc_snippet)}")

    lines.append(f"\n🔗 <a href='{ad_url}'><b>לפתיחת המודעה המלאה ביד 2 ⬅️</b></a>")

    return "\n".join(lines)


# ======================= סריקה ושליחה =======================
async def scan_and_notify_searches(bot, specific_user_id: Optional[int] = None) -> Tuple[int, int, int, int]:
    searches = get_all_active_searches()
    if specific_user_id:
        searches = [s for s in searches if s[1] == specific_user_id]

    total_fetched = 0
    total_matched = 0
    total_seen = 0
    total_sent = 0

    for search_id, user_id, channel_id, category, filters_json in searches:
        try:
            filters_dict = json.loads(filters_json)
        except Exception:
            filters_dict = {}

        status_code, items = await asyncio.to_thread(fetch_yad2_feed, category, filters_dict)
        total_fetched += len(items)

        for item in items:
            ad_id = str(item.get("id") or item.get("token") or "")
            if not ad_id:
                continue

            is_valid, reason = is_valid_private_ad(item, category, filters_dict)
            if not is_valid:
                continue

            total_matched += 1
            if is_ad_seen(search_id, ad_id):
                total_seen += 1
                continue

            # שליפה עמוקה של דף הרכב
            detailed_data = await asyncio.to_thread(fetch_item_details, ad_id, category)
            full_item = {**item, **detailed_data} if detailed_data else item

            msg_text = format_ad_message(full_item, category)
            primary_image = find_image_recursively(full_item)

            try:
                target_chat = int(channel_id) if channel_id.lstrip("-").isdigit() else channel_id
                if primary_image:
                    try:
                        await bot.send_photo(chat_id=target_chat, photo=primary_image, caption=msg_text, parse_mode="HTML")
                    except Exception as photo_err:
                        logging.warning(f"send_photo נכשל ({photo_err}). שולח כתצוגה מקדימה...")
                        preview_html = f'<a href="{primary_image}">&#8205;</a>' + msg_text
                        await bot.send_message(chat_id=target_chat, text=preview_html, parse_mode="HTML")
                else:
                    await bot.send_message(chat_id=target_chat, text=msg_text, parse_mode="HTML")

                mark_ad_seen(search_id, ad_id)
                total_sent += 1
                title = full_item.get("title") or full_item.get("heading") or "מודעה"
                logging.info(f"✅ נשלחה מודעה: {title} לערוץ {channel_id}")
                await asyncio.sleep(1.5)
            except Exception as e:
                logging.error(f"שגיאה בשליחה ליעד {channel_id}: {e}")

    return total_fetched, total_matched, total_seen, total_sent


async def periodic_check_job(context: ContextTypes.DEFAULT_TYPE):
    fetched, matched, seen, sent = await scan_and_notify_searches(context.bot)
    logging.info(f"סריקה תקופתית: נקלטו {fetched}, תאמו {matched}, נשלחו {sent} (נצפו בעבר: {seen})")


# ======================= מקלדות צ'קבוקס (Multi-Select) =======================
def build_makes_keyboard(selected_makes: Set[str]) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for make in POPULAR_MAKES_BUTTONS:
        check = "✅" if make in selected_makes else "⬜"
        row.append(InlineKeyboardButton(f"{check} {make}", callback_data=f"toggle_make_{make}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🌟 כל היצרנים (ללא סינון)", callback_data="make_all")])
    count_text = f"➡️ המשך ({len(selected_makes)} נבחרו)" if selected_makes else "➡️ המשך ללא בחירה (הכל)"
    keyboard.append([InlineKeyboardButton(count_text, callback_data="make_done")])
    keyboard.append([InlineKeyboardButton("❌ ביטול", callback_data="cancel_wizard")])
    return InlineKeyboardMarkup(keyboard)


def build_areas_keyboard(selected_areas: Set[str]) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for area in POPULAR_AREAS:
        check = "✅" if area in selected_areas else "⬜"
        row.append(InlineKeyboardButton(f"{check} {area}", callback_data=f"toggle_area_{area}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🇮🇱 כל הארץ (ללא סינון)", callback_data="area_all")])
    count_text = f"➡️ המשך ({len(selected_areas)} נבחרו)" if selected_areas else "➡️ המשך ללא בחירה (כל הארץ)"
    keyboard.append([InlineKeyboardButton(count_text, callback_data="area_done")])
    keyboard.append([InlineKeyboardButton("❌ ביטול", callback_data="cancel_wizard")])
    return InlineKeyboardMarkup(keyboard)


# ======================= שיחת הגדרת חיפוש =======================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ יצירת חיפוש חדש", callback_data="btn_new_search")],
        [InlineKeyboardButton("📋 החיפושים הפעילים שלי", callback_data="btn_my_searches")],
        [InlineKeyboardButton("🔍 בצע בדיקה עכשיו", callback_data="btn_check_now")],
        [InlineKeyboardButton("🔄 אפס היסטוריית מודעות ושלח הכל מחדש", callback_data="btn_clear_history")],
    ]
    welcome_text = (
        "👋 <b>ברוך הבא לבוט החיפוש החכם של Yad2!</b>\n\n"
        "🛡️ <i>סוכנויות, מגרשים, מתווכים ומימון מסוננים אוטומטית.</i>\n\n"
        "בחר פעולה מהתפריט:"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(welcome_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(welcome_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def new_search_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["filters"] = {}
    context.user_data["selected_makes"] = set()
    context.user_data["selected_areas"] = set()

    keyboard = [
        [InlineKeyboardButton("🚗 רכבים", callback_data="setcat_cars")],
        [InlineKeyboardButton("🏠 דירות להשכרה", callback_data="setcat_rent")],
        [InlineKeyboardButton("🏢 דירות למכירה", callback_data="setcat_forsale")],
        [InlineKeyboardButton("❌ ביטול", callback_data="cancel_wizard")],
    ]
    text = "בחר קטגוריה לחיפוש:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return STATE_CATEGORY


async def category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["category"] = query.data.replace("setcat_", "")

    keyboard = [
        [InlineKeyboardButton("📩 שלח לכאן (לצ'אט הפרטי)", callback_data="dest_here")],
        [InlineKeyboardButton("❌ ביטול", callback_data="cancel_wizard")],
    ]
    msg = (
        "<b>לאן לשלוח את המודעות?</b>\n\n"
        "• לחץ על הכפתור למטה כדי לקבל ישירות לכאן.\n"
        "• <b>לערוץ פרטי:</b> הוסף את הבוט כמנהל בערוץ והעבר (Forward) לכאן הודעה ממנו.\n"
        "• <b>לערוץ ציבורי:</b> שלח את שם הערוץ (למשל: <code>@my_channel</code>)."
    )
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    return STATE_CHANNEL


async def channel_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["channel_id"] = str(update.effective_chat.id)
    return await prompt_makes_or_areas(query.message, context)


async def channel_entered_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = None
    msg = update.effective_message
    if hasattr(msg, "forward_origin") and msg.forward_origin and hasattr(msg.forward_origin, "chat") and msg.forward_origin.chat:
        chat_id = str(msg.forward_origin.chat.id)
    elif hasattr(msg, "forward_from_chat") and msg.forward_from_chat:
        chat_id = str(msg.forward_from_chat.id)
    else:
        txt = (msg.text or "").strip()
        chat_id = str(update.effective_chat.id) if txt == "כאן" else txt

    context.user_data["channel_id"] = chat_id

    try:
        target_chat = int(chat_id) if chat_id.lstrip("-").isdigit() else chat_id
        await context.bot.send_message(
            chat_id=target_chat,
            text="🔔 <b>הודעת בדיקה:</b> הבוט חובר בהצלחה לערוץ וישלח לכאן מודעות חדשות בזמן אמת!",
            parse_mode="HTML"
        )
        await msg.reply_text("✅ <b>הודעת בדיקה נשלחה בהצלחה לערוץ!</b>", parse_mode="HTML")
    except Exception as e:
        logging.error(f"שגיאה בשליחת הודעת בדיקה: {e}")
        await msg.reply_text(f"⚠️ <b>שים לב:</b> הבוט לא הצליח לפרסם הודעה בערוץ (ודא שהוא מנהל בערוץ עם הרשאת שליחה).", parse_mode="HTML")

    return await prompt_makes_or_areas(msg, context)


async def prompt_makes_or_areas(reply_target, context: ContextTypes.DEFAULT_TYPE):
    cat = context.user_data["category"]
    if cat == "cars":
        selected = context.user_data.get("selected_makes", set())
        txt = "בחר <b>יצרנים</b> (תוכל לסמן כמה שתרצה בלחיצה) או <b>הקלד שמות</b> מכל יצרן שתרצה:\nבסיום לחץ <b>➡️ המשך</b>:"
        await reply_target.reply_text(txt, parse_mode="HTML", reply_markup=build_makes_keyboard(selected))
        return STATE_MAKES_MULTI
    else:
        selected = context.user_data.get("selected_areas", set())
        txt = "בחר <b>אזורים</b> (תוכל לסמן כמה שתרצה) או <b>הקלד ערים</b> בהודעה:\nבסיום לחץ <b>➡️ המשך</b>:"
        await reply_target.reply_text(txt, parse_mode="HTML", reply_markup=build_areas_keyboard(selected))
        return STATE_AREAS_MULTI


async def makes_multi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    selected: Set[str] = context.user_data.get("selected_makes", set())

    if data.startswith("toggle_make_"):
        make = data.replace("toggle_make_", "")
        if make in selected:
            selected.remove(make)
        else:
            selected.add(make)
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=build_makes_keyboard(selected))
        return STATE_MAKES_MULTI

    elif data == "make_all":
        context.user_data["filters"]["makes"] = ["כל היצרנים"]
        await query.answer("נבחרו כל היצרנים")
        return await prompt_areas(query.message, context)

    elif data == "make_done":
        await query.answer()
        context.user_data["filters"]["makes"] = list(selected) if selected else ["כל היצרנים"]
        return await prompt_areas(query.message, context)


async def makes_multi_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt != "הכל":
        context.user_data["filters"]["makes"] = [x.strip() for x in txt.split(",") if x.strip()]
    else:
        context.user_data["filters"]["makes"] = ["כל היצרנים"]
    return await prompt_areas(update.message, context)


async def prompt_areas(reply_target, context: ContextTypes.DEFAULT_TYPE):
    selected = context.user_data.get("selected_areas", set())
    txt = "בחר <b>אזורים בארץ</b> (תוכל לסמן כמה שתרצה) או <b>הקלד ערים</b> מופרדות בפסיק:\nבסיום לחץ <b>➡️ המשך</b>:"
    await reply_target.reply_text(txt, parse_mode="HTML", reply_markup=build_areas_keyboard(selected))
    return STATE_AREAS_MULTI


async def areas_multi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    selected: Set[str] = context.user_data.get("selected_areas", set())

    if data.startswith("toggle_area_"):
        area = data.replace("toggle_area_", "")
        if area in selected:
            selected.remove(area)
        else:
            selected.add(area)
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=build_areas_keyboard(selected))
        return STATE_AREAS_MULTI

    elif data == "area_all":
        context.user_data["filters"]["areas"] = ["כל הארץ"]
        await query.answer("נבחרה כל הארץ")
        return await prompt_price(query.message, context)

    elif data == "area_done":
        await query.answer()
        context.user_data["filters"]["areas"] = list(selected) if selected else ["כל הארץ"]
        return await prompt_price(query.message, context)


async def areas_multi_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt != "הכל":
        context.user_data["filters"]["areas"] = [x.strip() for x in txt.split(",") if x.strip()]
    else:
        context.user_data["filters"]["areas"] = ["כל הארץ"]
    return await prompt_price(update.message, context)


async def prompt_price(reply_target, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("עד 30,000 ₪", callback_data="price_30000"), InlineKeyboardButton("עד 50,000 ₪", callback_data="price_50000")],
        [InlineKeyboardButton("עד 100,000 ₪", callback_data="price_100000"), InlineKeyboardButton("ללא הגבלה", callback_data="price_none")],
        [InlineKeyboardButton("❌ ביטול", callback_data="cancel_wizard")],
    ]
    await reply_target.reply_text("מהו <b>התקציב המקסימלי</b> בש\"ח?\nבחר מהכפתורים או <b>הקלד סכום ידנית</b> (למשל: <code>30000</code>):", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    return STATE_MAX_PRICE


async def max_price_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    p_data = query.data.replace("price_", "")
    if p_data != "none":
        context.user_data["filters"]["max_price"] = int(p_data)
    return await prompt_year_or_rooms(query.message, context)


async def max_price_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = clean_numeric(update.message.text)
    if p:
        context.user_data["filters"]["max_price"] = p
    return await prompt_year_or_rooms(update.message, context)


async def prompt_year_or_rooms(reply_target, context: ContextTypes.DEFAULT_TYPE):
    cat = context.user_data["category"]
    if cat == "cars":
        keyboard = [
            [InlineKeyboardButton("2010 ומעלה", callback_data="year_2010"), InlineKeyboardButton("2015 ומעלה", callback_data="year_2015")],
            [InlineKeyboardButton("2020 ומעלה", callback_data="year_2020"), InlineKeyboardButton("ללא הגבלה", callback_data="year_none")],
        ]
        await reply_target.reply_text("מהו <b>השנתון המינימלי</b> לרכב?\nבחר מהכפתורים או <b>הקלד שנתון ידנית</b> (למשל: <code>2010</code>):", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return STATE_YEAR_OR_ROOMS
    else:
        keyboard = [
            [InlineKeyboardButton("2 חדרים+", callback_data="rooms_2"), InlineKeyboardButton("3 חדרים+", callback_data="rooms_3")],
            [InlineKeyboardButton("4 חדרים+", callback_data="rooms_4"), InlineKeyboardButton("ללא הגבלה", callback_data="rooms_none")],
        ]
        await reply_target.reply_text("בחר <b>מינימום חדרים</b> בדירה:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return STATE_YEAR_OR_ROOMS


async def year_or_rooms_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = context.user_data["category"]
    data = query.data

    if cat == "cars":
        y_val = data.replace("year_", "")
        if y_val != "none":
            context.user_data["filters"]["min_year"] = int(y_val)
        return await prompt_gearbox(query.message)
    else:
        r_val = data.replace("rooms_", "")
        if r_val != "none":
            context.user_data["filters"]["min_rooms"] = int(r_val)
        return await finish_wizard(query.message, context)


async def year_or_rooms_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cat = context.user_data["category"]
    val = clean_numeric(update.message.text)
    if val:
        if cat == "cars":
            context.user_data["filters"]["min_year"] = val
        else:
            context.user_data["filters"]["min_rooms"] = val

    if cat == "cars":
        return await prompt_gearbox(update.message)
    else:
        return await finish_wizard(update.message, context)


async def prompt_gearbox(reply_target):
    keyboard = [
        [InlineKeyboardButton("🕹️ ידני בלבד", callback_data="gear_manual"), InlineKeyboardButton("🚗 אוטומט בלבד", callback_data="gear_auto")],
        [InlineKeyboardButton("הכל (לא משנה)", callback_data="gear_any")],
    ]
    await reply_target.reply_text("סוג <b>תיבת הילוכים</b>:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    return STATE_GEARBOX


async def gearbox_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    gear = query.data.replace("gear_", "")
    if gear in ["manual", "auto"]:
        context.user_data["filters"]["gearbox"] = gear

    keyboard = [
        [InlineKeyboardButton("בנזין", callback_data="fuel_petrol"), InlineKeyboardButton("דיזל", callback_data="fuel_diesel")],
        [InlineKeyboardButton("היברידי", callback_data="fuel_hybrid"), InlineKeyboardButton("חשמלי", callback_data="fuel_electric")],
        [InlineKeyboardButton("הכל (ללא הגבלה)", callback_data="fuel_any")],
    ]
    await query.edit_message_text("סוג <b>דלק</b> מועדף:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    return STATE_FUEL_TYPE


async def fuel_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    fuel = query.data.replace("fuel_", "")
    if fuel != "any":
        context.user_data["filters"]["fuel_type"] = fuel

    keyboard = [
        [InlineKeyboardButton("יד 1 בלבד", callback_data="hand_1"), InlineKeyboardButton("עד יד 2", callback_data="hand_2")],
        [InlineKeyboardButton("עד יד 3", callback_data="hand_3"), InlineKeyboardButton("ללא הגבלת יד", callback_data="hand_none")],
    ]
    await query.message.reply_text("מהי <b>היד המקסימלית</b>?\nבחר מהכפתורים או <b>הקלד יד ידנית</b> (למשל: <code>2</code>):", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    return STATE_MAX_HAND


async def max_hand_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    h_data = query.data.replace("hand_", "")
    if h_data != "none":
        context.user_data["filters"]["max_hand"] = int(h_data)
    return await prompt_max_km(query.message)


async def max_hand_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    h = clean_numeric(update.message.text)
    if h:
        context.user_data["filters"]["max_hand"] = h
    return await prompt_max_km(update.message)


async def prompt_max_km(reply_target):
    keyboard = [
        [InlineKeyboardButton("עד 100,000 ק\"מ", callback_data="km_100000"), InlineKeyboardButton("עד 150,000 ק\"מ", callback_data="km_150000")],
        [InlineKeyboardButton("עד 190,000 ק\"מ", callback_data="km_190000"), InlineKeyboardButton("ללא הגבלת ק\"מ", callback_data="km_none")],
    ]
    await reply_target.reply_text("מהו <b>הקילומטראז' המקסימלי</b>?\nבחר מהכפתורים או <b>הקלד ק\"מ ידנית</b> (למשל: <code>190000</code>):", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    return STATE_MAX_KM


async def max_km_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    k_data = query.data.replace("km_", "")
    if k_data != "none":
        context.user_data["filters"]["max_km"] = int(k_data)
    return await finish_wizard(query.message, context)


async def max_km_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    km = clean_numeric(update.message.text)
    if km:
        context.user_data["filters"]["max_km"] = km
    return await finish_wizard(update.message, context)


async def finish_wizard(reply_target, context: ContextTypes.DEFAULT_TYPE):
    user_id = reply_target.chat.id
    channel_id = context.user_data.get("channel_id", str(user_id))
    category = context.user_data.get("category", "cars")
    filters_dict = context.user_data.get("filters", {})

    search_id = add_search_to_db(user_id, channel_id, category, filters_dict)

    summary = (
        "🎉 <b>החיפוש נשמר בהצלחה והופעל!</b>\n\n"
        f"🆔 <b>מזהה חיפוש:</b> <code>{search_id}</code>\n"
        f"📂 <b>קטגוריה:</b> {category}\n"
        f"📢 <b>יעד שליחה:</b> <code>{channel_id}</code>\n"
        f"⚙️ <b>סינונים שהוגדרו:</b> <code>{json.dumps(filters_dict, ensure_ascii=False)}</code>\n\n"
        "⚡ <i>מבצע כעת סריקה מול יד 2 ושולח מודעות מתאימות...</i>"
    )
    await reply_target.reply_text(summary, parse_mode="HTML")

    asyncio.create_task(scan_and_notify_searches(context.bot, specific_user_id=user_id))
    return ConversationHandler.END


async def cancel_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("הפעולה בוטלה.")
    else:
        await update.message.reply_text("הפעולה בוטלה.")
    return ConversationHandler.END


# ======================= פקודות ניהול =======================
async def list_searches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    searches = get_user_searches(user_id)
    if not searches:
        keyboard = [[InlineKeyboardButton("➕ צור חיפוש עכשיו", callback_data="btn_new_search")]]
        await update.effective_message.reply_text("אין לך חיפושים פעילים כרגע.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    msg = "📋 <b>החיפושים הפעילים שלך:</b>\n\n"
    keyboard = []
    for s_id, chan, cat, filt in searches:
        msg += f"• <b>מזהה {s_id}</b> | קטגוריה: {cat}\n  יעד: <code>{chan}</code>\n  סינון: <code>{filt}</code>\n\n"
        keyboard.append([InlineKeyboardButton(f"❌ מחק חיפוש {s_id}", callback_data=f"del_{s_id}")])

    keyboard.append([InlineKeyboardButton("🔍 בצע בדיקה עכשיו", callback_data="btn_check_now")])
    keyboard.append([InlineKeyboardButton("🔄 אפס היסטוריה ושלח שוב", callback_data="btn_clear_history")])
    await update.effective_message.reply_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def delete_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    s_id = clean_numeric(query.data.replace("del_", ""))
    if s_id and delete_search_from_db(s_id, update.effective_user.id):
        await query.edit_message_text(f"✅ חיפוש {s_id} נמחק בהצלחה.")
    else:
        await query.edit_message_text("חיפוש לא נמצא או שכבר נמחק.")


async def clear_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clear_seen_history(user_id)
    msg_text = "🔄 <b>היסטוריית המודעות אופסה בהצלחה!</b>\nבבדיקה הבאה כל המודעות התואמות יישלחו מחדש."
    if update.callback_query:
        await update.callback_query.answer("היסטוריה אופסה!")
        await update.callback_query.message.reply_text(msg_text, parse_mode="HTML")
    else:
        await update.message.reply_text(msg_text, parse_mode="HTML")


async def check_now_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer("מתחיל בדיקה...")
        status_msg = await update.callback_query.message.reply_text("🔍 סורק מודעות תואמות מ-Yad2...")
    else:
        status_msg = await update.message.reply_text("🔍 סורק מודעות תואמות מ-Yad2...")

    fetched, matched, seen, sent = await scan_and_notify_searches(context.bot, specific_user_id=update.effective_user.id)
    if sent > 0:
        await status_msg.edit_text(f"✅ <b>הבדיקה הסתיימה בהצלחה!</b>\nנמצאו ונשלחו {sent} מודעות חדשות מתוך {matched} מודעות תואמות (נסרקו {fetched} סה\"כ).")
    elif seen > 0:
        await status_msg.edit_text(
            f"ℹ️ <b>הבדיקה הסתיימה:</b>\nנמצאו {seen} מודעות תואמות לחיפוש שלך, אך כולן כבר נשלחו בעבר בערוץ.\n\n"
            f"💡 <i>רוצה לקבל אותן שוב? שלח /clear_history ואז /check_now</i>",
            parse_mode="HTML"
        )
    elif fetched > 0:
        await status_msg.edit_text(f"ℹ️ נסרקו {fetched} מודעות מיד 2, אך הן נפסלו בסינון.")
    else:
        await status_msg.edit_text("⚠️ הבדיקה הסתיימה. לא הוחזרו מודעות מיד 2 כרגע (ודא שיש חיבור רשת תקין).")


# ======================= Main =======================
def main():
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("שגיאה: יש להגדיר TELEGRAM_BOT_TOKEN בקובץ .env או במשתני הסביבה!")
        return

    init_db()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("new_search", new_search_entry),
            CallbackQueryHandler(new_search_entry, pattern="^btn_new_search$"),
        ],
        states={
            STATE_CATEGORY: [
                CallbackQueryHandler(category_chosen, pattern="^setcat_"),
                CallbackQueryHandler(cancel_wizard, pattern="^cancel_wizard$"),
            ],
            STATE_CHANNEL: [
                CallbackQueryHandler(channel_selected_callback, pattern="^dest_here$"),
                CallbackQueryHandler(cancel_wizard, pattern="^cancel_wizard$"),
                MessageHandler(filters.ALL & ~filters.COMMAND, channel_entered_message),
            ],
            STATE_MAKES_MULTI: [
                CallbackQueryHandler(makes_multi_callback, pattern="^(toggle_make_|make_all|make_done)"),
                CallbackQueryHandler(cancel_wizard, pattern="^cancel_wizard$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, makes_multi_text),
            ],
            STATE_AREAS_MULTI: [
                CallbackQueryHandler(areas_multi_callback, pattern="^(toggle_area_|area_all|area_done)"),
                CallbackQueryHandler(cancel_wizard, pattern="^cancel_wizard$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, areas_multi_text),
            ],
            STATE_MAX_PRICE: [
                CallbackQueryHandler(max_price_callback, pattern="^price_"),
                CallbackQueryHandler(cancel_wizard, pattern="^cancel_wizard$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, max_price_text),
            ],
            STATE_YEAR_OR_ROOMS: [
                CallbackQueryHandler(year_or_rooms_callback, pattern="^(year_|rooms_)"),
                CallbackQueryHandler(cancel_wizard, pattern="^cancel_wizard$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, year_or_rooms_text),
            ],
            STATE_GEARBOX: [
                CallbackQueryHandler(gearbox_chosen, pattern="^gear_"),
                CallbackQueryHandler(cancel_wizard, pattern="^cancel_wizard$"),
            ],
            STATE_FUEL_TYPE: [
                CallbackQueryHandler(fuel_chosen, pattern="^fuel_"),
                CallbackQueryHandler(cancel_wizard, pattern="^cancel_wizard$"),
            ],
            STATE_MAX_HAND: [
                CallbackQueryHandler(max_hand_callback, pattern="^hand_"),
                CallbackQueryHandler(cancel_wizard, pattern="^cancel_wizard$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, max_hand_text),
            ],
            STATE_MAX_KM: [
                CallbackQueryHandler(max_km_callback, pattern="^km_"),
                CallbackQueryHandler(cancel_wizard, pattern="^cancel_wizard$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, max_hand_text),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_wizard),
            CallbackQueryHandler(cancel_wizard, pattern="^cancel_wizard$"),
        ],
        per_chat=True,
        per_user=True,
        per_message=False,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("my_searches", list_searches))
    app.add_handler(CommandHandler("check_now", check_now_handler))
    app.add_handler(CommandHandler("clear_history", clear_history_handler))
    app.add_handler(CallbackQueryHandler(start_command, pattern="^btn_menu$"))
    app.add_handler(CallbackQueryHandler(list_searches, pattern="^btn_my_searches$"))
    app.add_handler(CallbackQueryHandler(check_now_handler, pattern="^btn_check_now$"))
    app.add_handler(CallbackQueryHandler(clear_history_handler, pattern="^btn_clear_history$"))
    app.add_handler(CallbackQueryHandler(delete_search_callback, pattern="^del_"))

    if app.job_queue:
        app.job_queue.run_repeating(periodic_check_job, interval=CHECK_INTERVAL_SECONDS, first=5)

    logging.info("הבוט פועל ומאזין...")
    app.run_polling()


if __name__ == "__main__":
    main()
