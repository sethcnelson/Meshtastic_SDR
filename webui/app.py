#!/usr/bin/env python3
"""Meshtastic SDR Web UI — read-only dashboard for mesh.db."""

import argparse
import json
import os
import sqlite3
import sys

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
db_conn = None


def get_db(db_path):
    """Open a read-only SQLite connection."""
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 3000")
    return conn


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/nodes")
def api_nodes():
    rows = db_conn.execute(
        "SELECT node_id, long_name, short_name, hw_model, role, "
        "       first_seen, last_seen "
        "FROM nodes ORDER BY last_seen DESC"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/traffic")
def api_traffic():
    limit = request.args.get("limit", "50")
    try:
        limit = min(int(limit), 500)
    except ValueError:
        limit = 50

    clauses = []
    params = []

    msg_type = request.args.get("msg_type")
    if msg_type:
        clauses.append("msg_type = ?")
        params.append(msg_type)

    node = request.args.get("node")
    if node:
        like = f"%{node}%"
        clauses.append(
            "(source_id LIKE ? OR source_name LIKE ? "
            "OR dest_id LIKE ? OR dest_name LIKE ?)"
        )
        params.extend([like, like, like, like])

    where = ""
    if clauses:
        where = "WHERE " + " AND ".join(clauses)

    query = (
        f"SELECT id, timestamp, source_id, source_name, dest_id, dest_name, "
        f"       packet_id, channel_hash, channel_name, port_num, msg_type, data "
        f"FROM traffic {where} ORDER BY id DESC LIMIT ?"
    )
    params.append(limit)

    rows = db_conn.execute(query, params).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/positions")
def api_positions():
    query = """
        SELECT t.source_id, t.source_name, t.data, t.timestamp
        FROM traffic t
        INNER JOIN (
            SELECT source_id, MAX(id) AS max_id
            FROM traffic
            WHERE msg_type = 'POSITION_APP'
            GROUP BY source_id
        ) latest ON t.id = latest.max_id
    """
    rows = db_conn.execute(query).fetchall()

    positions = []
    for row in rows:
        try:
            data = json.loads(row["data"]) if row["data"] else {}
        except (json.JSONDecodeError, TypeError):
            continue

        lat = data.get("latitude", 0)
        lng = data.get("longitude", 0)
        if lat == 0 and lng == 0:
            continue

        positions.append({
            "source_id": row["source_id"],
            "source_name": row["source_name"],
            "latitude": lat,
            "longitude": lng,
            "timestamp": row["timestamp"],
        })

    return jsonify(positions)


@app.route("/api/stats")
def api_stats():
    total_nodes = db_conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    total_packets = db_conn.execute("SELECT COUNT(*) FROM traffic").fetchone()[0]

    packets_24h = db_conn.execute(
        "SELECT COUNT(*) FROM traffic "
        "WHERE timestamp >= datetime('now', '-1 day')"
    ).fetchone()[0]

    type_rows = db_conn.execute(
        "SELECT msg_type, COUNT(*) AS cnt FROM traffic "
        "GROUP BY msg_type ORDER BY cnt DESC"
    ).fetchall()
    by_type = {r["msg_type"]: r["cnt"] for r in type_rows}

    return jsonify({
        "total_nodes": total_nodes,
        "total_packets": total_packets,
        "packets_24h": packets_24h,
        "by_type": by_type,
    })


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global db_conn

    default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mesh.db")
    default_db = os.path.normpath(default_db)

    parser = argparse.ArgumentParser(description="Meshtastic SDR Web Dashboard")
    parser.add_argument("--port", type=int, default=5000, help="HTTP port (default 5000)")
    parser.add_argument("--db", default=default_db, help=f"Path to mesh.db (default {default_db})")
    args = parser.parse_args()

    if not os.path.isfile(args.db):
        print(f"Error: database not found: {args.db}", file=sys.stderr)
        sys.exit(1)

    db_conn = get_db(args.db)
    print(f"[webui] Database: {args.db}")
    print(f"[webui] Starting on http://localhost:{args.port}")
    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
