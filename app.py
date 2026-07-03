from flask import Flask, jsonify, render_template
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
import traceback

# =====================================================
# Load Environment Variables
# =====================================================
load_dotenv()

TWENTY_API_KEY = os.getenv("TWENTY_API_KEY")
TWENTY_API_URL = os.getenv("TWENTY_API_URL")

app = Flask(__name__)
# Allowing all origins for ease of frontend integration. 
# Update this with your Vercel URL in production for security.
CORS(app)

# =====================================================
# Global Cache Memory
# =====================================================
SERVER_CACHE = {
    "properties": None,
    "zones": None
}

MAX_LIMIT = 200
MAX_PAGES = 50

def get_headers():
    return {
        "Authorization": f"Bearer {TWENTY_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

def fetch_all(endpoint, collection_name):
    """Generic paginator for Twenty CRM endpoints."""
    headers = get_headers()
    all_records = []
    starting_after = None
    page = 0

    print(f"\n========== Fetching {collection_name} ==========")

    while True:
        page += 1
        if page > MAX_PAGES:
            print(f"⚠️ Hit MAX_PAGES while fetching {collection_name}")
            break

        params = {"depth": 1, "limit": MAX_LIMIT}
        if starting_after:
            params["starting_after"] = starting_after

        print("Calling:", f"{TWENTY_API_URL}{endpoint}")
        response = requests.get(
            f"{TWENTY_API_URL}{endpoint}",
            headers=headers,
            params=params
        )

        if response.status_code != 200:
            raise Exception(f"{endpoint} failed ({response.status_code})\n{response.text}")

        payload = response.json()
        page_records = payload.get("data", {}).get(collection_name, [])
        all_records.extend(page_records)

        page_info = payload.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        end_cursor = page_info.get("endCursor")

        print(f"Page {page}: {len(page_records)} records (Total={len(all_records)})")

        if not has_next or not end_cursor or end_cursor == starting_after:
            break

        starting_after = end_cursor

    print(f"✅ Finished {collection_name}: {len(all_records)} records\n")
    return all_records

# =====================================================
# API Routes
# =====================================================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/properties", methods=["GET"])
def get_properties():
    """STRICTLY READ-ONLY: Returns memory instantly or asks frontend to sync."""
    global SERVER_CACHE

    if SERVER_CACHE["properties"] is None:
        return jsonify({"message": "Cache empty. Needs manual sync.", "data": None}), 200

    return jsonify({
        "data": {
            "properties": SERVER_CACHE["properties"],
            "zones": SERVER_CACHE["zones"]
        }
    }), 200


@app.route("/api/sync", methods=["POST"])
def force_sync():
    """THE HEAVY LIFTER: Fetches fresh data from CRM and updates memory."""
    global SERVER_CACHE
    
    if not TWENTY_API_KEY or not TWENTY_API_URL:
        return jsonify({"error": "Missing TWENTY_API_KEY or TWENTY_API_URL"}), 500

    try:
        SERVER_CACHE["properties"] = fetch_all("properties", "properties")
        SERVER_CACHE["zones"] = fetch_all("zoneallocations", "zoneallocations")
        
        return jsonify({
            "message": "Sync successful",
            "data": {
                "properties": SERVER_CACHE["properties"],
                "zones": SERVER_CACHE["zones"]
            }
        }), 200
        
    except Exception as e:
        print("=" * 80)
        print("FULL EXCEPTION")
        traceback.print_exc()
        print("=" * 80)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("🚀 Jumbo Homes Backend")
    print(f"Running on port {port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)
