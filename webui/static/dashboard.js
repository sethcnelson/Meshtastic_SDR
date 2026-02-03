/* Meshtastic SDR Dashboard — Vanilla JS */
(function () {
    "use strict";

    // ── Hardware Model Lookup ────────────────────────────────────────────────
    var HW_MODELS = {
        0: "Unset",
        1: "T-LoRa V2",
        2: "T-LoRa V1",
        3: "T-LoRa V2.1 1.6",
        4: "T-Beam",
        5: "Heltec V2.0",
        6: "T-Beam V0.7",
        7: "T-Echo",
        8: "T-LoRa V1 1.3",
        9: "RAK4631",
        10: "Heltec V2.1",
        11: "Heltec V1",
        12: "T-Beam S3 Core",
        13: "RAK11200",
        14: "Nano G1",
        15: "T-LoRa V2.1 1.8",
        16: "T-LoRa T3 S3",
        17: "Nano G1 Explorer",
        18: "Nano G2 Ultra",
        19: "LoRa Type",
        20: "WiPhone",
        21: "WIO WM1110",
        22: "RAK2560",
        23: "Heltec HRU 3601",
        24: "Heltec Wireless Bridge",
        25: "Station G1",
        26: "RAK11310",
        27: "SenseLora RP2040",
        28: "SenseLora S3",
        29: "CanaryOne",
        30: "RP2040 LoRa",
        31: "Station G2",
        32: "LoRa Relay V1",
        33: "T-Echo Plus",
        34: "PPR",
        35: "GenieBlocks",
        36: "nRF52 Unknown",
        37: "Portduino",
        38: "Android Sim",
        39: "DIY V1",
        40: "nRF52840 PCA10059",
        41: "DR Dev",
        42: "M5Stack",
        43: "Heltec V3",
        44: "Heltec WSL V3",
        45: "BetaFPV 2400 TX",
        46: "BetaFPV 900 Nano TX",
        47: "RPi Pico",
        48: "Heltec Wireless Tracker",
        49: "Heltec Wireless Paper",
        50: "T-Deck",
        51: "T-Watch S3",
        52: "PiComputer S3",
        53: "Heltec HT62",
        54: "eByte ESP32-S3",
        55: "ESP32-S3 Pico",
        56: "Chatter 2",
        57: "Heltec Wireless Paper V1.0",
        58: "Heltec Wireless Tracker V1.0",
        59: "unPhone",
        60: "TD LoRaC",
        61: "CDEBYTE EoRa S3",
        62: "TWC Mesh V4",
        63: "nRF52 ProMicro DIY",
        64: "RadioMaster 900 Bandit Nano",
        65: "Heltec Capsule Sensor V3",
        66: "Heltec Vision Master T190",
        67: "Heltec Vision Master E213",
        68: "Heltec Vision Master E290",
        69: "Heltec Mesh Node T114",
        70: "SenseCAP Indicator",
        71: "Tracker T1000-E",
        72: "RAK3172",
        73: "WIO-E5",
        74: "RadioMaster 900 Bandit",
        75: "ME25LS01 4Y10TD",
        76: "RP2040 Feather RFM95",
        77: "M5Stack Core Basic",
        78: "M5Stack Core2",
        79: "RPi Pico 2",
        80: "M5Stack CoreS3",
        81: "Seeed XIAO S3",
        82: "MS24SF1",
        83: "T-LoRa C6",
        84: "WisMesh Tap",
        85: "Routastic",
        86: "Mesh Tab",
        87: "MeshLink",
        88: "XIAO nRF52 Kit",
        89: "ThinkNode M1",
        90: "ThinkNode M2",
        91: "T-ETH Elite",
        92: "Heltec Sensor Hub",
        93: "Muzi Base",
        94: "Heltec Mesh Pocket",
        95: "Seeed Solar Node",
        96: "NomadStar Meteor Pro",
        97: "CrowPanel",
        98: "Link 32",
        99: "WIO Tracker L1",
        100: "WIO Tracker L1 E-Ink",
        101: "Muzi R1 Neo",
        102: "T-Deck Pro",
        103: "T-LoRa Pager",
        104: "M5Stack Reserved",
        105: "WisMesh Tag",
        106: "RAK3312",
        107: "ThinkNode M5",
        108: "Heltec Mesh Solar",
        109: "T-Echo Lite",
        110: "Heltec V4",
        111: "M5Stack C6L",
        112: "M5Stack Cardputer Adv",
        113: "Heltec Wireless Tracker V2",
        114: "T-Watch Ultra",
        115: "ThinkNode M3",
        116: "WisMesh Tap V2",
        117: "RAK3401",
        118: "RAK6421",
        119: "ThinkNode M4",
        120: "ThinkNode M6",
        121: "MeshStick 1262",
        122: "T-Beam 1 Watt",
        123: "T5 S3 E-Paper Pro",
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

    // ── Tile Layer Providers ─────────────────────────────────────────────────
    var TILE_LAYERS = {
        dark: {
            url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
            subdomains: "abcd",
            maxZoom: 19
        },
        light: {
            url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
            subdomains: "abcd",
            maxZoom: 19
        },
        satellite: {
            url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attribution: '&copy; Esri',
            subdomains: null,
            maxZoom: 18
        },
        topo: {
            url: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://opentopomap.org">OpenTopoMap</a>',
            subdomains: "abc",
            maxZoom: 17
        }
    };

    // ── State ────────────────────────────────────────────────────────────────
    var map = null;
    var markers = {};
    var mapInitialized = false;
    var knownMsgTypes = new Set();
    var debounceTimer = null;
    var currentTileLayer = null;

    // Cached data arrays
    var nodesData = [];
    var trafficData = [];

    // Sort state per table: { col: index, asc: boolean } or null
    var nodeSort = null;
    var trafficSort = null;

    // Node directory filter
    var nodeFilterText = "";
    var nodeFilterTimer = null;

    // Positions cache: { node_id: { latitude, longitude, timestamp } }
    var positionsMap = {};

    // Watch list (array of node_id strings)
    var watchList = [];

    // ── Init ─────────────────────────────────────────────────────────────────
    function init() {
        // Load watch list from localStorage
        try {
            var stored = localStorage.getItem("meshWatchList");
            if (stored) watchList = JSON.parse(stored);
        } catch (e) { watchList = []; }

        // Initialize map
        var savedTheme = localStorage.getItem("meshMapTheme") || "dark";
        map = L.map("map", { zoomControl: true }).setView([39.8, -98.5], 4);
        setMapTheme(savedTheme);

        // Wire up star buttons inside map popups
        map.on("popupopen", function (e) {
            var btn = e.popup.getElement().querySelector(".popup-star");
            if (btn) {
                btn.addEventListener("click", function () {
                    var nodeId = this.getAttribute("data-node");
                    toggleWatch(nodeId);
                    // Update the star in the open popup
                    var starred = watchList.indexOf(nodeId) !== -1;
                    this.textContent = starred ? "\u2605" : "\u2606";
                    this.className = (starred ? "star-btn starred" : "star-btn") + " popup-star";
                });
            }
        });

        // Set theme dropdown to saved value
        var themeSelect = document.getElementById("map-theme");
        themeSelect.value = savedTheme;
        themeSelect.addEventListener("change", function () {
            setMapTheme(this.value);
        });

        // Traffic filters
        document.getElementById("filter-type").addEventListener("change", function () {
            fetchTraffic();
        });

        document.getElementById("filter-node").addEventListener("input", function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(fetchTraffic, 300);
        });

        // Node directory filter
        document.getElementById("node-filter").addEventListener("input", function () {
            clearTimeout(nodeFilterTimer);
            var val = this.value;
            nodeFilterTimer = setTimeout(function () {
                nodeFilterText = val.trim().toLowerCase();
                renderNodes();
            }, 200);
        });

        // Sidebar toggle
        document.getElementById("sidebar-toggle").addEventListener("click", function () {
            document.getElementById("sidebar").classList.toggle("open");
        });

        // Initialize sort headers
        initSortHeaders();

        refresh();
        setInterval(refresh, 10000);
    }

    // ── Map Theme ────────────────────────────────────────────────────────────
    function setMapTheme(theme) {
        if (currentTileLayer) {
            map.removeLayer(currentTileLayer);
        }

        var cfg = TILE_LAYERS[theme] || TILE_LAYERS.dark;
        var opts = {
            attribution: cfg.attribution,
            maxZoom: cfg.maxZoom
        };
        if (cfg.subdomains) opts.subdomains = cfg.subdomains;

        currentTileLayer = L.tileLayer(cfg.url, opts).addTo(map);

        // Update body class for popup styling
        document.body.className = document.body.className.replace(/map-\w+/g, "");
        document.body.classList.add("map-" + theme);

        localStorage.setItem("meshMapTheme", theme);
    }

    // ── Sort Headers ─────────────────────────────────────────────────────────
    function initSortHeaders() {
        // Node table headers
        var nodeHeaders = document.querySelectorAll("#nodes-table th[data-col]");
        nodeHeaders.forEach(function (th) {
            th.addEventListener("click", function () {
                var col = parseInt(this.getAttribute("data-col"), 10);
                if (nodeSort && nodeSort.col === col) {
                    nodeSort.asc = !nodeSort.asc;
                } else {
                    nodeSort = { col: col, asc: true };
                }
                updateSortArrows("#nodes-table", nodeSort);
                renderNodes();
            });
        });

        // Traffic table headers
        var trafficHeaders = document.querySelectorAll("#traffic-table th[data-col]");
        trafficHeaders.forEach(function (th) {
            th.addEventListener("click", function () {
                var col = parseInt(this.getAttribute("data-col"), 10);
                if (trafficSort && trafficSort.col === col) {
                    trafficSort.asc = !trafficSort.asc;
                } else {
                    trafficSort = { col: col, asc: true };
                }
                updateSortArrows("#traffic-table", trafficSort);
                renderTraffic();
            });
        });
    }

    function updateSortArrows(tableSelector, sortState) {
        var headers = document.querySelectorAll(tableSelector + " th[data-col]");
        headers.forEach(function (th) {
            // Remove existing arrow
            var arrow = th.querySelector(".sort-arrow");
            if (arrow) arrow.remove();

            var col = parseInt(th.getAttribute("data-col"), 10);
            if (sortState && sortState.col === col) {
                var span = document.createElement("span");
                span.className = "sort-arrow";
                span.textContent = sortState.asc ? "\u25B2" : "\u25BC";
                th.appendChild(span);
            }
        });
    }

    // ── Refresh ──────────────────────────────────────────────────────────────
    function refresh() {
        fetchStats();
        fetchNodes();
        fetchTraffic();
        fetchPositions();
        fetchWatchList();
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

    // ── Node Name Display Helper ─────────────────────────────────────────────
    function displayNodeName(longName, shortName, nodeId) {
        if (longName || shortName) {
            return esc(longName || shortName);
        }
        // No name resolved — show hex User ID with unresolved label
        return '<span class="node-unnamed-id">' + esc(nodeId) + '</span>' +
            ' <span class="node-unnamed">(unresolved)</span>';
    }

    // ── Nodes ────────────────────────────────────────────────────────────────
    function fetchNodes() {
        fetchJSON("/api/nodes", function (rows) {
            nodesData = rows.map(function (n) {
                var hw = n.hw_model != null ? (HW_MODELS[n.hw_model] || ("ID " + n.hw_model)) : "\u2014";
                return {
                    node_id: n.node_id,
                    long_name: n.long_name,
                    short_name: n.short_name,
                    cols: [n.node_id, n.long_name || n.short_name || n.node_id, hw, n.first_seen || "", n.last_seen || ""],
                    hw: hw,
                    first_seen: n.first_seen,
                    last_seen: n.last_seen
                };
            });
            renderNodes();
        });
    }

    function renderNodes() {
        var tbody = document.querySelector("#nodes-table tbody");
        var rows = nodesData;

        if (rows.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="muted">No data yet</td></tr>';
            return;
        }

        // Filter
        if (nodeFilterText) {
            rows = rows.filter(function (n) {
                var searchable = n.cols.join(" ").toLowerCase();
                return searchable.indexOf(nodeFilterText) !== -1;
            });
        }

        // Sort
        if (nodeSort) {
            var col = nodeSort.col;
            var asc = nodeSort.asc;
            var isDate = col === 3 || col === 4;
            rows = rows.slice().sort(function (a, b) {
                var va = a.cols[col];
                var vb = b.cols[col];
                if (va == null) va = "";
                if (vb == null) vb = "";

                if (isDate) {
                    var da = va ? new Date(va).getTime() : 0;
                    var db = vb ? new Date(vb).getTime() : 0;
                    return asc ? da - db : db - da;
                }

                va = String(va).toLowerCase();
                vb = String(vb).toLowerCase();
                if (va < vb) return asc ? -1 : 1;
                if (va > vb) return asc ? 1 : -1;
                return 0;
            });
        }

        tbody.innerHTML = rows.map(function (n) {
            var isStarred = watchList.indexOf(n.node_id) !== -1;
            var starClass = isStarred ? "star-btn starred" : "star-btn";
            var starChar = isStarred ? "\u2605" : "\u2606";

            var pos = positionsMap[n.node_id];
            var pinHtml = "";
            if (pos) {
                var pinTitle = pos.latitude.toFixed(5) + ', ' + pos.longitude.toFixed(5);
                var pinDetails = positionDetails(pos);
                if (pinDetails.length > 0) {
                    pinTitle += ' | ' + pinDetails.join(' | ');
                }
                pinTitle += ' (' + fmtTime(pos.timestamp) + ')';
                pinHtml = ' <a href="#" class="coord-link pin-icon" data-lat="' + pos.latitude +
                    '" data-lng="' + pos.longitude +
                    '" data-node="' + esc(n.node_id) +
                    '" title="' + esc(pinTitle) + '">\u{1F4CD}</a>';
            }

            return "<tr>" +
                '<td class="th-star"><button class="' + starClass + '" data-node="' + esc(n.node_id) + '">' + starChar + '</button></td>' +
                "<td>" + esc(n.node_id) + pinHtml + "</td>" +
                "<td>" + displayNodeName(n.long_name, n.short_name, n.node_id) + "</td>" +
                "<td>" + esc(n.hw) + "</td>" +
                "<td>" + fmtTime(n.first_seen) + "</td>" +
                "<td>" + fmtTime(n.last_seen) + "</td>" +
                "</tr>";
        }).join("");

        // Attach star click handlers
        tbody.querySelectorAll(".star-btn").forEach(function (btn) {
            btn.addEventListener("click", function (e) {
                e.stopPropagation();
                toggleWatch(this.getAttribute("data-node"));
            });
        });

        // Attach coordinate link handlers
        attachCoordLinks(tbody);
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
            trafficData = rows.map(function (r) {
                var src = r.source_name || r.source_id || "";
                var dst = r.dest_name || r.dest_id || "";
                var dataStr = truncate(r.data || "", 60);
                return {
                    _raw: r,
                    cols: [r.timestamp || "", src, dst, r.msg_type || "", r.channel_name || "", dataStr]
                };
            });
            renderTraffic();
        });
    }

    function renderTraffic() {
        var tbody = document.querySelector("#traffic-table tbody");
        var rows = trafficData;

        if (rows.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="muted">No data yet</td></tr>';
            return;
        }

        // Sort
        if (trafficSort) {
            var col = trafficSort.col;
            var asc = trafficSort.asc;
            var isDate = col === 0;
            rows = rows.slice().sort(function (a, b) {
                var va = a.cols[col];
                var vb = b.cols[col];
                if (va == null) va = "";
                if (vb == null) vb = "";

                if (isDate) {
                    var da = va ? new Date(va).getTime() : 0;
                    var db = vb ? new Date(vb).getTime() : 0;
                    return asc ? da - db : db - da;
                }

                va = String(va).toLowerCase();
                vb = String(vb).toLowerCase();
                if (va < vb) return asc ? -1 : 1;
                if (va > vb) return asc ? 1 : -1;
                return 0;
            });
        }

        tbody.innerHTML = rows.map(function (item) {
            var r = item._raw;
            var srcDisplay = r.source_name
                ? esc(r.source_name)
                : (r.source_id ? '<span class="node-unnamed-id">' + esc(r.source_id) + '</span> <span class="node-unnamed">(unresolved)</span>' : "\u2014");
            var dstDisplay = r.dest_name
                ? esc(r.dest_name)
                : (r.dest_id ? '<span class="node-unnamed-id">' + esc(r.dest_id) + '</span> <span class="node-unnamed">(unresolved)</span>' : "\u2014");
            var dataStr = truncate(r.data || "", 60);

            // Add pin icon for POSITION_APP with valid coordinates
            var pinHtml = "";
            if (r.msg_type === "POSITION_APP" && r.data) {
                try {
                    var pd = JSON.parse(r.data);
                    var plat = pd.latitude || 0;
                    var plng = pd.longitude || 0;
                    if (plat !== 0 || plng !== 0) {
                        pinHtml = ' <a href="#" class="coord-link pin-icon" data-lat="' + plat +
                            '" data-lng="' + plng +
                            '" data-node="' + esc(r.source_id || "") +
                            '" title="Show on map">\u{1F4CD}</a>';
                    }
                } catch (e) {}
            }

            var lockHtml = encryptionIcon(r.key_used);

            return "<tr>" +
                "<td>" + lockHtml + " " + fmtTime(r.timestamp) + "</td>" +
                "<td>" + srcDisplay + "</td>" +
                "<td>" + dstDisplay + "</td>" +
                '<td><span class="badge ' + badgeClass(r.msg_type) + '">' + esc(r.msg_type) + '</span>' + pinHtml + '</td>' +
                "<td>" + esc(r.channel_name || "\u2014") + "</td>" +
                "<td>" + esc(dataStr) + "</td>" +
                "</tr>";
        }).join("");

        // Attach coordinate link handlers
        attachCoordLinks(tbody);
    }

    // ── Watch List ───────────────────────────────────────────────────────────
    function toggleWatch(nodeId) {
        var idx = watchList.indexOf(nodeId);
        if (idx !== -1) {
            watchList.splice(idx, 1);
        } else {
            watchList.push(nodeId);
        }
        localStorage.setItem("meshWatchList", JSON.stringify(watchList));
        renderNodes();
        fetchWatchList();
    }

    function fetchWatchList() {
        var container = document.getElementById("watchlist-container");

        if (watchList.length === 0) {
            container.innerHTML = '<p class="muted watchlist-empty">Click the star icon on any node to add it here</p>';
            return;
        }

        var url = "/api/watchlist?nodes=" + encodeURIComponent(watchList.join(","));
        fetchJSON(url, function (items) {
            if (!items || items.length === 0) {
                container.innerHTML = '<p class="muted watchlist-empty">No data for watched nodes</p>';
                return;
            }

            container.innerHTML = items.map(function (item) {
                var node = item.node || {};
                var nameHtml = displayNodeName(node.long_name, node.short_name, node.node_id);
                var hw = node.hw_model != null ? (HW_MODELS[node.hw_model] || ("ID " + node.hw_model)) : "\u2014";
                var lastSeen = node.last_seen ? fmtTime(node.last_seen) : "\u2014";

                var posHtml = "";
                if (item.position) {
                    // Parse precision from the position data if available
                    var wlPrec = null;
                    // Check the cached positionsMap for extra fields
                    var cachedPos = positionsMap[node.node_id];
                    if (cachedPos && cachedPos.precision_bits != null) {
                        wlPrec = cachedPos.precision_bits;
                    }
                    var precHtml = "";
                    if (wlPrec != null) {
                        precHtml = ' <span class="precision-badge">' + esc(precisionLabel(wlPrec)) + '</span>';
                    }
                    var altHtml = "";
                    if (cachedPos && cachedPos.altitude != null) {
                        altHtml = ' <span class="pos-detail">Alt: ' + cachedPos.altitude + 'm</span>';
                    }
                    var satsHtml = "";
                    if (cachedPos && cachedPos.sats_in_view != null) {
                        satsHtml = ' <span class="pos-detail">Sats: ' + cachedPos.sats_in_view + '</span>';
                    }
                    posHtml = '<div class="watchlist-card-position">' +
                        '<a href="#" class="coord-link" data-lat="' + item.position.latitude + '" data-lng="' + item.position.longitude + '" data-node="' + esc(node.node_id || "") + '">' +
                        item.position.latitude.toFixed(5) + ", " + item.position.longitude.toFixed(5) +
                        '</a>' +
                        " (" + fmtTime(item.position.timestamp) + ")" +
                        precHtml + altHtml + satsHtml +
                        '</div>';
                }

                var trafficHtml = "";
                if (item.traffic && item.traffic.length > 0) {
                    var entries = item.traffic.map(function (t) {
                        var raw = t.data || "";
                        var needsExpand = raw.length > 40;
                        var preview = truncate(raw, 40);

                        // For POSITION_APP, extract coords and add a map link
                        var posLink = "";
                        if (t.msg_type === "POSITION_APP" && raw) {
                            try {
                                var pd = JSON.parse(raw);
                                var plat = pd.latitude || 0;
                                var plng = pd.longitude || 0;
                                if (plat !== 0 || plng !== 0) {
                                    posLink = ' <a href="#" class="coord-link" data-lat="' + plat + '" data-lng="' + plng + '" data-node="' + esc(t.source_id || node.node_id || "") + '" title="Show on map">\u{1F4CD}</a>';
                                }
                            } catch (e) {}
                        }

                        var dataHtml;
                        if (needsExpand) {
                            dataHtml = '<span class="watchlist-traffic-data expandable">' +
                                '<span class="data-preview">' + esc(preview) + '</span>' +
                                '<span class="data-full" style="display:none">' + esc(raw) + '</span>' +
                                '</span>';
                        } else {
                            dataHtml = '<span class="watchlist-traffic-data">' + esc(raw) + '</span>';
                        }
                        var tLock = encryptionIcon(t.key_used);
                        return '<div class="watchlist-traffic-entry">' +
                            tLock +
                            '<span class="watchlist-traffic-time">' + fmtTime(t.timestamp) + '</span>' +
                            '<span class="badge ' + badgeClass(t.msg_type) + '">' + esc(t.msg_type) + '</span>' +
                            dataHtml + posLink +
                            '</div>';
                    }).join("");

                    trafficHtml = '<div class="watchlist-card-traffic">' +
                        '<div class="watchlist-card-traffic-title">Recent Activity</div>' +
                        entries +
                        '</div>';
                }

                return '<div class="watchlist-card">' +
                    '<div class="watchlist-card-header">' +
                        '<div>' +
                            '<div class="watchlist-card-name">' + nameHtml + '</div>' +
                            '<div class="watchlist-card-id">' + esc(node.node_id || "") + '</div>' +
                        '</div>' +
                        '<button class="watchlist-remove-btn" data-node="' + esc(node.node_id || "") + '" title="Remove">\u2715</button>' +
                    '</div>' +
                    '<div class="watchlist-card-meta">' +
                        '<span>' + esc(hw) + '</span>' +
                        '<span>Last: ' + lastSeen + '</span>' +
                    '</div>' +
                    posHtml +
                    trafficHtml +
                    '</div>';
            }).join("");

            // Attach remove handlers
            container.querySelectorAll(".watchlist-remove-btn").forEach(function (btn) {
                btn.addEventListener("click", function () {
                    toggleWatch(this.getAttribute("data-node"));
                });
            });

            // Attach expand/collapse handlers on truncated data
            container.querySelectorAll(".watchlist-traffic-data.expandable").forEach(function (el) {
                el.addEventListener("click", function () {
                    var preview = this.querySelector(".data-preview");
                    var full = this.querySelector(".data-full");
                    if (full.style.display === "none") {
                        preview.style.display = "none";
                        full.style.display = "";
                    } else {
                        preview.style.display = "";
                        full.style.display = "none";
                    }
                });
            });

            // Attach coordinate link handlers
            attachCoordLinks(container);
        });
    }

    // ── Positions / Map ──────────────────────────────────────────────────────
    function fetchPositions() {
        fetchJSON("/api/positions", function (rows) {
            if (rows.length === 0) return;

            // Update positions cache
            rows.forEach(function (p) {
                positionsMap[p.source_id] = {
                    latitude: p.latitude,
                    longitude: p.longitude,
                    timestamp: p.timestamp,
                    precision_bits: p.precision_bits,
                    altitude: p.altitude,
                    sats_in_view: p.sats_in_view,
                    ground_speed: p.ground_speed
                };
            });

            // Re-render nodes to pick up pin icons
            renderNodes();

            var bounds = [];

            rows.forEach(function (p) {
                var latlng = [p.latitude, p.longitude];
                bounds.push(latlng);

                var nameHtml;
                if (p.source_name) {
                    nameHtml = "<b>" + esc(p.source_name) + "</b>";
                } else {
                    nameHtml = '<b class="node-unnamed-id">' + esc(p.source_id) + '</b> <span class="node-unnamed">(unresolved)</span>';
                }
                var isStarred = watchList.indexOf(p.source_id) !== -1;
                var starChar = isStarred ? "\u2605" : "\u2606";
                var starClass = isStarred ? "star-btn starred" : "star-btn";
                var detailParts = positionDetails(p);
                var detailHtml = "";
                if (detailParts.length > 0) {
                    detailHtml = '<div class="popup-details">' +
                        detailParts.map(function (d) { return '<span>' + esc(d) + '</span>'; }).join("") +
                        '</div>';
                }

                var popup = '<div class="popup-header">' +
                    '<button class="' + starClass + ' popup-star" data-node="' + esc(p.source_id) + '">' + starChar + '</button> ' +
                    nameHtml + '</div>' +
                    esc(p.source_id) + "<br>" +
                    p.latitude.toFixed(5) + ", " + p.longitude.toFixed(5) + "<br>" +
                    detailHtml +
                    '<small class="popup-pos-time">Position updated ' + fmtTime(p.timestamp) + '</small>';

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

    // ── Pan to Node on Map ─────────────────────────────────────────────────
    function panToNode(lat, lng, nodeId) {
        map.setView([lat, lng], 15);
        if (nodeId && markers[nodeId]) {
            markers[nodeId].openPopup();
        }
        // Scroll map panel into view on mobile/small screens
        document.getElementById("panel-map").scrollIntoView({ behavior: "smooth", block: "center" });
    }

    function attachCoordLinks(container) {
        container.querySelectorAll(".coord-link").forEach(function (link) {
            link.addEventListener("click", function (e) {
                e.preventDefault();
                var lat = parseFloat(this.getAttribute("data-lat"));
                var lng = parseFloat(this.getAttribute("data-lng"));
                var nodeId = this.getAttribute("data-node");
                panToNode(lat, lng, nodeId);
            });
        });
    }

    // ── Encryption Icon Helper ───────────────────────────────────────────────
    function encryptionIcon(keyUsed) {
        if (keyUsed === "public") {
            return '<svg class="lock-icon lock-public" title="Public channel (default key)" viewBox="0 0 16 16"><title>Public channel (default key)</title><path d="M11 5V4a3 3 0 0 0-6 0v1" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><rect x="3" y="7" width="10" height="7" rx="1.5" fill="currentColor"/></svg>';
        }
        if (keyUsed === "private") {
            return '<svg class="lock-icon lock-private" title="Private channel (encrypted)" viewBox="0 0 16 16"><title>Private channel (encrypted)</title><path d="M5 7V4a3 3 0 0 1 6 0v3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><rect x="3" y="7" width="10" height="7" rx="1.5" fill="currentColor"/></svg>';
        }
        return "";
    }

    // ── Position Precision Helper ────────────────────────────────────────────
    function precisionLabel(bits) {
        if (bits == null) return null;
        if (bits === 0) return "Disabled";
        if (bits >= 32) return "Full (~1cm)";
        if (bits >= 23) return "High (~1m)";
        if (bits >= 19) return "Med (~75m)";
        if (bits >= 16) return "Low (~600m)";
        if (bits >= 14) return "City (~2.4km)";
        if (bits >= 13) return "Region (~4.8km)";
        if (bits >= 11) return "Area (~19km)";
        return "Coarse (~" + Math.round(40075000 / Math.pow(2, bits)) + "m)";
    }

    function positionDetails(p) {
        var parts = [];
        var prec = precisionLabel(p.precision_bits);
        if (prec) parts.push("Precision: " + prec + " (" + p.precision_bits + " bits)");
        if (p.altitude != null) parts.push("Alt: " + p.altitude + "m");
        if (p.sats_in_view != null) parts.push("Sats: " + p.sats_in_view);
        if (p.ground_speed != null) parts.push("Speed: " + p.ground_speed + " km/h");
        return parts;
    }

    // ── Utilities ────────────────────────────────────────────────────────────
    function esc(s) {
        if (s == null) return "";
        var div = document.createElement("div");
        div.appendChild(document.createTextNode(String(s)));
        return div.innerHTML;
    }

    function fmtTime(iso) {
        if (!iso) return "\u2014";
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
