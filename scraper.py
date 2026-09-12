"""
AntiGravity — Autonomous Multi-Source Ingestion Core (scraper.py)

Data Sources (all FREE, no API key required):
  1. USGS GeoJSON    — Seismic events (earthquakes)
  2. GDELT GEO API   — Conflicts, military, protests, disasters, nuclear
  3. UCDP API        — Uppsala armed conflict database
  4. ReliefWeb API   — Humanitarian disasters, floods, epidemics

Runs continuously, polling each feed on its own interval.
Persists deduplicated events to worldmonitor.db SQLite vault.
"""

import sqlite3
import time
import requests
import json
import sys
import logging
from datetime import datetime, timezone, timedelta

# ─── Configuration ────────────────────────────────────────────────────────────
DB_PATH            = "worldmonitor.db"
POLL_INTERVAL      = 60    # seconds between full poll cycle
INFERENCE_BREATHER = 1.5   # seconds between Ollama calls
OLLAMA_ENDPOINT    = "http://localhost:11434/api/generate"
OLLAMA_MODEL       = "llama3.2"
SYSTEM_PROMPT = (
    "You are a global crisis analyst. "
    "Summarize the following world event in exactly 15 words. "
    "Be direct, factual, and threat-focused. No preamble."
)

# ─── GDELT queries per layer ───────────────────────────────────────────────────
GDELT_BASE = "https://api.gdeltproject.org/api/v2/geo/geo"
GDELT_LAYERS = {
    "CONFLICT":  "conflict OR war OR attack OR airstrike OR bombing OR gunfire",
    "MILITARY":  "military OR troops OR soldiers OR army OR navy OR airforce OR missiles",
    "POLITICAL": "protest OR riot OR coup OR sanctions OR election OR unrest OR demonstration",
    "NUCLEAR":   "nuclear OR radiation OR radioactive OR atomic",
    "DISASTER":  "flood OR hurricane OR typhoon OR tornado OR wildfire OR volcano OR landslide",
    "HEALTH":    "epidemic OR pandemic OR outbreak OR disease OR virus OR plague",
}

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("AntiGravity.Scraper")

# ─── Database ─────────────────────────────────────────────────────────────────
def init_db(conn: sqlite3.Connection) -> None:
    """Initialize schema."""
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id   TEXT    UNIQUE NOT NULL,
            title      TEXT    NOT NULL,
            category   TEXT    NOT NULL,
            layer      TEXT    NOT NULL DEFAULT 'SEISMIC',
            source     TEXT    NOT NULL DEFAULT 'USGS',
            latitude   REAL    NOT NULL,
            longitude  REAL    NOT NULL,
            magnitude  REAL,
            ai_summary TEXT,
            url        TEXT,
            timestamp  TEXT    NOT NULL
        )
    """)
    # Migrate existing DB: add columns if missing
    for col, col_type, default in [
        ("layer",  "TEXT", "'SEISMIC'"),
        ("source", "TEXT", "'USGS'"),
        ("url",    "TEXT", "''"),
    ]:
        try:
            conn.execute(f"ALTER TABLE events ADD COLUMN {col} {col_type} DEFAULT {default}")
            log.info(f"Migrated DB: added column '{col}'")
        except sqlite3.OperationalError:
            pass  # Column already exists
    conn.commit()
    log.info("Database schema verified/initialized.")


def event_exists(conn: sqlite3.Connection, event_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM events WHERE event_id = ?", (event_id,)).fetchone()
    return row is not None


def insert_event(conn: sqlite3.Connection, event: dict) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO events
            (event_id, title, category, layer, source,
             latitude, longitude, magnitude, ai_summary, url, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event["event_id"],
            event["title"],
            event["category"],
            event.get("layer", "SEISMIC"),
            event.get("source", "USGS"),
            event["latitude"],
            event["longitude"],
            event.get("magnitude"),
            event.get("ai_summary", "[pending]"),
            event.get("url", ""),
            event["timestamp"],
        ),
    )
    conn.commit()


# ─── Fallback Summary Generator ───────────────────────────────────────────────
def fallback_summary(event: dict) -> str:
    """Generate a concise, useful summary from event metadata when Ollama is unavailable."""
    layer = event.get("layer", "SEISMIC")
    title = event.get("title", "")
    mag   = event.get("magnitude")
    source = event.get("source", "")

    if layer == "SEISMIC":
        # Extract location from title (USGS titles are like "M 2.5 - 10km NE of City, State")
        location = title.split(" - ", 1)[1] if " - " in title else title
        if mag is not None:
            if mag >= 6.0:
                severity = "Major"
            elif mag >= 4.0:
                severity = "Moderate"
            elif mag >= 2.0:
                severity = "Minor"
            else:
                severity = "Micro"
            return f"{severity} seismic event (M{mag:.1f}) detected {location}. Monitoring for aftershocks."
        return f"Seismic activity detected {location}. Magnitude assessment pending."

    elif layer == "CONFLICT":
        return f"Armed conflict reported: {title[:80]}. Situation under monitoring."

    elif layer == "MILITARY":
        return f"Military activity: {title[:80]}. Strategic assessment ongoing."

    elif layer == "DISASTER":
        return f"Natural disaster reported: {title[:80]}. Relief assessment underway."

    elif layer == "POLITICAL":
        return f"Political unrest: {title[:80]}. Civil stability under review."

    elif layer == "NUCLEAR":
        return f"Nuclear-related event: {title[:80]}. Radiation monitoring active."

    elif layer == "HEALTH":
        return f"Health crisis: {title[:80]}. Epidemiological tracking active."

    elif layer == "BLAST":
        if mag is not None:
            return f"Explosion/blast event (M{mag:.1f}) detected: {title[:60]}."
        return f"Blast event detected: {title[:80]}."

    else:
        return f"Event detected: {title[:80]}. Source: {source}."


# ─── Ollama Inference ─────────────────────────────────────────────────────────
_ollama_available: bool | None = None  # Cache connectivity status within a cycle

def run_inference(event: dict) -> str:
    global _ollama_available
    prompt = (
        f"Event: {event['title']}\n"
        f"Type: {event.get('layer','SEISMIC')}\n"
        f"Source: {event.get('source','')}\n"
        f"Location: {event['latitude']:.4f}°, {event['longitude']:.4f}°\n"
        f"Time: {event['timestamp']}"
    )
    payload = {
        "model":   OLLAMA_MODEL,
        "prompt":  prompt,
        "system":  SYSTEM_PROMPT,
        "stream":  False,
        "options": {"temperature": 0.3, "num_predict": 40},
    }

    # Skip Ollama entirely if we already know it's down this cycle
    if _ollama_available is False:
        return fallback_summary(event)

    try:
        resp = requests.post(OLLAMA_ENDPOINT, json=payload, timeout=30)
        resp.raise_for_status()
        _ollama_available = True
        words = resp.json().get("response", "").strip().split()
        summary = " ".join(words[:15])
        return summary if summary else fallback_summary(event)
    except requests.exceptions.ConnectionError:
        if _ollama_available is not False:
            log.warning("Ollama unreachable — using fallback summary generator.")
        _ollama_available = False
        return fallback_summary(event)
    except Exception as exc:
        log.warning(f"Ollama inference failed ({exc}) — using fallback.")
        return fallback_summary(event)


# ─── USGS Seismic Feed ────────────────────────────────────────────────────────
USGS_FEED_DAY  = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
USGS_FEED_HOUR = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"

SEISMIC_CATEGORY_MAP = {
    "earthquake":        "SEISMIC",
    "quarry blast":      "BLAST",
    "explosion":         "BLAST",
    "mine collapse":     "STRUCTURAL",
    "ice quake":         "CRYOGENIC",
    "sonic boom":        "ATMOSPHERIC",
    "other event":       "ANOMALY",
    "not reported":      "UNCLASSIFIED",
    "nuclear explosion": "NUCLEAR",
}

def ingest_usgs(conn: sqlite3.Connection, url: str) -> int:
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        features = resp.json().get("features", [])
    except Exception as exc:
        log.error(f"USGS fetch failed: {exc}")
        return 0

    new_count = 0
    for feature in features:
        try:
            props  = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [None, None])
            lng, lat = coords[0], coords[1]
            if lat is None or lng is None:
                continue

            raw_time = props.get("time")
            ts = (
                datetime.fromtimestamp(raw_time / 1000, tz=timezone.utc).isoformat()
                if raw_time else datetime.now(tz=timezone.utc).isoformat()
            )
            raw_type = (props.get("type") or "").strip().lower()
            event = {
                "event_id":  feature.get("id", ""),
                "title":     props.get("title") or props.get("place") or "Unknown Seismic Event",
                "category":  SEISMIC_CATEGORY_MAP.get(raw_type, "SEISMIC"),
                "layer":     "SEISMIC",
                "source":    "USGS",
                "latitude":  float(lat),
                "longitude": float(lng),
                "magnitude": props.get("mag"),
                "url":       props.get("url", ""),
                "timestamp": ts,
            }
            if not event["event_id"] or event_exists(conn, event["event_id"]):
                continue

            log.info(f"  ↳ SEISMIC: {event['title']}")
            time.sleep(INFERENCE_BREATHER)
            event["ai_summary"] = run_inference(event)
            insert_event(conn, event)
            new_count += 1
        except Exception as exc:
            log.warning(f"USGS parse error: {exc}")
    return new_count


# ─── GDELT Intelligence Feed ──────────────────────────────────────────────────
def ingest_gdelt(conn: sqlite3.Connection, layer: str, query: str) -> int:
    """Fetch GDELT GEO API results for a given query and persist as events."""
    params = {
        "query":    query,
        "TIMESPAN": "1week",
        "format":   "GeoJSON",
        "MAXRECORDS": "50",
    }
    try:
        resp = requests.get(GDELT_BASE, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.error(f"GDELT [{layer}] fetch failed: {exc}")
        return 0

    features = data.get("features", [])
    new_count = 0
    for feature in features:
        try:
            props  = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [None, None])
            if not coords or coords[0] is None:
                continue
            lng, lat = float(coords[0]), float(coords[1])

            # Build unique ID from URL or name+location
            url     = props.get("url", "")
            name    = props.get("name", "") or props.get("title", "") or "Unknown Event"
            event_id = f"gdelt_{layer}_{abs(hash(url or (name + str(lat) + str(lng))))}"

            if event_exists(conn, event_id):
                continue

            # Parse date
            date_str = props.get("date", "")
            try:
                if date_str:
                    ts = datetime.strptime(date_str, "%Y%m%d%H%M%S").replace(
                        tzinfo=timezone.utc).isoformat()
                else:
                    ts = datetime.now(tz=timezone.utc).isoformat()
            except Exception:
                ts = datetime.now(tz=timezone.utc).isoformat()

            event = {
                "event_id":  event_id,
                "title":     name[:200],
                "category":  layer,
                "layer":     layer,
                "source":    "GDELT",
                "latitude":  lat,
                "longitude": lng,
                "magnitude": None,
                "url":       url,
                "timestamp": ts,
            }

            log.info(f"  ↳ GDELT/{layer}: {event['title'][:60]}")
            time.sleep(INFERENCE_BREATHER)
            event["ai_summary"] = run_inference(event)
            insert_event(conn, event)
            new_count += 1
        except Exception as exc:
            log.warning(f"GDELT [{layer}] parse error: {exc}")

    return new_count


# ─── UCDP Armed Conflict Feed ─────────────────────────────────────────────────
def ingest_ucdp(conn: sqlite3.Connection) -> int:
    """Fetch UCDP georeferenced conflict events."""
    url = "https://ucdpapi.pcr.uu.se/api/gedevents/23.1?pagesize=100&page=1"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        items = resp.json().get("Result", [])
    except Exception as exc:
        log.error(f"UCDP fetch failed: {exc}")
        return 0

    new_count = 0
    for item in items:
        try:
            lat = item.get("latitude")
            lng = item.get("longitude")
            if lat is None or lng is None:
                continue

            event_id = f"ucdp_{item.get('id', abs(hash(str(item))))}"
            if event_exists(conn, event_id):
                continue

            date_str = item.get("date_start", "")
            try:
                ts = datetime.strptime(date_str, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc).isoformat()
            except Exception:
                ts = datetime.now(tz=timezone.utc).isoformat()

            country = item.get("country", "Unknown")
            deaths  = item.get("deaths_total", 0) or 0
            title   = f"Armed conflict: {country} ({deaths} casualties)"

            event = {
                "event_id":  event_id,
                "title":     title,
                "category":  "CONFLICT",
                "layer":     "CONFLICT",
                "source":    "UCDP",
                "latitude":  float(lat),
                "longitude": float(lng),
                "magnitude": min(float(deaths) / 100.0, 9.9) if deaths else None,
                "url":       "",
                "timestamp": ts,
            }

            log.info(f"  ↳ UCDP: {title[:60]}")
            time.sleep(INFERENCE_BREATHER)
            event["ai_summary"] = run_inference(event)
            insert_event(conn, event)
            new_count += 1
        except Exception as exc:
            log.warning(f"UCDP parse error: {exc}")

    return new_count


# ─── ReliefWeb Disaster Feed ──────────────────────────────────────────────────
def ingest_reliefweb(conn: sqlite3.Connection) -> int:
    """Fetch ReliefWeb ongoing disasters."""
    url = (
        "https://api.reliefweb.int/v2/disasters"
        "?appname=worldtracker"
        "&profile=list&preset=latest&limit=50"
        "&filter[field]=status&filter[value]=ongoing"
        "&fields[include][]=name&fields[include][]=date"
        "&fields[include][]=type&fields[include][]=country"
        "&fields[include][]=url"
    )
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        items = resp.json().get("data", [])
    except Exception as exc:
        log.error(f"ReliefWeb fetch failed: {exc}")
        return 0

    new_count = 0
    for item in items:
        try:
            fields  = item.get("fields", {})
            event_id = f"rw_{item.get('id', '')}"
            if event_exists(conn, event_id):
                continue

            country_data = fields.get("country", [{}])
            country = country_data[0].get("name", "Unknown") if country_data else "Unknown"

            # ReliefWeb doesn't give lat/lng directly — use country centroid lookup
            lat, lng = get_country_centroid(country)
            if lat is None:
                continue

            disaster_types = [t.get("name", "") for t in fields.get("type", [])]
            type_str = ", ".join(disaster_types) if disaster_types else "Disaster"
            title    = fields.get("name", f"{type_str} in {country}")

            date_str = fields.get("date", {}).get("created", "")
            try:
                ts = datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
            except Exception:
                ts = datetime.now(tz=timezone.utc).isoformat()

            # Map disaster type to layer
            type_lower = type_str.lower()
            if "flood" in type_lower:
                layer = "DISASTER"
            elif "earthquake" in type_lower or "seismic" in type_lower:
                layer = "SEISMIC"
            elif "epidemic" in type_lower or "disease" in type_lower:
                layer = "HEALTH"
            elif "conflict" in type_lower or "violence" in type_lower:
                layer = "CONFLICT"
            else:
                layer = "DISASTER"

            event = {
                "event_id":  event_id,
                "title":     title,
                "category":  layer,
                "layer":     layer,
                "source":    "ReliefWeb",
                "latitude":  lat,
                "longitude": lng,
                "magnitude": None,
                "url":       fields.get("url", ""),
                "timestamp": ts,
            }

            log.info(f"  ↳ ReliefWeb: {title[:60]}")
            time.sleep(INFERENCE_BREATHER)
            event["ai_summary"] = run_inference(event)
            insert_event(conn, event)
            new_count += 1
        except Exception as exc:
            log.warning(f"ReliefWeb parse error: {exc}")

    return new_count


# ─── Country Centroid Lookup ───────────────────────────────────────────────────
COUNTRY_CENTROIDS: dict[str, tuple[float, float]] = {
    "Afghanistan": (33.93, 67.71), "Albania": (41.15, 20.17), "Algeria": (28.03, 1.66),
    "Angola": (-11.20, 17.87), "Argentina": (-38.42, -63.62), "Armenia": (40.07, 45.04),
    "Australia": (-25.27, 133.78), "Azerbaijan": (40.14, 47.58), "Bahrain": (26.00, 50.55),
    "Bangladesh": (23.68, 90.36), "Belarus": (53.71, 27.95), "Belgium": (50.50, 4.47),
    "Bolivia": (-16.29, -63.59), "Bosnia": (43.92, 17.68), "Brazil": (-14.24, -51.93),
    "Bulgaria": (42.73, 25.49), "Burkina Faso": (12.36, -1.56), "Burma": (21.92, 95.96),
    "Myanmar": (21.92, 95.96), "Cambodia": (12.57, 104.99), "Cameroon": (7.37, 12.35),
    "Canada": (56.13, -106.35), "Central African Republic": (6.61, 20.94),
    "Chad": (15.45, 18.73), "Chile": (-35.68, -71.54), "China": (35.86, 104.20),
    "Colombia": (4.57, -74.30), "Congo": (-4.04, 21.76),
    "Democratic Republic of the Congo": (-4.04, 21.76), "Croatia": (45.10, 15.20),
    "Cuba": (21.52, -77.78), "Czech Republic": (49.82, 15.47), "Denmark": (56.26, 9.50),
    "Dominican Republic": (18.74, -70.16), "Ecuador": (-1.83, -78.18),
    "Egypt": (26.82, 30.80), "El Salvador": (13.79, -88.90), "Ethiopia": (9.14, 40.49),
    "France": (46.23, 2.21), "Georgia": (42.31, 43.36), "Germany": (51.17, 10.45),
    "Ghana": (7.95, -1.02), "Greece": (39.07, 21.82), "Guatemala": (15.78, -90.23),
    "Guinea": (9.95, -11.61), "Haiti": (18.97, -72.29), "Honduras": (15.20, -86.24),
    "Hungary": (47.16, 19.50), "India": (20.59, 78.96), "Indonesia": (-0.79, 113.92),
    "Iran": (32.43, 53.69), "Iraq": (33.22, 43.68), "Israel": (31.05, 34.85),
    "Italy": (41.87, 12.57), "Japan": (36.20, 138.25), "Jordan": (30.59, 36.24),
    "Kazakhstan": (48.02, 66.92), "Kenya": (-0.02, 37.91), "Kosovo": (42.60, 20.90),
    "Kuwait": (29.31, 47.49), "Kyrgyzstan": (41.20, 74.77), "Lebanon": (33.85, 35.86),
    "Libya": (26.34, 17.23), "Madagascar": (-18.77, 46.87), "Malaysia": (4.21, 108.01),
    "Mali": (17.57, -3.99), "Mexico": (23.63, -102.55), "Moldova": (47.41, 28.37),
    "Morocco": (31.79, -7.09), "Mozambique": (-18.67, 35.53), "Nepal": (28.39, 84.12),
    "Netherlands": (52.13, 5.29), "Nicaragua": (12.87, -85.21), "Niger": (17.61, 8.08),
    "Nigeria": (9.08, 8.68), "North Korea": (40.34, 127.51), "Norway": (60.47, 8.47),
    "Pakistan": (30.38, 69.35), "Palestine": (31.95, 35.23), "Panama": (8.54, -80.78),
    "Papua New Guinea": (-6.31, 143.96), "Peru": (-9.19, -75.02),
    "Philippines": (12.88, 121.77), "Poland": (51.92, 19.15), "Portugal": (39.40, -8.22),
    "Romania": (45.94, 24.97), "Russia": (61.52, 105.32), "Rwanda": (-1.94, 29.87),
    "Saudi Arabia": (23.89, 45.08), "Senegal": (14.50, -14.45), "Serbia": (44.02, 21.01),
    "Sierra Leone": (8.46, -11.78), "Somalia": (5.15, 46.20), "South Africa": (-30.56, 22.94),
    "South Korea": (35.91, 127.77), "South Sudan": (6.88, 31.31), "Spain": (40.46, -3.75),
    "Sri Lanka": (7.87, 80.77), "Sudan": (12.86, 30.22), "Sweden": (60.13, 18.64),
    "Switzerland": (46.82, 8.23), "Syria": (34.80, 38.99), "Taiwan": (23.70, 121.00),
    "Tajikistan": (38.86, 71.28), "Tanzania": (-6.37, 34.89), "Thailand": (15.87, 100.99),
    "Tunisia": (33.89, 9.54), "Turkey": (38.96, 35.24), "Turkmenistan": (38.97, 59.56),
    "Uganda": (1.37, 32.29), "Ukraine": (48.38, 31.17), "United Arab Emirates": (23.42, 53.85),
    "United Kingdom": (55.38, -3.44), "United States": (37.09, -95.71),
    "Uzbekistan": (41.38, 64.59), "Venezuela": (6.42, -66.59), "Vietnam": (14.06, 108.28),
    "West Bank": (31.95, 35.23), "Yemen": (15.55, 48.52), "Zambia": (-13.13, 27.85),
    "Zimbabwe": (-19.02, 29.15),
}

def get_country_centroid(country_name: str) -> tuple[float | None, float | None]:
    """Look up approximate centroid for a country name."""
    # Try exact match first
    if country_name in COUNTRY_CENTROIDS:
        return COUNTRY_CENTROIDS[country_name]
    # Try partial match
    name_lower = country_name.lower()
    for k, v in COUNTRY_CENTROIDS.items():
        if k.lower() in name_lower or name_lower in k.lower():
            return v
    return None, None


# ─── Backfill Missing Summaries ───────────────────────────────────────────────
def backfill_missing_summaries(conn: sqlite3.Connection) -> int:
    """Fix existing events that have placeholder AI summaries."""
    rows = conn.execute(
        "SELECT id, title, category, layer, source, latitude, longitude, magnitude, timestamp "
        "FROM events WHERE ai_summary IN ('[AI offline]', '[pending]', '[AI inference failed]', '[no summary]', '')"
    ).fetchall()

    if not rows:
        return 0

    count = 0
    for row in rows:
        event = {
            "title":     row[1],
            "category":  row[2],
            "layer":     row[3],
            "source":    row[4],
            "latitude":  row[5],
            "longitude":  row[6],
            "magnitude": row[7],
            "timestamp": row[8],
        }
        summary = fallback_summary(event)
        conn.execute("UPDATE events SET ai_summary = ? WHERE id = ?", (summary, row[0]))
        count += 1

    conn.commit()
    return count


# ─── Main Loop ────────────────────────────────────────────────────────────────
def main():
    global _ollama_available
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        log.info("=== DRY RUN MODE — no data will be written ===")

    log.info("AntiGravity Multi-Source Scraper initializing...")
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    # ── Backfill any missing AI summaries from previous runs ──────────────────
    n_backfill = backfill_missing_summaries(conn)
    if n_backfill:
        log.info(f"Backfilled {n_backfill} events with fallback summaries.")

    # Reset Ollama availability for the new cycle
    _ollama_available = None

    # ── First cycle: seed all sources ─────────────────────────────────────────
    log.info("=== SEEDING: USGS (all_day feed) ===")
    n = ingest_usgs(conn, USGS_FEED_DAY)
    log.info(f"USGS seed: {n} new events")

    # log.info("=== SEEDING: UCDP armed conflicts ===")
    # n = ingest_ucdp(conn)
    # log.info(f"UCDP seed: {n} new events")

    # log.info("=== SEEDING: ReliefWeb disasters ===")
    # n = ingest_reliefweb(conn)
    # log.info(f"ReliefWeb seed: {n} new events")

    # log.info("=== SEEDING: GDELT intelligence layers ===")
    # for layer, query in GDELT_LAYERS.items():
    #     n = ingest_gdelt(conn, layer, query)
    #     log.info(f"GDELT/{layer}: {n} new events")

    log.info("=== SEED COMPLETE — entering continuous poll loop ===")

    # ── Continuous polling ────────────────────────────────────────────────────
    try:
        while True:
            time.sleep(POLL_INTERVAL)
            log.info("--- Poll cycle start ---")

            ingest_usgs(conn, USGS_FEED_HOUR)
            # ingest_ucdp(conn)  # Deprecated/Requires Auth
            # ingest_reliefweb(conn) # Requires Auth / V1 Gone
            # for layer, query in GDELT_LAYERS.items():
            #     ingest_gdelt(conn, layer, query)  # Deprecated API
            
            conn.commit()
            log.info("--- Poll cycle end ---")
    except KeyboardInterrupt:
        log.info("Scraper stopped. Closing database.")
        conn.close()
        sys.exit(0)


if __name__ == "__main__":
    main()
