"""
Air Quality Tracker
===================
Fetches real-time and historical air quality data from the OpenAQ v3 API.
Tracks PM2.5, PM10, NO2, O3, CO, and SO2 against WHO air quality guidelines.

Usage:
    python tracker.py                             # Demo mode (no API key needed)
    python tracker.py --city "Halifax"            # Live data (requires API key)
    python tracker.py --city "Toronto" --days 7
    python tracker.py --list-cities
    python tracker.py --setup                     # Help setting up your API key
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone


# ── WHO Air Quality Guidelines (2021) ─────────────────────────────────────────
WHO_LIMITS = {
    "pm25":  {"name": "PM2.5 (Fine Particles)",   "daily": 15.0,   "unit": "µg/m³"},
    "pm10":  {"name": "PM10 (Coarse Particles)",   "daily": 45.0,   "unit": "µg/m³"},
    "no2":   {"name": "Nitrogen Dioxide (NO₂)",    "daily": 25.0,   "unit": "µg/m³"},
    "o3":    {"name": "Ozone (O₃)",                "daily": 100.0,  "unit": "µg/m³"},
    "co":    {"name": "Carbon Monoxide (CO)",       "daily": 4000.0, "unit": "µg/m³"},
    "so2":   {"name": "Sulphur Dioxide (SO₂)",     "daily": 40.0,   "unit": "µg/m³"},
}

AQI_CATEGORIES = [
    (0,   50,  "Good",                  "🟢", "Air quality is satisfactory."),
    (51,  100, "Moderate",              "🟡", "Acceptable; some pollutants may concern sensitive individuals."),
    (101, 150, "Unhealthy (Sensitive)", "🟠", "Sensitive groups may experience health effects."),
    (151, 200, "Unhealthy",             "🔴", "Everyone may begin to experience health effects."),
    (201, 300, "Very Unhealthy",        "🟣", "Health alert: everyone may experience serious effects."),
    (301, 500, "Hazardous",             "⚫", "Emergency conditions. Entire population affected."),
]

EXAMPLE_CITIES = ["Halifax", "Toronto", "Vancouver", "Montreal", "London", "New York", "Delhi", "Beijing"]
API_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".openaq_api_key")


# ── API Key Management ─────────────────────────────────────────────────────────

def load_api_key():
    key = os.environ.get("OPENAQ_API_KEY", "").strip()
    if key:
        return key
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE) as f:
            key = f.read().strip()
        if key:
            return key
    return None


def save_api_key(key):
    with open(API_KEY_FILE, "w") as f:
        f.write(key.strip())
    print(f"  API key saved.")


def print_setup_instructions():
    print("""
  ── How to get a free OpenAQ API key ────────────────────────────────

  1. Go to: https://explore.openaq.org/register
  2. Sign up with just an email and password (it's free)
  3. After registering, go to: https://explore.openaq.org/account
  4. Copy your API key

  Then run this command (replace the key with yours):
      python tracker.py --save-key YOUR_API_KEY_HERE

  After that, run:
      python tracker.py --city "Halifax"

  ────────────────────────────────────────────────────────────────────
""")


# ── OpenAQ v3 API ─────────────────────────────────────────────────────────────

def api_get(url, api_key):
    req = urllib.request.Request(url, headers={
        "X-API-Key": api_key,
        "Accept": "application/json",
        "User-Agent": "AirQualityTracker/2.0",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def fetch_live_data(city, days, api_key):
    print(f"  Searching for monitoring stations in {city}...")
    url = "https://api.openaq.org/v3/locations?" + urllib.parse.urlencode({
        "city": city, "limit": 5,
    })
    data = api_get(url, api_key)
    locations = data.get("results", [])

    if not locations:
        raise ValueError(f"No monitoring stations found for '{city}'.")

    print(f"  Found {len(locations)} station(s). Fetching measurements...")

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    grouped = {}

    for loc in locations[:3]:
        loc_id = loc["id"]
        try:
            sensors_data = api_get(
                f"https://api.openaq.org/v3/locations/{loc_id}/sensors", api_key
            )
        except Exception:
            continue

        for sensor in sensors_data.get("results", []):
            raw_param = sensor.get("parameter", {}).get("name", "").lower().replace(".", "").replace(" ", "")
            # Map to our keys
            param = raw_param if raw_param in WHO_LIMITS else None
            if param is None:
                continue

            sensor_id = sensor["id"]
            try:
                meas = api_get(
                    f"https://api.openaq.org/v3/sensors/{sensor_id}/days?"
                    + urllib.parse.urlencode({
                        "date_from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "date_to": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "limit": 100,
                    }),
                    api_key,
                )
            except Exception:
                continue

            for m in meas.get("results", []):
                val = m.get("value")
                if val is None:
                    continue
                try:
                    val = float(val)
                except (TypeError, ValueError):
                    continue
                if val >= 0:
                    grouped.setdefault(param, []).append(val)

    return grouped


# ── Sample Data ────────────────────────────────────────────────────────────────

def generate_sample_data(city, days):
    import random
    random.seed(sum(ord(c) for c in city))
    baselines = {
        "pm25": random.uniform(4, 18), "pm10": random.uniform(10, 35),
        "no2": random.uniform(8, 30), "o3": random.uniform(40, 90),
        "co": random.uniform(300, 800), "so2": random.uniform(5, 25),
    }
    return {
        p: [max(0, round(random.gauss(b, b * 0.25), 2)) for _ in range(days * 24)]
        for p, b in baselines.items()
    }


# ── Display ────────────────────────────────────────────────────────────────────

def aqi_from_pm25(pm25):
    for lo_c, hi_c, lo_i, hi_i in [
        (0.0,12.0,0,50),(12.1,35.4,51,100),(35.5,55.4,101,150),
        (55.5,150.4,151,200),(150.5,250.4,201,300),(250.5,500.4,301,500)
    ]:
        if lo_c <= pm25 <= hi_c:
            return int(((hi_i - lo_i) / (hi_c - lo_c)) * (pm25 - lo_c) + lo_i)
    return 500


def aqi_category(aqi):
    for lo, hi, label, icon, desc in AQI_CATEGORIES:
        if lo <= aqi <= hi:
            return {"label": label, "icon": icon, "description": desc}
    return {"label": "Hazardous", "icon": "⚫", "description": "Emergency conditions."}


def compute_stats(values):
    if not values:
        return {}
    n, mean = len(values), sum(values) / len(values)
    return {"mean": round(mean, 2), "min": round(min(values), 2), "max": round(max(values), 2), "count": n}


def draw_bar(value, max_val, width=30):
    if max_val == 0:
        return "░" * width
    filled = int(min(value / max_val, 1.0) * width)
    return "█" * filled + "░" * (width - filled)


def print_dashboard(grouped, city, days):
    width = 70
    print("\n" + "═" * width)
    print(f"  🌬️  AIR QUALITY TRACKER")
    print(f"  Location: {city}  |  Period: Last {days} days  |  {datetime.now().strftime('%Y-%m-%d')}")
    print("═" * width)

    if not grouped:
        print("  No data found. Try a different city or run in demo mode.")
        print("═" * width + "\n")
        return

    if "pm25" in grouped:
        aqi = aqi_from_pm25(sum(grouped["pm25"]) / len(grouped["pm25"]))
        cat = aqi_category(aqi)
        print(f"\n  {cat['icon']}  Overall AQI (PM2.5 based): {aqi} — {cat['label']}")
        print(f"      {cat['description']}")

    print()
    for param, info in WHO_LIMITS.items():
        if param not in grouped:
            continue
        stats = compute_stats(grouped[param])
        mean, limit = stats["mean"], info["daily"]
        pct = (mean / limit * 100) if limit else 0
        status = "✅" if mean <= limit else "⚠️ "

        print(f"  {status} {info['name']}")
        print(f"     Mean: {mean} {info['unit']}  |  Min: {stats['min']}  |  Max: {stats['max']}  |  n={stats['count']}")
        if limit:
            print(f"     [{draw_bar(mean, limit)}] {pct:.0f}% of WHO daily limit ({limit} {info['unit']})")
        print()

    print("═" * width)
    violations = sum(
        1 for p, info in WHO_LIMITS.items()
        if p in grouped and info["daily"] and compute_stats(grouped[p])["mean"] > info["daily"]
    )
    print(f"  {len([p for p in WHO_LIMITS if p in grouped])} pollutants tracked | {violations} exceeding WHO daily guidelines")
    print("═" * width + "\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Air Quality Tracker — monitor air quality vs WHO guidelines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tracker.py                          # Demo mode (no API key needed)
  python tracker.py --setup                  # How to get a free API key
  python tracker.py --save-key YOUR_KEY      # Save your API key
  python tracker.py --city "Halifax"         # Live data for Halifax
  python tracker.py --city "Toronto" --days 14
  python tracker.py --list-cities
  python tracker.py --export report.json
        """
    )
    parser.add_argument("--city", default=None)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--export", metavar="FILE")
    parser.add_argument("--list-cities", action="store_true")
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--save-key", metavar="KEY")
    args = parser.parse_args()

    if args.list_cities:
        print("\nExample cities:\n" + "\n".join(f"  {c}" for c in EXAMPLE_CITIES) + "\n")
        return

    if args.setup:
        print_setup_instructions()
        return

    if args.save_key:
        save_api_key(args.save_key)
        print('  Done! Now run: python tracker.py --city "Halifax"')
        return

    if args.city is None:
        print("\nAir Quality Tracker — Demo Mode")
        print("  Run with --setup to get a free API key for live data.\n")
        grouped = generate_sample_data("Halifax", args.days)
        print_dashboard(grouped, "Halifax (demo)", args.days)
        if args.export:
            json.dump(grouped, open(args.export, "w"), indent=2)
        return

    api_key = load_api_key()
    if not api_key:
        print("\n  No API key found. Run:  python tracker.py --setup\n")
        sys.exit(1)

    print(f"\nAir Quality Tracker — {args.city}")
    try:
        grouped = fetch_live_data(args.city, args.days, api_key)
        if not grouped:
            print("  No data returned — showing demo data instead.\n")
            grouped = generate_sample_data(args.city, args.days)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("  Invalid API key. Get a new one at: https://explore.openaq.org/account")
            sys.exit(1)
        print(f"  HTTP {e.code} — showing demo data instead.\n")
        grouped = generate_sample_data(args.city, args.days)
    except Exception as e:
        print(f"  Error: {e}\n  Showing demo data instead.\n")
        grouped = generate_sample_data(args.city, args.days)

    print_dashboard(grouped, args.city, args.days)
    if args.export:
        json.dump(grouped, open(args.export, "w"), indent=2)
        print(f"  Saved to {args.export}")


if __name__ == "__main__":
    main()
