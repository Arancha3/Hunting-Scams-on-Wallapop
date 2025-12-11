import requests
import json
import time
from datetime import datetime, timezone
from statistics import median
import os

# ---------------------------------------
# CONFIG
# ---------------------------------------
URL = "https://api.wallapop.com/api/v3/search"

HEADERS = {
    "Host": "api.wallapop.com",
    "X-DeviceOS": "0"
}

KEYWORDS = ["iphone", "samsung", "xiaomi"]

# Taxonomía target: SMARTPHONES (ID = 9447)
TARGET_TAXONOMY = 9447

SUSPICIOUS_KEYWORDS = [
    "urgente", "chollo", "réplica", "imitación", "icloud", "bloqueado",
    "imei", "sin factura", "muy barato", "solo hoy", "liberado",
    "sin caja", "liquido", "sin probar", "nuevo a estrenar"
]

OUTPUT_DIR = "/var/log/wallapop"
GLOBAL_SEEN_PATH = os.path.join(OUTPUT_DIR, "wallapop_seen_ids_all.txt")


# ---------------------------------------
# PUBLICATION TIME CLEAN EXTRACTION
# ---------------------------------------
def extract_publication_time(item):
    raw = item.get("published_at") or item.get("created_at") or None

    if raw is None:
        return None

    # ISO8601 format
    if isinstance(raw, str) and "T" in raw:
        return raw

    # UNIX seconds
    if isinstance(raw, int) and raw < 10**11:
        return datetime.fromtimestamp(raw, tz=timezone.utc).isoformat().replace("+00:00", "Z")

    # UNIX milliseconds
    if isinstance(raw, int) and raw < 10**14:
        return datetime.fromtimestamp(raw / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")

    # UNIX microseconds
    if isinstance(raw, int):
        return datetime.fromtimestamp(raw / 1e6, tz=timezone.utc).isoformat().replace("+00:00", "Z")

    return None


# ---------------------------------------
# API CALL — DIRECT TAXONOMY FILTERING
# ---------------------------------------
def fetch_items(keyword):
    params = {
        "keywords": keyword,
        "source": "search_box",
        "order_by": "newest",
        "filters": json.dumps({
            "taxonomy_ids": [TARGET_TAXONOMY]
        })
    }

    r = requests.get(URL, params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()

    return data["data"]["section"]["payload"].get("items", [])


def fetch_all_items():
    all_items = []
    for kw in KEYWORDS:
        try:
            items = fetch_items(kw)
            all_items.extend(items)
            print(f"[OK] {len(items)} items para '{kw}'")
        except Exception as e:
            print(f"[ERROR] al buscar '{kw}': {e}")

    print(f"[INFO] Total items obtenidos: {len(all_items)}")
    return all_items


# ---------------------------------------
# Stats for risk scoring
# ---------------------------------------
def compute_stats(items):
    prices = []
    seller_count = {}

    for item in items:
        try:
            prices.append(item["price"]["amount"])
        except:
            pass

        seller = item.get("user_id")
        if seller:
            seller_count[seller] = seller_count.get(seller, 0) + 1

    med = median(prices) if prices else 0
    return med, seller_count


# ---------------------------------------
# RISK SCORING (100-POINT SYSTEM)
# ---------------------------------------
def compute_risk(item, median_price, seller_count):
    score = 0
    factors = []
    desc = (item.get("description") or "").lower()
    title = (item.get("title") or "").lower()
    price = item["price"]["amount"]
    seller_id = item.get("user_id")

    # -----------------------------
    # A — PRICE ANOMALIES
    # -----------------------------
    if price < 0.5 * median_price:
        score += 40
        factors.append("Very low price (<50% median)")

    if price < 30:
        score += 20
        factors.append("Extremely low price (<30€)")

    # -----------------------------
    # B — KEYWORD SUSPICION
    # -----------------------------
    found_keywords = [kw for kw in SUSPICIOUS_KEYWORDS if kw in desc]
    if found_keywords:
        score += 20
        factors.append("Keywords: " + ", ".join(found_keywords))

    # -----------------------------
    # C — SELLER BEHAVIOUR
    # -----------------------------
    if seller_id:
        posts = seller_count.get(seller_id, 0)

        if posts > 20:
            score += 20
            factors.append("Seller posts many items (>20/day)")

        if posts == 1:
            score += 10
            factors.append("Seller with only one listing")

    # -----------------------------
    # D — TEXT QUALITY / ANOMALIES
    # -----------------------------
    if len(desc) < 20:
        score += 10
        factors.append("Very short description")

    if "no funciona" in desc and price > 100:
        score += 10
        factors.append("Contradiction: 'no funciona' but high price")

    # -----------------------------
    # E — IMAGE ANALYSIS (ROBUST)
    # -----------------------------
    urls = []
    images = item.get("images", [])

    # Case A: images is dict
    if isinstance(images, dict):
        urls = images.get("urls", {}).get("big", [])

    # Case B: images is list of dicts
    elif isinstance(images, list):
        for img in images:
            if isinstance(img, dict):
                big = img.get("urls", {}).get("big", [])
                if isinstance(big, list):
                    urls.extend(big)

    if not isinstance(urls, list):
        urls = []

    num_images = len(urls)

    if num_images == 1:
        score += 15
        factors.append("Only one image (possible stock photo)")

    if num_images > 2 and len(set(urls)) < len(urls) / 2:
        score += 10
        factors.append("Repeated images (possible fake listing)")

    # -----------------------------
    # F — GENERIC TITLE
    # -----------------------------
    generic_titles = ["movil", "smartphone", "teléfono"]
    if title in generic_titles:
        score += 15
        factors.append("Generic title (model not specified)")

    # -----------------------------
    # G — HIGH-END WITH WEAK DESCRIPTION
    # -----------------------------
    high_end = ["13 pro", "14 pro", "15 pro", "ultra"]
    if any(h in title for h in high_end) and len(desc) < 30:
        score += 20
        factors.append("High-end model with weak description")

    # -----------------------------
    # H — OLD MODELS OVERPRICED
    # -----------------------------
    old_models = ["iphone 6", "iphone 7", "iphone 8", "iphone se (1"]
    if any(o in title for o in old_models) and price > median_price * 1.5:
        score += 10
        factors.append("Overpriced old model")

    return min(score, 100), found_keywords, factors


# ---------------------------------------
# DEDUPLICATION
# ---------------------------------------
def load_seen_ids():
    if not os.path.exists(GLOBAL_SEEN_PATH):
        return set()
    with open(GLOBAL_SEEN_PATH, "r") as f:
        return set(line.strip() for line in f.readlines())


def append_seen_ids(ids):
    with open(GLOBAL_SEEN_PATH, "a") as f:
        for i in ids:
            f.write(i + "\n")


# ---------------------------------------
# SAVE ITEMS
# ---------------------------------------
def save_items(items):
    today = datetime.utcnow().strftime("%Y%m%d")
    json_path = os.path.join(OUTPUT_DIR, f"wallapop_smartphones_{today}.json")

    seen_ids = load_seen_ids()
    new_items = []
    new_ids = []

    for item in items:
        item_id = item.get("id")
        if not item_id:
            continue
        if item_id in seen_ids:
            continue

        new_items.append(item)
        new_ids.append(item_id)

    if not new_items:
        print("[INFO] No hay anuncios nuevos.")
        return

    with open(json_path, "a", encoding="utf-8") as f:
        for it in new_items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    append_seen_ids(new_ids)
    print(f"[OK] Guardados {len(new_items)} nuevos anuncios.")


# ---------------------------------------
# MAIN LOOP (30 MIN)
# ---------------------------------------
def main_loop():
    print("=== Poller Smartphone TAXONOMY 9447 ===")

    while True:
        print("\n--- Nueva ejecución ---", datetime.utcnow().isoformat())

        items = fetch_all_items()

        print(f"[INFO] Items recibidos directamente por taxonomía 9447: {len(items)}")

        if not items:
            print("[WARN] No se recibieron smartphones.")
            time.sleep(1800)
            continue

        median_price, seller_count = compute_stats(items)
        print(f"[INFO] Precio mediano: {median_price}")

        enriched = []

        for item in items:
            # Publication timestamp
            pub = extract_publication_time(item)
            if pub:
                item["publication_time_at"] = pub

            # GEO → Elastic Maps
            lat = item.get("location", {}).get("latitude")
            lon = item.get("location", {}).get("longitude")
            if lat is not None and lon is not None:
                item["location_geo"] = {"lat": float(lat), "lon": float(lon)}

            # RISK SCORE
            score, kws, factors = compute_risk(item, median_price, seller_count)

            item["enrichment"] = {
                "median_price": float(median_price),
                "risk_score": float(score),
                "suspicious_keywords": kws,
                "risk_factors": factors
            }

            enriched.append(item)

        save_items(enriched)

        print("[INFO] Esperando 30 minutos...")
        time.sleep(1800)


if __name__ == "__main__":
    main_loop()

