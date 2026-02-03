/* Meshtastic SDR Dashboard — Vanilla JS */
(function () {
    "use strict";

    // ── Hardware Model Lookup ────────────────────────────────────────────────
    var HW_MODELS = {
        0: "Unset", 1: "T-Lora V2", 2: "T-Lora V1", 3: "T-Lora V2 1.6",
        4: "T-Beam", 5: "Heltec V2.0", 6: "T-Beam V0.7", 7: "T-Echo",
        8: "T-Lora V1.1 (1.3\")", 9: "RAK4631", 10: "Heltec V2.1",
        11: "Heltec V1", 12: "Lily Go Pico", 25: "RAK11200",
        26: "Nano G1", 29: "Station G1", 30: "M5 Stack",
        32: "Heltec V3", 33: "Heltec WSL V3", 34: "Betafpv 2400 TX",
        35: "Betafpv 900 Nano TX", 36: "RPI Pico", 37: "Heltec Wireless Tracker",
        38: "Heltec Wireless Paper", 39: "T-Deck", 40: "T-Watch S3",
        41: "Picomputer S3", 42: "Heltec HT62", 43: "eByte ESP32-S3",
        44: "ESP32-S3 Pico", 45: "Chatter 2", 46: "Heltec Wireless Paper V1",
        47: "Heltec Wireless Tracker V1", 48: "Unphone",
        49: "T-Lora C6", 50: "Station G2", 51: "Heltec Capsule V3",
        52: "Heltec Vision Master T190", 53: "Heltec Vision Master E213",
        54: "Heltec Vision Master E290", 55: "Heltec Mesh Node",
        56: "Heltec Capsule Lite", 57: "Heltec Vision Master E290 V2",
        255: "Private HW"
    };

    // ── Msg type badge classes ───────────────────────────────────────────────
    var BADGE_CLASS = {
        TEXT_MESSAGE_APP: "badge-text",
        TEXT_MESSAGE_COMPRESSED_APP: "badge-text",
        POSITION_APP: "badge-position",
        TELEMETRY_APP: "badge-telemetry",
        NODEINFO_APP: "badge-nodeinfo",
        ROUTING_APP: "badge-routing"
    };

    // ── State ────────────────────────────────────────────────────────────────
    var map = null;
    var markers = {};
    var mapInitialized = false;
    var knownMsgTypes = new Set();
    var debounceTimer = null;

    // ── Init ─────────────────────────────────────────────────────────────────
    function init() {
        map = L.map("map", { zoomControl: true }).setView([39.8, -98.5], 4);
        L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
            subdomains: "abcd",
            maxZoom: 19
        }).addTo(map);

        document.getElementById("filter-type").addEventListener("change", function () {
            fetchTraffic();
        });

        document.getElementById("filter-node").addEventListener("input", function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(fetchTraffic, 300);
        });

        refresh();
        setInterval(refresh, 10000);
    }

    function refresh() {
        fetchStats();
        fetchNodes();
        fetchTraffic();
        fetchPositions();
        document.getElementById("last-update").textContent =
            "Updated " + new Date().toLocaleTimeString();
    }

    // ── Fetch helpers ────────────────────────────────────────────────────────
    function fetchJSON(url, callback) {
        fetch(url)
            .then(function (r) { return r.json(); })
            .then(callback)
            .catch(function (err) { console.error("Fetch error:", url, err); });
    }

    // ── Stats ────────────────────────────────────────────────────────────────
    function fetchStats() {
        fetchJSON("/api/stats", function (data) {
            document.getElementById("stat-nodes").textContent = data.total_nodes;
            document.getElementById("stat-packets").textContent = data.total_packets.toLocaleString();
            document.getElementById("stat-24h").textContent = data.packets_24h.toLocaleString();

            var list = document.getElementById("by-type-list");
            var types = data.by_type || {};
            var keys = Object.keys(types);

            if (keys.length === 0) {
                list.innerHTML = '<li class="muted">No data yet</li>';
                return;
            }

            list.innerHTML = keys.map(function (t) {
                return '<li><span class="badge ' + badgeClass(t) + '">' +
                    esc(t) + '</span><span>' + types[t].toLocaleString() + '</span></li>';
            }).join("");

            // Update filter dropdown with any new types
            keys.forEach(function (t) {
                if (!knownMsgTypes.has(t)) {
                    knownMsgTypes.add(t);
                    var opt = document.createElement("option");
                    opt.value = t;
                    opt.textContent = t;
                    document.getElementById("filter-type").appendChild(opt);
                }
            });
        });
    }

    // ── Nodes ────────────────────────────────────────────────────────────────
    function fetchNodes() {
        fetchJSON("/api/nodes", function (rows) {
            var tbody = document.querySelector("#nodes-table tbody");

            if (rows.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="muted">No data yet</td></tr>';
                return;
            }

            tbody.innerHTML = rows.map(function (n) {
                var name = n.long_name || n.short_name || "—";
                var hw = HW_MODELS[n.hw_model] || ("ID " + n.hw_model);
                return "<tr>" +
                    "<td>" + esc(n.node_id) + "</td>" +
                    "<td>" + esc(name) + "</td>" +
                    "<td>" + esc(hw) + "</td>" +
                    "<td>" + fmtTime(n.first_seen) + "</td>" +
                    "<td>" + fmtTime(n.last_seen) + "</td>" +
                    "</tr>";
            }).join("");
        });
    }

    // ── Traffic ──────────────────────────────────────────────────────────────
    function fetchTraffic() {
        var params = [];
        var msgType = document.getElementById("filter-type").value;
        var node = document.getElementById("filter-node").value.trim();
        if (msgType) params.push("msg_type=" + encodeURIComponent(msgType));
        if (node) params.push("node=" + encodeURIComponent(node));

        var url = "/api/traffic" + (params.length ? "?" + params.join("&") : "");
        fetchJSON(url, function (rows) {
            var tbody = document.querySelector("#traffic-table tbody");

            if (rows.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="muted">No data yet</td></tr>';
                return;
            }

            tbody.innerHTML = rows.map(function (r) {
                var src = r.source_name || r.source_id || "—";
                var dst = r.dest_name || r.dest_id || "—";
                var dataStr = truncate(r.data || "", 60);
                return "<tr>" +
                    "<td>" + fmtTime(r.timestamp) + "</td>" +
                    "<td>" + esc(src) + "</td>" +
                    "<td>" + esc(dst) + "</td>" +
                    '<td><span class="badge ' + badgeClass(r.msg_type) + '">' + esc(r.msg_type) + '</span></td>' +
                    "<td>" + esc(r.channel_name || "—") + "</td>" +
                    "<td>" + esc(dataStr) + "</td>" +
                    "</tr>";
            }).join("");
        });
    }

    // ── Positions / Map ──────────────────────────────────────────────────────
    function fetchPositions() {
        fetchJSON("/api/positions", function (rows) {
            if (rows.length === 0) return;

            var bounds = [];

            rows.forEach(function (p) {
                var latlng = [p.latitude, p.longitude];
                bounds.push(latlng);

                var label = p.source_name || p.source_id;
                var popup = "<b>" + esc(label) + "</b><br>" +
                    esc(p.source_id) + "<br>" +
                    p.latitude.toFixed(5) + ", " + p.longitude.toFixed(5) + "<br>" +
                    "<small>" + fmtTime(p.timestamp) + "</small>";

                if (markers[p.source_id]) {
                    markers[p.source_id].setLatLng(latlng).setPopupContent(popup);
                } else {
                    markers[p.source_id] = L.circleMarker(latlng, {
                        radius: 6,
                        color: "#58a6ff",
                        fillColor: "#58a6ff",
                        fillOpacity: 0.7,
                        weight: 1
                    }).addTo(map).bindPopup(popup);
                }
            });

            if (!mapInitialized && bounds.length > 0) {
                map.fitBounds(bounds, { padding: [30, 30], maxZoom: 14 });
                mapInitialized = true;
            }
        });
    }

    // ── Utilities ────────────────────────────────────────────────────────────
    function esc(s) {
        if (s == null) return "";
        var div = document.createElement("div");
        div.appendChild(document.createTextNode(String(s)));
        return div.innerHTML;
    }

    function fmtTime(iso) {
        if (!iso) return "—";
        try {
            var d = new Date(iso);
            return d.toLocaleString(undefined, {
                month: "short", day: "numeric",
                hour: "2-digit", minute: "2-digit", second: "2-digit"
            });
        } catch (e) {
            return esc(iso);
        }
    }

    function truncate(s, max) {
        return s.length > max ? s.slice(0, max) + "\u2026" : s;
    }

    function badgeClass(msgType) {
        return BADGE_CLASS[msgType] || "badge-other";
    }

    // ── Boot ─────────────────────────────────────────────────────────────────
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
