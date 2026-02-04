# Meshtastic SDR — Web UI Dashboard

Single-page web dashboard that provides a real-time view of your Meshtastic mesh network by reading from the existing `mesh.db` SQLite database.

## Features

### Main Panels (2x2 Grid)

- **Watch List** — pin nodes you want to monitor closely; shows node info, latest position, and recent traffic for each watched node. Managed via star icons in the Node Directory or map popups. Persisted in browser localStorage.
- **Node Map** — Leaflet.js map with switchable tile themes (Dark, Light, Satellite, Topo). Nodes with known positions appear as circle markers with popups showing name, coordinates, altitude, satellite count, precision, and star toggle. Clickable coordinate links in the Node Directory and Traffic Feed pan the map to that location.
- **Node Directory** — sortable, filterable table of all discovered nodes. Columns: star toggle, node ID (with pin icon if position known), name, hardware model, first seen, last seen. Each row is clickable to expand an inline telemetry detail view showing device metrics, environment data, power metrics, air quality, local stats, and recent traffic. Includes a 5-state status indicator dot per node.
- **Traffic Feed** — live packet log with filters by message type and node ID/name. All columns are sortable. Shows encryption lock icons (public vs private channel), message type badges, and pin icons for position packets.

### Collapsible Stats Sidebar

Toggle via the hamburger button in the header. Contains:

- **Stats cards** — total nodes, total packets, 24h packet count
- **Packets by type** — breakdown of all observed message types with counts
- **RF Overview** — all-time and 24h tallies of total RF packets, decrypted/undecrypted ratio, public vs private channel counts (requires `packets_raw` table)
- **Channel Utilization** — per-node channel utilization percentage with bar charts, sourced from device telemetry
- **Hourly Traffic (24h)** — stacked bar chart showing decrypted vs undecrypted packets per hour
- **Packet Details** — hop limit distribution, packet size stats (avg/min/max), mesh rebroadcast detection (same packet_id heard from multiple relay nodes), MQTT count
- **Most Active Nodes (24h)** — top 20 nodes ranked by packet count with per-hour sparkline activity charts
- **Position Update Frequency** — nodes ranked by position update count with average interval, plus Meshtastic broadcast interval scaling display (adjusted when mesh exceeds 40 online nodes)

### Additional Features

- **Auto-refresh** — all panels poll the API every 10 seconds
- **Responsive** — 4-panel grid collapses to single column below 1024px
- **Hardware model lookup** — numeric HW model IDs are resolved to human-readable names (130+ models)
- **Encryption indicators** — lock icons distinguish public channel (default key, open lock) from private channel (closed lock) packets
- **Unnamed node display** — nodes without a long/short name show their hex ID with an "(unresolved)" label; nodes that have never transmitted directly (only seen as destinations) show "(not heard from)" instead
- **Broadcast interval scaling** — when 40+ nodes are online in a 2h window, the sidebar shows scaled Position, Telemetry, and NodeInfo intervals using the Meshtastic formula: `ScaledInterval = Interval * (1.0 + ((OnlineNodes - 40) * 0.075))`

## Node Status Indicators

Each node in the directory has a colored status dot based on its recent activity:

| Status | Color | Dot | Criteria |
|--------|-------|-----|----------|
| **Active** | Green | Glowing | Heard from within 2 hours |
| **Quiet** | Blue | Solid | NodeInfo received within 3h, but no other traffic in the last 2h |
| **Hiding** | Orange | Glowing | Active (traffic within 2h) but NodeInfo is stale (>3h) — has sent NodeInfo before |
| **Dormant** | Purple | Dim | Last traffic was 2-4 hours ago, NodeInfo stale or never sent |
| **Offline** | Grey | Dim | Not heard from in over 4 hours, or never heard from directly |

### Edge Cases

- A node with **no NodeInfo ever sent** cannot be "Quiet" or "Hiding" — it will be Active, Dormant, or Offline based solely on traffic timing.
- A **destination-only node** (never transmitted, only seen as a destination in another node's packet) is always Offline, shows "(not heard from)" instead of "(unresolved)", and has an empty First Seen column.
- Hover over any status dot to see a detailed tooltip explaining the node's timing.

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
| `GET /api/nodes` | All nodes with status enrichment (last_activity, last_nodeinfo, online_nodes) |
| `GET /api/traffic` | Recent traffic with optional filters |
| `GET /api/positions` | Latest position per node, excludes 0,0 coords; includes precision, altitude, sats |
| `GET /api/stats` | Aggregate counts: total nodes, total packets, 24h packets, breakdown by type |
| `GET /api/watchlist?nodes=id1,id2` | Node info + last 5 traffic entries + latest position for specified nodes |
| `GET /api/node_telemetry?node=id` | Latest telemetry by sub-type (device, environment, power, air_quality, local_stats) |
| `GET /api/metrics` | RF totals, hourly chart data, channel utilization, hop distribution, packet sizes, rebroadcasts, MQTT count |
| `GET /api/metrics/activity` | Top 20 active nodes with hourly breakdown, position update frequency |

### Traffic Filters

- `limit` — max rows returned (default 50, max 500)
- `msg_type` — exact match on message type (e.g. `POSITION_APP`, `TEXT_MESSAGE_APP`)
- `node` — substring match against source/dest ID or name

## Backend Details

- **Read-only** SQLite connection using `?mode=ro` URI — the dashboard never writes to the database
- `check_same_thread=False` allows Flask's threaded request handling to share the connection
- `busy_timeout=3000` handles WAL contention if the listener is writing concurrently
- Position data is extracted from the `traffic` table where `msg_type = 'POSITION_APP'`, using a subquery to get only the latest position per node
- RF-level metrics (hop counts, packet sizes, rebroadcasts) come from the `packets_raw` table which logs every received RF packet including undecrypted ones
- The `public_key` field is excluded from API responses
- Telemetry data is parsed into structured JSON by the listener (device metrics, environment, power, air quality, local stats, health, host metrics)

## File Structure

```
webui/
├── app.py                  # Flask application and API routes
├── README.md               # This file
├── templates/
│   └── index.html          # Dashboard HTML (single page)
└── static/
    ├── style.css           # Dark terminal theme with sidebar, status dots, telemetry styles
    └── dashboard.js        # Client-side polling, DOM updates, map, sorting, watch list, telemetry
```
