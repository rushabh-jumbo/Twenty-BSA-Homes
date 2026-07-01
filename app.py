from flask import Flask, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv

# =====================================================
# Load Environment Variables
# =====================================================

load_dotenv()

TWENTY_API_KEY = os.getenv("TWENTY_API_KEY")
TWENTY_API_URL = os.getenv("TWENTY_API_URL")

app = Flask(__name__)
CORS(app)

MAX_LIMIT = 200
MAX_PAGES = 50


def get_headers():
    return {
        "Authorization": f"Bearer {TWENTY_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }


def fetch_all(endpoint, collection_name):
    """
    Generic paginator for Twenty CRM endpoints.
    """

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

        params = {
            "depth": 1,
            "limit": MAX_LIMIT
        }

        if starting_after:
            params["starting_after"] = starting_after

        print("Calling:", f"{TWENTY_API_URL}properties")
        response = requests.get(
            f"{TWENTY_API_URL}{endpoint}",
            headers=headers,
            params=params
        )

        if response.status_code != 200:
            raise Exception(
                f"{endpoint} failed "
                f"({response.status_code})\n"
                f"{response.text}"
            )

        payload = response.json()

        page_records = payload.get("data", {}).get(collection_name, [])

        all_records.extend(page_records)

        page_info = payload.get("pageInfo", {})

        has_next = page_info.get("hasNextPage", False)
        end_cursor = page_info.get("endCursor")

        print(
            f"Page {page}: "
            f"{len(page_records)} records "
            f"(Total={len(all_records)})"
        )

        if not has_next:
            break

        if not end_cursor:
            print("⚠️ endCursor missing.")
            break

        if end_cursor == starting_after:
            print("⚠️ Cursor did not advance.")
            break

        starting_after = end_cursor

    print(f"✅ Finished {collection_name}: {len(all_records)} records\n")

    return all_records


@app.route("/api/properties", methods=["GET"])
def get_properties():

    if not TWENTY_API_KEY or not TWENTY_API_URL:
        return jsonify({
            "error": "Missing TWENTY_API_KEY or TWENTY_API_URL"
        }), 500

    try:

        properties = fetch_all(
            "properties",
            "properties"
        )

        zones = fetch_all(
            "zoneallocations",
            "zoneallocations"
        )

        return jsonify({
            "data": {
                "properties": properties,
                "zones": zones
            }
        })

    except Exception as e:
    import traceback

    print("=" * 80)
    print("FULL EXCEPTION")
    traceback.print_exc()
    print("=" * 80)

    return jsonify({
        "error": str(e)
    }), 500

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    print("=" * 60)
    print("🚀 Jumbo Homes Backend")
    print(f"Running on port {port}")
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
