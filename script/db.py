import os
import sqlite3
from datetime import datetime, timezone

_conn = None

def init_db(debug=False):
    global _conn
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mesh.db")

    if debug:
        print(f"[DEBUG] Opening database: {db_path}")

    _conn = sqlite3.connect(db_path, timeout=5)
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.execute("PRAGMA busy_timeout=5000")

    _conn.executescript("""
        CREATE TABLE IF NOT EXISTS nodes (
            node_id     TEXT PRIMARY KEY,
            long_name   TEXT,
            short_name  TEXT,
            hw_model    INTEGER,
            role        INTEGER,
            public_key  BLOB,
            first_seen  TEXT NOT NULL,
            last_seen   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS traffic (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    TEXT NOT NULL,
            source_id    TEXT,
            source_name  TEXT,
            dest_id      TEXT,
            dest_name    TEXT,
            packet_id    TEXT,
            channel_hash TEXT,
            channel_name TEXT,
            port_num     INTEGER,
            msg_type     TEXT NOT NULL,
            data         TEXT,
            key_used     TEXT,
            via_mqtt     INTEGER DEFAULT 0,
            hop_start    INTEGER,
            hop_limit    INTEGER
        );

        CREATE TABLE IF NOT EXISTS packets_raw (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    TEXT NOT NULL,
            source_id    TEXT,
            dest_id      TEXT,
            packet_id    TEXT,
            channel_hash TEXT,
            flags        TEXT,
            hop_limit    INTEGER,
            hop_start    INTEGER,
            want_ack     INTEGER,
            via_mqtt     INTEGER,
            packet_size  INTEGER,
            decrypted    INTEGER NOT NULL DEFAULT 0,
            key_used     TEXT
        );
    """)

    # Auto-migrate existing databases: add columns if missing
    _migrations = [
        ("traffic", "via_mqtt", "ALTER TABLE traffic ADD COLUMN via_mqtt INTEGER DEFAULT 0"),
        ("traffic", "hop_start", "ALTER TABLE traffic ADD COLUMN hop_start INTEGER"),
        ("traffic", "hop_limit", "ALTER TABLE traffic ADD COLUMN hop_limit INTEGER"),
        ("packets_raw", "hop_start", "ALTER TABLE packets_raw ADD COLUMN hop_start INTEGER"),
    ]
    for table, column, ddl in _migrations:
        cols = [row[1] for row in _conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in cols:
            if debug:
                print(f"[DEBUG] Migrating: {ddl}")
            _conn.execute(ddl)

    _conn.commit()


def upsert_node(node_id, long_name=None, short_name=None, hw_model=None, role=None, public_key=None, timestamp=None):
    if _conn is None:
        return
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()
    else:
        timestamp = str(timestamp)

    pk_blob = None
    if public_key:
        if isinstance(public_key, str):
            pk_blob = bytes.fromhex(public_key)
        else:
            pk_blob = public_key

    _conn.execute("""
        INSERT INTO nodes (node_id, long_name, short_name, hw_model, role, public_key, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            long_name  = COALESCE(excluded.long_name,  nodes.long_name),
            short_name = COALESCE(excluded.short_name, nodes.short_name),
            hw_model   = COALESCE(excluded.hw_model,   nodes.hw_model),
            role       = COALESCE(excluded.role,        nodes.role),
            public_key = COALESCE(excluded.public_key,  nodes.public_key),
            last_seen  = excluded.last_seen
    """, (node_id, long_name, short_name, hw_model, role, pk_blob, timestamp, timestamp))
    _conn.commit()

def get_node_name(node_id):
    if _conn is None:
        return (None, None)
    row = _conn.execute(
        "SELECT long_name, short_name FROM nodes WHERE node_id = ?", (node_id,)
    ).fetchone()
    if row:
        return row
    return (None, None)

def resolve_name(node_id):
    if node_id is None:
        return None
    if node_id == "ffffffff":
        return "broadcast"
    long_name, short_name = get_node_name(node_id)
    if long_name and short_name:
        return f"{long_name} ({short_name})"
    if long_name:
        return long_name
    if short_name:
        return short_name
    return node_id

def ensure_node(node_id, timestamp=None):
    """Create a minimal nodes row if this node_id has never been seen."""
    if _conn is None or not node_id or node_id == "ffffffff":
        return
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()
    else:
        timestamp = str(timestamp)
    _conn.execute("""
        INSERT INTO nodes (node_id, first_seen, last_seen)
        VALUES (?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            last_seen = excluded.last_seen
    """, (node_id, timestamp, timestamp))


def log_traffic(timestamp, source_id, dest_id, packet_id=None, channel_hash=None,
                channel_name=None, port_num=None, msg_type="UNKNOWN", data=None, key_used=None,
                via_mqtt=False, hop_start=None, hop_limit=None):
    if _conn is None:
        return
    import json as _json
    ensure_node(source_id, timestamp)
    ensure_node(dest_id, timestamp)
    source_name = resolve_name(source_id)
    dest_name = resolve_name(dest_id)

    data_str = None
    if data is not None:
        if isinstance(data, (dict, list)):
            data_str = _json.dumps(data)
        else:
            data_str = str(data)

    _conn.execute("""
        INSERT INTO traffic (timestamp, source_id, source_name, dest_id, dest_name,
                             packet_id, channel_hash, channel_name, port_num,
                             msg_type, data, key_used, via_mqtt, hop_start, hop_limit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(timestamp), source_id, source_name, dest_id, dest_name,
          packet_id, channel_hash, channel_name, port_num,
          msg_type, data_str, key_used,
          1 if via_mqtt else 0, hop_start, hop_limit))
    _conn.commit()

def log_raw_packet(timestamp, source_id, dest_id, packet_id=None,
                   channel_hash=None, flags=None, hop_limit=None,
                   hop_start=None, want_ack=None, via_mqtt=None,
                   packet_size=None, decrypted=False, key_used=None):
    if _conn is None:
        return
    _conn.execute("""
        INSERT INTO packets_raw (timestamp, source_id, dest_id, packet_id,
                                 channel_hash, flags, hop_limit, hop_start,
                                 want_ack, via_mqtt, packet_size, decrypted,
                                 key_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(timestamp), source_id, dest_id, packet_id,
          channel_hash, flags, hop_limit, hop_start,
          1 if want_ack else 0, 1 if via_mqtt else 0,
          packet_size, 1 if decrypted else 0, key_used))
    _conn.commit()


def close_db():
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
