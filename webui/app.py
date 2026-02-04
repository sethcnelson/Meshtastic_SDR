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

    # Enrich with last activity and last nodeinfo timestamps
    # Last non-NODEINFO traffic per node (any activity)
    activity_rows = db_conn.execute(
        "SELECT source_id, MAX(timestamp) AS last_activity "
        "FROM traffic "
        "GROUP BY source_id"
    ).fetchall()
    activity_map = {r["source_id"]: r["last_activity"] for r in activity_rows}

    # Last NODEINFO_APP per node
    nodeinfo_rows = db_conn.execute(
        "SELECT source_id, MAX(timestamp) AS last_nodeinfo "
        "FROM traffic WHERE msg_type = 'NODEINFO_APP' "
        "GROUP BY source_id"
    ).fetchall()
    nodeinfo_map = {r["source_id"]: r["last_nodeinfo"] for r in nodeinfo_rows}

    # Count online nodes (active in last 2h) for scaled interval calculation
    online_count = db_conn.execute(
        "SELECT COUNT(DISTINCT source_id) FROM traffic "
        "WHERE timestamp >= datetime('now', '-2 hours')"
    ).fetchone()[0]

    result = []
    for r in rows:
        node = dict(r)
        node["last_activity"] = activity_map.get(r["node_id"])
        node["last_nodeinfo"] = nodeinfo_map.get(r["node_id"])
        node["online_nodes"] = online_count
        result.append(node)

    return jsonify(result)


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
        f"       packet_id, channel_hash, channel_name, port_num, msg_type, data, key_used "
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

        entry = {
            "source_id": row["source_id"],
            "source_name": row["source_name"],
            "latitude": lat,
            "longitude": lng,
            "timestamp": row["timestamp"],
        }
        if "precision_bits" in data:
            entry["precision_bits"] = data["precision_bits"]
        if "altitude" in data:
            entry["altitude"] = data["altitude"]
        if "sats_in_view" in data:
            entry["sats_in_view"] = data["sats_in_view"]
        if "ground_speed" in data:
            entry["ground_speed"] = data["ground_speed"]
        positions.append(entry)

    return jsonify(positions)


@app.route("/api/watchlist")
def api_watchlist():
    nodes_param = request.args.get("nodes", "").strip()
    if not nodes_param:
        return jsonify([])

    node_ids = [n.strip() for n in nodes_param.split(",") if n.strip()]
    if not node_ids:
        return jsonify([])

    # Fetch node info
    placeholders = ",".join("?" * len(node_ids))
    node_rows = db_conn.execute(
        f"SELECT node_id, long_name, short_name, hw_model, role, "
        f"       first_seen, last_seen "
        f"FROM nodes WHERE node_id IN ({placeholders})",
        node_ids,
    ).fetchall()
    node_map = {r["node_id"]: dict(r) for r in node_rows}

    result = []
    for nid in node_ids:
        node_info = node_map.get(nid, {"node_id": nid})

        # Last 5 traffic entries involving this node
        traffic_rows = db_conn.execute(
            "SELECT id, timestamp, source_id, source_name, dest_id, dest_name, "
            "       packet_id, channel_hash, channel_name, port_num, msg_type, data, key_used "
            "FROM traffic "
            "WHERE source_id = ? OR dest_id = ? "
            "ORDER BY id DESC LIMIT 5",
            (nid, nid),
        ).fetchall()

        # Latest position
        pos_row = db_conn.execute(
            "SELECT data, timestamp FROM traffic "
            "WHERE source_id = ? AND msg_type = 'POSITION_APP' "
            "ORDER BY id DESC LIMIT 1",
            (nid,),
        ).fetchone()

        position = None
        if pos_row:
            try:
                data = json.loads(pos_row["data"]) if pos_row["data"] else {}
                lat = data.get("latitude", 0)
                lng = data.get("longitude", 0)
                if lat != 0 or lng != 0:
                    position = {
                        "latitude": lat,
                        "longitude": lng,
                        "timestamp": pos_row["timestamp"],
                    }
            except (json.JSONDecodeError, TypeError):
                pass

        result.append({
            "node": node_info,
            "traffic": [dict(r) for r in traffic_rows],
            "position": position,
        })

    return jsonify(result)


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


@app.route("/api/node_telemetry")
def api_node_telemetry():
    node_id = request.args.get("node", "").strip()
    if not node_id:
        return jsonify(None)

    # Fetch the latest telemetry entries by sub-type for this node
    rows = db_conn.execute(
        "SELECT data, timestamp FROM traffic "
        "WHERE source_id = ? AND msg_type = 'TELEMETRY_APP' "
        "ORDER BY id DESC LIMIT 20",
        (node_id,),
    ).fetchall()

    result = {"device": None, "environment": None, "power": None,
              "air_quality": None, "local_stats": None}

    for row in rows:
        try:
            data = json.loads(row["data"]) if row["data"] else {}
        except (json.JSONDecodeError, TypeError):
            continue

        ttype = data.get("telemetry_type")
        if ttype and ttype in result and result[ttype] is None:
            result[ttype] = {"data": data, "timestamp": row["timestamp"]}

        # Stop early if we have all types
        if all(v is not None for v in result.values()):
            break

    return jsonify(result)


def _safe_table_exists(table_name):
    """Check if a table exists in the database."""
    row = db_conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row[0] > 0


@app.route("/api/metrics")
def api_metrics():
    result = {}

    # ── Decryption tallies (from packets_raw if available) ────────────────
    has_raw = _safe_table_exists("packets_raw")

    if has_raw:
        totals = db_conn.execute(
            "SELECT "
            "  COUNT(*) AS total, "
            "  SUM(CASE WHEN decrypted = 1 THEN 1 ELSE 0 END) AS decrypted, "
            "  SUM(CASE WHEN decrypted = 0 THEN 1 ELSE 0 END) AS undecrypted, "
            "  SUM(CASE WHEN key_used = 'public' THEN 1 ELSE 0 END) AS public_ct, "
            "  SUM(CASE WHEN key_used = 'private' THEN 1 ELSE 0 END) AS private_ct "
            "FROM packets_raw"
        ).fetchone()
        result["rf_totals"] = {
            "total": totals["total"],
            "decrypted": totals["decrypted"],
            "undecrypted": totals["undecrypted"],
            "public": totals["public_ct"],
            "private": totals["private_ct"],
        }

        # 24h breakdown
        totals_24h = db_conn.execute(
            "SELECT "
            "  COUNT(*) AS total, "
            "  SUM(CASE WHEN decrypted = 1 THEN 1 ELSE 0 END) AS decrypted, "
            "  SUM(CASE WHEN decrypted = 0 THEN 1 ELSE 0 END) AS undecrypted, "
            "  SUM(CASE WHEN key_used = 'public' THEN 1 ELSE 0 END) AS public_ct, "
            "  SUM(CASE WHEN key_used = 'private' THEN 1 ELSE 0 END) AS private_ct "
            "FROM packets_raw WHERE timestamp >= datetime('now', '-1 day')"
        ).fetchone()
        result["rf_totals_24h"] = {
            "total": totals_24h["total"],
            "decrypted": totals_24h["decrypted"],
            "undecrypted": totals_24h["undecrypted"],
            "public": totals_24h["public_ct"],
            "private": totals_24h["private_ct"],
        }

        # Hourly packet counts (last 24h) for graphing
        hourly = db_conn.execute(
            "SELECT strftime('%Y-%m-%dT%H:00:00', timestamp) AS hour, "
            "  COUNT(*) AS total, "
            "  SUM(CASE WHEN decrypted = 1 THEN 1 ELSE 0 END) AS decrypted, "
            "  SUM(CASE WHEN decrypted = 0 THEN 1 ELSE 0 END) AS undecrypted "
            "FROM packets_raw "
            "WHERE timestamp >= datetime('now', '-1 day') "
            "GROUP BY hour ORDER BY hour"
        ).fetchall()
        result["hourly"] = [dict(r) for r in hourly]
    else:
        result["rf_totals"] = None
        result["rf_totals_24h"] = None
        result["hourly"] = []

    # ── Channel utilization (from decoded telemetry) ──────────────────────
    util_rows = db_conn.execute(
        "SELECT t.source_id, t.source_name, t.data, t.timestamp "
        "FROM traffic t "
        "INNER JOIN ( "
        "  SELECT source_id, MAX(id) AS max_id "
        "  FROM traffic "
        "  WHERE msg_type = 'TELEMETRY_APP' "
        "    AND data LIKE '%channel_utilization%' "
        "  GROUP BY source_id "
        ") latest ON t.id = latest.max_id"
    ).fetchall()

    channel_util = []
    for row in util_rows:
        try:
            data = json.loads(row["data"]) if row["data"] else {}
        except (json.JSONDecodeError, TypeError):
            continue
        cu = data.get("channel_utilization")
        if cu is not None:
            channel_util.append({
                "source_id": row["source_id"],
                "source_name": row["source_name"],
                "channel_utilization": cu,
                "air_util_tx": data.get("air_util_tx"),
                "timestamp": row["timestamp"],
            })
    result["channel_utilization"] = channel_util

    # ── Hop count distribution (from packets_raw) ──────────────────────────
    if has_raw:
        hop_rows = db_conn.execute(
            "SELECT hop_limit, COUNT(*) AS cnt FROM packets_raw "
            "WHERE hop_limit IS NOT NULL "
            "GROUP BY hop_limit ORDER BY hop_limit"
        ).fetchall()
        result["hop_distribution"] = [dict(r) for r in hop_rows]

        # Average packet size
        size_row = db_conn.execute(
            "SELECT AVG(packet_size) AS avg_size, MIN(packet_size) AS min_size, "
            "       MAX(packet_size) AS max_size "
            "FROM packets_raw WHERE packet_size > 0"
        ).fetchone()
        result["packet_sizes"] = {
            "avg": round(size_row["avg_size"], 1) if size_row["avg_size"] else 0,
            "min": size_row["min_size"] or 0,
            "max": size_row["max_size"] or 0,
        }

        # Duplicate packet detection (same packet_id seen multiple times)
        # These are mesh rebroadcasts — the same original packet relayed by different nodes
        dup_row = db_conn.execute(
            "SELECT COUNT(*) AS dup_ids, SUM(cnt) AS dup_total FROM ("
            "  SELECT packet_id, COUNT(*) AS cnt FROM packets_raw "
            "  WHERE packet_id IS NOT NULL "
            "  GROUP BY packet_id HAVING COUNT(*) > 1"
            ")"
        ).fetchone()
        unique_ids = db_conn.execute(
            "SELECT COUNT(DISTINCT packet_id) FROM packets_raw "
            "WHERE packet_id IS NOT NULL"
        ).fetchone()[0]
        total_raw = db_conn.execute("SELECT COUNT(*) FROM packets_raw").fetchone()[0]
        result["duplicates"] = {
            "rebroadcast_packet_ids": dup_row["dup_ids"] or 0,
            "rebroadcast_total_copies": dup_row["dup_total"] or 0,
            "unique_packet_ids": unique_ids or 0,
            "total_packets": total_raw,
        }

        # Via MQTT count
        mqtt_row = db_conn.execute(
            "SELECT SUM(CASE WHEN via_mqtt = 1 THEN 1 ELSE 0 END) AS mqtt_ct "
            "FROM packets_raw"
        ).fetchone()
        result["via_mqtt"] = mqtt_row["mqtt_ct"] or 0
    else:
        result["hop_distribution"] = []
        result["packet_sizes"] = None
        result["duplicates"] = None
        result["via_mqtt"] = 0

    return jsonify(result)


@app.route("/api/metrics/activity")
def api_metrics_activity():
    """Per-node activity patterns over the last 24 hours."""
    # Top 20 most active nodes in last 24h
    rows = db_conn.execute(
        "SELECT source_id, source_name, COUNT(*) AS pkt_count, "
        "       COUNT(DISTINCT msg_type) AS type_count "
        "FROM traffic "
        "WHERE timestamp >= datetime('now', '-1 day') "
        "GROUP BY source_id "
        "ORDER BY pkt_count DESC LIMIT 20"
    ).fetchall()

    nodes = []
    for r in rows:
        # Per-hour breakdown for this node
        hourly = db_conn.execute(
            "SELECT strftime('%H', timestamp) AS hour, COUNT(*) AS cnt "
            "FROM traffic "
            "WHERE source_id = ? AND timestamp >= datetime('now', '-1 day') "
            "GROUP BY hour ORDER BY hour",
            (r["source_id"],),
        ).fetchall()
        hourly_map = {h["hour"]: h["cnt"] for h in hourly}

        nodes.append({
            "source_id": r["source_id"],
            "source_name": r["source_name"],
            "pkt_count": r["pkt_count"],
            "type_count": r["type_count"],
            "hourly": hourly_map,
        })

    # Position update frequency — average interval between POSITION_APP per node
    pos_freq = db_conn.execute(
        "SELECT source_id, source_name, COUNT(*) AS pos_count, "
        "       MIN(timestamp) AS first_pos, MAX(timestamp) AS last_pos "
        "FROM traffic "
        "WHERE msg_type = 'POSITION_APP' AND timestamp >= datetime('now', '-1 day') "
        "GROUP BY source_id HAVING pos_count >= 2 "
        "ORDER BY pos_count DESC LIMIT 20"
    ).fetchall()

    pos_frequency = []
    for r in pos_freq:
        try:
            from datetime import datetime
            first = datetime.fromisoformat(r["first_pos"])
            last = datetime.fromisoformat(r["last_pos"])
            span = (last - first).total_seconds()
            avg_interval = span / (r["pos_count"] - 1) if r["pos_count"] > 1 else 0
        except Exception:
            avg_interval = 0

        pos_frequency.append({
            "source_id": r["source_id"],
            "source_name": r["source_name"],
            "pos_count": r["pos_count"],
            "avg_interval_secs": round(avg_interval),
        })

    return jsonify({
        "top_nodes": nodes,
        "position_frequency": pos_frequency,
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
