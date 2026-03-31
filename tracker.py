"""
Air Quality Tracker
===================
Fetches real-time and historical air quality data from the OpenAQ API.
Tracks PM2.5, PM10, NO2, O3, CO, and SO2 against WHO air quality guidelines.

Usage:
    python tracker.py                          # Demo mode (sample data)
    python tracker.py --city "Halifax"         # Fetch live data for a city
    python tracker.py --city "Toronto" --days 7
    python tracker.py --list-cities
"""

import argparse
import json
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta


# WHO Air Quality Guidelines (2021)
WHO_LIMITS = {
    "pm25":  {"name": "PM2.5 (Fine Particles)", "annual": 5.0,  "daily": 15.0,  "unit": "µg/m³"},
    "pm10":  {"name": "PM10 (Coarse Particles)", "annual": 15.0, "daily": 45.0,  "unit": "µg/m³"},
    "no2":   {"name": "Nitrogen Dioxide (NO₂)",  "annual": 10.0, "daily": 25.0,  "unit": "µg/m³"},
    "o3":    {"name": "Ozone (O₃)",              "annual": None, "daily": 100.0, "unit": "µg/m³"},
    "co":    {"name": "Carbon Monoxide (CO)",     "annual": None, "daily": 4000.0,"unit": "µg/m³"},
    "so2":   {"name": "Sulphur Dioxide (SO₂)",   "annual": None, "daily": 40.0,  "unit": "µg/m³"},
}

AQI_CATEGORIES = [
    (0,   50,  "Good",            "🟢", "Air quality is satisfactory."),
    (51,  100, "Moderate",        "🟡", "Acceptable; some pollutants may be a concern for sensitive individuals."),
    (101, 150, "Unhealthy (Sensitive)", "🟠", "Sensitive groups may experience health effects."),
    (151, 200, "Unhealthy",       "🔴", "Everyone may begin to experience health effects."),
    (201, 300, "Very Unhealthy",  "🟣", "Health alert: everyone may experience serious effects."),
    (301, 500, "Hazardous",       "⚫", "Emergency conditions. Entire population affected."),
]

EXAMPLE_CITIES = ["Halifax", "Toronto", "Vancouver", "Montreal", "London", "New York", "Delhi", "Beijing"]


def aqi_from_pm25(pm25: float) -> int:
    """Estimate US AQI from PM2.5 concentration (µg/m³)."""
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 500.4, 301, 500),
    ]
    for lo_c, hi_c, lo_i, hi_i in breakpoints:
        if lo_c <= pm25 <= hi_c:
            aqi = ((hi_i - lo_i) / (hi_c - lo_c)) * (pm25 - lo_c) + lo_i
            return int(round(aqi))
    return 500


def aqi_category(aqi: int) -> dict:
    for lo, hi, label, icon, desc in AQI_CATEGORIES:
        if lo <= aqi <= hi:
            return {"label": label, "icon": icon, "description": desc}
    return {"label": "Hazardous", "icon": "⚫", "description": "Emergency conditions."}


def fetch_openaq(city: str, days: int) -> list[dict]:
    """Fetch measurements from OpenAQ API v2."""
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    url = (
        "https://api.openaq.org/v2/measurements?"
        + urllib.parse.urlencode({
            "city": city,
            "date_from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "date_to": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit": 1000,
            "sort": "desc",
        })
    )
    print(f"  Fetching air quality data for {city} from OpenAQ...")
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "AirQualityTracker/1.0",
            "Accept": "application/json"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        return data.get("results", [])
    except Exception as e:
        print(f"  [Warning] Could not fetch live data: {e}")
        print("  Using sample data for demonstration.\n")
        return generate_sample_data(city, days)


def generate_sample_data(city: str, days: int) -> list[dict]:
    """Generate realistic sample air quality data."""
    import random
    random.seed(sum(ord(c) for c in city))

    # Vary baseline by "city" for realism
    baselines = {
        "pm25": random.uniform(4, 18),
        "pm10": random.uniform(10, 35),
        "no2":  random.uniform(8, 30),
        "o3":   random.uniform(40, 90),
        "co":   random.uniform(300, 800),
        "so2":  random.uniform(5, 25),
    }

    results = []
    end = datetime.utcnow()
    for i in range(days * 24):  # hourly
        timestamp = (end - timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for param, base in baselines.items():
            value = max(0, round(random.gauss(base, base * 0.25), 2))
            results.append({
                "parameter": param,
                "value": value,
                "unit": "µg/m³",
                "date": {"utc": timestamp},
                "city": city,
            })
    return results


def parse_measurements(records: list[dict]) -> dict:
    """Group measurements by parameter."""
    grouped = {}
    for r in records:
        param = r.get("parameter", "").lower()
        try:
            value = float(r.get("value", 0))
        except (TypeError, ValueError):
            continue
        if value < 0:
            continue
        if param not in grouped:
            grouped[param] = []
        grouped[param].append(value)
    return grouped


def compute_stats(values: list[float]) -> dict:
    if not values:
        return {}
    n = len(values)
    mean = sum(values) / n
    return {
        "mean": round(mean, 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "count": n,
    }


def draw_bar(value: float, max_val: float, width: int = 30) -> str:
    if max_val == 0:
        return "░" * width
    filled = int(min(value / max_val, 1.0) * width)
    return "█" * filled + "░" * (width - filled)


def print_dashboard(grouped: dict, city: str, days: int):
    width = 70
    print("\n" + "═" * width)
    print(f"  🌬️  AIR QUALITY TRACKER")
    print(f"  Location: {city}  |  Period: Last {days} days  |  {datetime.now().strftime('%Y-%m-%d')}")
    print("═" * width)

    if not grouped:
        print("  No data found. Try a different city or run in demo mode.")
        print("═" * width + "\n")
        return

    # Show AQI estimate if PM2.5 available
    if "pm25" in grouped:
        mean_pm25 = sum(grouped["pm25"]) / len(grouped["pm25"])
        aqi = aqi_from_pm25(mean_pm25)
        cat = aqi_category(aqi)
        print(f"\n  {cat['icon']}  Overall AQI (PM2.5 based): {aqi} — {cat['label']}")
        print(f"      {cat['description']}")

    print()
    for param, info in WHO_LIMITS.items():
        if param not in grouped:
            continue
        values = grouped[param]
        stats = compute_stats(values)
        daily_limit = info["daily"]
        mean = stats["mean"]

        pct = (mean / daily_limit * 100) if daily_limit else 0
        bar = draw_bar(mean, daily_limit)
        status = "✅" if mean <= daily_limit else "⚠️ "

        print(f"  {status} {info['name']}")
        print(f"     Mean: {mean} {info['unit']}  |  Min: {stats['min']}  |  Max: {stats['max']}  |  n={stats['count']}")
        if daily_limit:
            print(f"     [{bar}] {pct:.0f}% of WHO daily limit ({daily_limit} {info['unit']})")
        print()

    print("═" * width)
    violations = sum(
        1 for p, info in WHO_LIMITS.items()
        if p in grouped and info["daily"] and compute_stats(grouped[p])["mean"] > info["daily"]
    )
    print(f"  {len([p for p in WHO_LIMITS if p in grouped])} pollutants tracked | {violations} exceeding WHO daily guidelines")
    print("═" * width + "\n")


def export_json(grouped: dict, city: str, filename: str):
    out = {
        "city": city,
        "generated": datetime.now().isoformat(),
        "who_guidelines": WHO_LIMITS,
        "results": {}
    }
    for param, values in grouped.items():
        stats = compute_stats(values)
        limit = WHO_LIMITS.get(param, {}).get("daily")
        out["results"][param] = {
            "stats": stats,
            "who_daily_limit": limit,
            "exceeds_limit": bool(limit and stats.get("mean", 0) > limit),
        }
    with open(filename, "w") as f:
        json.dump(out, f, indent=2)
    print(f"  Report saved to {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Air Quality Tracker — monitor air quality vs WHO guidelines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tracker.py                        # Demo mode (sample data)
  python tracker.py --city "Halifax"       # Live data for Halifax
  python tracker.py --city "Toronto" --days 14
  python tracker.py --list-cities          # Show example cities
  python tracker.py --export report.json  # Export results
        """
    )
    parser.add_argument("--city", default="DEMO", help="City name (e.g. 'Halifax', 'Toronto')")
    parser.add_argument("--days", type=int, default=7, help="Days of history to analyze (default: 7)")
    parser.add_argument("--export", metavar="FILE", help="Export results to JSON")
    parser.add_argument("--list-cities", action="store_true", help="Show example cities")
    args = parser.parse_args()

    if args.list_cities:
        print("\nExample cities with OpenAQ data:")
        for c in EXAMPLE_CITIES:
            print(f"  {c}")
        print()
        return

    city = "Halifax (demo)" if args.city == "DEMO" else args.city

    if args.city == "DEMO":
        print(f"\nAir Quality Tracker — Demo Mode")
        print("  (Use --city to fetch live data from OpenAQ)\n")
        records = generate_sample_data("Halifax", args.days)
    else:
        print(f"\nAir Quality Tracker — {city}")
        records = fetch_openaq(args.city, args.days)

    grouped = parse_measurements(records)
    print_dashboard(grouped, city, args.days)

    if args.export:
        export_json(grouped, city, args.export)


if __name__ == "__main__":
    main()
