"""
AntiGravity — Cross-Origin Transport Proxy (server.py)
Flask API gateway on port 3001 serving the SQLite vault to the WebGL frontend.
Supports multiple intelligence layers: SEISMIC, CONFLICT, DISASTER, WILDFIRE, MILITARY, etc.
"""

import sqlite3
from flask import Flask, jsonify, request
from flask_cors import CORS

# ─── Config ───────────────────────────────────────────────────────────────────
DB_PATH = "worldmonitor.db"
PORT    = 3001

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})


# ─── Database Helper ──────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """Heartbeat — lets the frontend know the server is alive."""
    try:
        conn = get_db()
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        conn.close()
        return jsonify({"status": "ok", "event_count": count})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/events", methods=["GET"])
def get_events():
    """
    Return telemetry events as a JSON array.
    Optional query params:
      ?layers=SEISMIC,CONFLICT   — filter by layer (comma-separated)
      ?hours=24                  — only events from last N hours
    """
    try:
        layers_param = request.args.get("layers", "")
        hours_param  = request.args.get("hours", "")

        conn = get_db()

        query = """
            SELECT id, title, category, layer, source,
                   latitude, longitude, magnitude,
                   ai_summary, url, timestamp
            FROM events
        """
        conditions = []
        params     = []

        if layers_param:
            layer_list = [l.strip().upper() for l in layers_param.split(",") if l.strip()]
            if layer_list:
                placeholders = ",".join("?" for _ in layer_list)
                conditions.append(f"layer IN ({placeholders})")
                params.extend(layer_list)

        if hours_param:
            try:
                h = int(hours_param)
                conditions.append(
                    "datetime(timestamp) >= datetime('now', ?)"
                )
                params.append(f"-{h} hours")
            except ValueError:
                pass

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC LIMIT 500"

        rows = conn.execute(query, params).fetchall()
        conn.close()

        events = [
            {
                "id":         row["id"],
                "title":      row["title"],
                "category":   row["category"],
                "layer":      row["layer"] if row["layer"] else row["category"],
                "source":     row["source"] if row["source"] else "USGS",
                "latitude":   row["latitude"],
                "longitude":  row["longitude"],
                "magnitude":  row["magnitude"],
                "ai_summary": row["ai_summary"] or "",
                "url":        row["url"] if row["url"] else "",
                "timestamp":  row["timestamp"],
            }
            for row in rows
        ]
        return jsonify(events)

    except sqlite3.OperationalError:
        return jsonify([])
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/layers", methods=["GET"])
def get_layers():
    """Return event counts grouped by layer."""
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT layer, COUNT(*) as cnt FROM events GROUP BY layer ORDER BY cnt DESC"
        ).fetchall()
        conn.close()
        return jsonify([{"layer": r["layer"], "count": r["cnt"]} for r in rows])
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[AntiGravity Server] Starting on http://0.0.0.0:{PORT}")
    print(f"[AntiGravity Server] Events endpoint: http://localhost:{PORT}/api/events")
    print(f"[AntiGravity Server] Layers endpoint: http://localhost:{PORT}/api/layers")
    print(f"[AntiGravity Server] Health endpoint:  http://localhost:{PORT}/api/health")
    app.run(host="0.0.0.0", port=PORT, debug=False)
