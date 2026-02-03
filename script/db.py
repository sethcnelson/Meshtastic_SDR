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
            key_used     TEXT
        );
    """)
    _conn.commit()

    # Migrate: replace stored raw keys with "public" or "private" labels
    _migrate_key_used()


# The default Meshtastic public key (AQ== expanded to full base64)
_DEFAULT_KEY = "1PG7OiApB1nwvP+rz05pAQ=="


def _migrate_key_used():
    """One-time migration: convert raw key strings in key_used to 'public' or 'private'."""
    # Check if any rows still have raw key data (not already migrated)
    row = _conn.execute(
        "SELECT COUNT(*) FROM traffic "
        "WHERE key_used IS NOT NULL AND key_used NOT IN ('public', 'private')"
    ).fetchone()
    if row[0] == 0:
        return

    # Mark default key traffic as public
    _conn.execute(
        "UPDATE traffic SET key_used = 'public' WHERE key_used = ?",
        (_DEFAULT_KEY,)
    )
    # Mark everything else that isn't already labeled as private
    _conn.execute(
        "UPDATE traffic SET key_used = 'private' "
        "WHERE key_used IS NOT NULL AND key_used NOT IN ('public', 'private')"
    )
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
                channel_name=None, port_num=None, msg_type="UNKNOWN", data=None, key_used=None):
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
                             msg_type, data, key_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(timestamp), source_id, source_name, dest_id, dest_name,
          packet_id, channel_hash, channel_name, port_num,
          msg_type, data_str, key_used))
    _conn.commit()

def close_db():
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
