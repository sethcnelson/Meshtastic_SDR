# Meshtastic SDR — Web UI Dashboard

Single-page web dashboard that provides a real-time view of your Meshtastic mesh network by reading from the existing `mesh.db` SQLite database.

## Features

- **Stats cards** — total nodes, total packets, 24h packet count, packets by message type
- **Node directory** — scrollable table of all discovered nodes with hardware model, first/last seen timestamps
- **Traffic feed** — live packet log with filters by message type and node ID/name
- **Node map** — Leaflet.js map with dark CartoDB tiles showing latest node positions as circle markers
- **Auto-refresh** — all panels poll the API every 10 seconds
- **Responsive** — 4-panel grid collapses to single column below 1024px

## Requirements

- Python 3
- Flask (`pip install flask`)
- A running or previously-run Meshtastic SDR listener that has populated `mesh.db`

No other dependencies. Leaflet.js is loaded from CDN.

## Usage

```bash
pip install flask
cd webui
python3 app.py
```

Open http://localhost:5000 in a browser.

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `5000` | HTTP listen port |
| `--db` | `../mesh.db` | Path to SQLite database |

Both flags are optional. The default `--db` path resolves to `mesh.db` in the project root, which is where the listener writes it.

```bash
# Examples
python3 app.py --port 8080
python3 app.py --db /path/to/other/mesh.db
python3 app.py --port 8080 --db /path/to/other/mesh.db
```

## API Endpoints

All endpoints return JSON and are read-only.

| Route | Description |
|-------|-------------|
| `GET /api/nodes` | All nodes (excludes `public_key` for security) |
| `GET /api/traffic?limit=50&msg_type=X&node=X` | Recent traffic with optional filters (excludes `key_used`) |
| `GET /api/positions` | Latest position per node, filtered to exclude 0,0 GPS coords |
| `GET /api/stats` | Aggregate counts: total nodes, total packets, 24h packets, breakdown by type |

### Traffic Filters

- `limit` — max rows returned (default 50, max 500)
- `msg_type` — exact match on message type (e.g. `POSITION_APP`, `TEXT_MESSAGE_APP`)
- `node` — substring match against source/dest ID or name

## Backend Details

- **Read-only** SQLite connection using `?mode=ro` URI — the dashboard never writes to the database
- `check_same_thread=False` allows Flask's threaded request handling to share the connection
- `busy_timeout=3000` handles WAL contention if the listener is writing concurrently
- Position data is extracted from the `traffic` table where `msg_type = 'POSITION_APP'`, using a subquery to get only the latest position per node
- The `public_key` and `key_used` fields are excluded from API responses

## File Structure

```
webui/
├── app.py                  # Flask application and API routes
├── templates/
│   └── index.html          # Dashboard HTML (single page)
└── static/
    ├── style.css           # Dark terminal theme
    └── dashboard.js        # Client-side polling, DOM updates, map
```
