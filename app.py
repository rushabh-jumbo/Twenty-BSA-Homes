from flask import Flask, jsonify, render_template
from flask_cors import CORS
import os
import requests
import threading
import traceback
import time
from dotenv import load_dotenv

# =====================================================
# Load Environment Variables
# =====================================================
load_dotenv()

TWENTY_API_KEY = os.getenv("TWENTY_API_KEY")
TWENTY_API_URL = os.getenv("TWENTY_API_URL")

app = Flask(__name__)
CORS(app)

# =====================================================
# Global Cache Memory
# =====================================================
SERVER_CACHE = {
    "status": "empty",  # States: 'empty', 'syncing', 'ready', 'error'
    "properties": None,
    "zones": None
}

MAX_LIMIT = 50
MAX_PAGES = 200

def get_headers():
    return {
        "Authorization": f"Bearer {TWENTY_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

def fetch_all(endpoint, collection_name):
    """Generic paginator for Twenty CRM endpoints with retry logic."""
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

        max_retries = 3
        payload = None
        
        for attempt in range(max_retries):
            response = requests.get(
                f"{TWENTY_API_URL}{endpoint}",
                headers=headers,
                params=params
            )

            if response.status_code == 200:
                payload = response.json()
                break
            else:
                print(f"⚠️ Attempt {attempt + 1} failed for {endpoint}: {response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(2) # Wait 2 seconds before retrying
                else:
                    raise Exception(f"{endpoint} failed after {max_retries} attempts ({response.status_code})\n{response.text}")

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

def background_sync_task():
    """Runs in the background so Render doesn't timeout the HTTP request."""
    global SERVER_CACHE
    try:
        SERVER_CACHE["status"] = "syncing"
        SERVER_CACHE["properties"] = fetch_all("properties", "properties")
        SERVER_CACHE["zones"] = fetch_all("zoneallocations", "zoneallocations")
        SERVER_CACHE["status"] = "ready"
    except Exception as e:
        print("=" * 80)
        print("BACKGROUND SYNC EXCEPTION")
        traceback.print_exc()
        print("=" * 80)
        SERVER_CACHE["status"] = "error"

# =====================================================
# API Routes
# =====================================================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/properties", methods=["GET"])
def get_properties():
    """Provides the current status and memory (if ready)."""
    global SERVER_CACHE

    return jsonify({
        "status": SERVER_CACHE["status"],
        "data": {
            "properties": SERVER_CACHE["properties"],
            "zones": SERVER_CACHE["zones"]
        }
    }), 200

@app.route("/api/sync", methods=["POST"])
def force_sync():
    """Instantly triggers the background thread and returns 202."""
    global SERVER_CACHE
    
    if not TWENTY_API_KEY or not TWENTY_API_URL:
        return jsonify({"error": "Missing TWENTY_API_KEY or TWENTY_API_URL"}), 500

    if SERVER_CACHE["status"] == "syncing":
        return jsonify({"message": "Sync already in progress"}), 200

    thread = threading.Thread(target=background_sync_task)
    thread.start()
    
    return jsonify({"message": "Background sync started"}), 202

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("🚀 Jumbo Homes Backend")
    print(f"Running on port {port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)
