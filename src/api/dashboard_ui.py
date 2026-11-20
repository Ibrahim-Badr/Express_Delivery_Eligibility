DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Logistics Operator Dashboard | Express Delivery Eligibility</title>
  <style>
    :root {
      --bg: #0f172a;
      --surface: #1e293b;
      --surface-alt: #273449;
      --text: #f8fafc;
      --muted: #94a3b8;
      --border: #334155;
      --accent: #38bdf8;
      --express: #10b981;
      --express-bg: rgba(16, 185, 129, 0.16);
      --standard: #64748b;
      --warn: #f59e0b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }
    .skip-link {
      position: absolute;
      left: -9999px;
      background: var(--accent);
      color: #000;
      padding: 0.5rem 1rem;
      font-weight: 600;
    }
    .skip-link:focus { left: 1rem; top: 1rem; z-index: 50; }
    header {
      padding: 1.25rem 1.5rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      background: var(--surface);
    }
    h1 { margin: 0; font-size: 1.35rem; }
    .subtitle { margin: 0.2rem 0 0; color: var(--muted); font-size: 0.9rem; }
    .actions { display: flex; gap: 0.75rem; flex-wrap: wrap; align-items: center; }
    button, a.nav-btn {
      min-block-size: 38px;
      padding: 0.45rem 0.95rem;
      border-radius: 0.5rem;
      border: 1px solid var(--border);
      background: var(--surface-alt);
      color: var(--text);
      font-weight: 600;
      font-size: 0.88rem;
      cursor: pointer;
      text-decoration: none;
    }
    button.primary {
      background: var(--accent);
      color: #082f49;
      border-color: var(--accent);
    }
    button[aria-pressed="true"] {
      background: var(--express);
      color: #022c22;
      border-color: var(--express);
    }
    :where(a, button):focus-visible {
      outline: 3px solid var(--accent);
      outline-offset: 2px;
    }
    main { padding: 1.5rem; max-width: 1280px; margin: 0 auto; }
    .alert-banner {
      padding: 0.85rem 1.1rem;
      border-radius: 0.6rem;
      margin-bottom: 1.25rem;
      background: var(--surface);
      border: 1px solid var(--border);
      font-weight: 500;
    }
    .alert-banner.express-hit {
      background: var(--express-bg);
      border-color: var(--express);
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
      margin-bottom: 1.25rem;
    }
    .kpi-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1rem;
    }
    .kpi-label { color: var(--muted); font-size: 0.82rem; }
    .kpi-value { font-size: 1.65rem; font-weight: 700; margin-top: 0.25rem; }
    .toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-bottom: 0.9rem;
    }
    .table-wrapper {
      overflow: auto;
      max-inline-size: 100%;
      max-block-size: min(560px, 72vh);
      container-type: inline-size;
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      background: var(--surface);
    }
    table { width: 100%; border-collapse: separate; border-spacing: 0; }
    caption {
      text-align: left;
      padding: 0.75rem 1rem;
      font-weight: 600;
      color: var(--muted);
      background: var(--surface);
    }
    thead {
      position: sticky;
      inset-block-start: 0;
      z-index: 1;
      background: var(--surface-alt);
    }
    th, td {
      padding: 0.7rem 0.9rem;
      border-bottom: 1px solid var(--border);
      text-align: left;
      font-size: 0.88rem;
      white-space: nowrap;
    }
    tbody th { position: sticky; inset-inline-start: 0; background: var(--surface); }
    .badge {
      display: inline-block;
      padding: 0.2rem 0.55rem;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 700;
    }
    .badge-oui { background: var(--express-bg); color: #34d399; border: 1px solid #059669; }
    .badge-non { background: rgba(100,116,139,0.2); color: #cbd5e1; border: 1px solid #475569; }
    .badge-warn { color: var(--warn); font-weight: 600; }
    tr.prepared { opacity: 0.55; }
    @container (width < 680px) {
      table, thead, tbody, tr, th, td { display: block; white-space: normal; }
      thead { display: none; }
      tr { margin-block-end: 0.9rem; border-bottom: 2px solid var(--border); padding: 0.4rem; }
      tbody th { position: sticky; inset-block-start: 0; z-index: 2; background: var(--surface-alt); }
      td::before { font-weight: 600; color: var(--muted); content: attr(data-label) ": "; }
    }
  </style>
</head>
<body>
  <a href="#main-content" class="skip-link">Skip to delivery queue</a>
  <header>
    <div>
      <h1>Logistics Operator Dashboard</h1>
      <p class="subtitle">RabbitMQ (Pika) Real-Time Daily Delivery Preparation Stream</p>
    </div>
    <nav class="actions" aria-label="Dashboard actions">
      <button id="simulate-btn" class="primary" type="button">
        Simulate Live Order (RabbitMQ)
      </button>
      <a class="nav-btn" href="/docs">OpenAPI Docs</a>
    </nav>
  </header>

  <main id="main-content" tabindex="-1">
    <div id="live-alert" class="alert-banner" role="status" aria-live="polite">
      Connecting to RabbitMQ live order stream...
    </div>

    <section class="kpi-grid" aria-label="Daily shipment metrics">
      <div class="kpi-card">
        <div class="kpi-label">Orders Streamed</div>
        <div id="kpi-total" class="kpi-value">0</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Express Priority (OUI)</div>
        <div id="kpi-express" class="kpi-value" style="color: var(--express)">0</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Standard (NON)</div>
        <div id="kpi-standard" class="kpi-value">0</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Stock Alerts</div>
        <div id="kpi-stock" class="kpi-value" style="color: var(--warn)">0</div>
      </div>
    </section>

    <div class="toolbar">
      <div class="actions" role="group" aria-label="Filter deliveries">
        <button type="button" class="filter-btn" data-filter="all" aria-pressed="true">
          All Deliveries
        </button>
        <button type="button" class="filter-btn" data-filter="oui" aria-pressed="false">
          Express Only (OUI)
        </button>
        <button type="button" class="filter-btn" data-filter="non" aria-pressed="false">
          Standard Only (NON)
        </button>
      </div>
      <span id="stream-status" class="subtitle">Stream: active</span>
    </div>

    <div tabindex="0" role="region" aria-labelledby="deliveries-caption" class="table-wrapper">
      <table>
        <caption id="deliveries-caption">Incoming orders scored for Express eligibility</caption>
        <thead>
          <tr>
            <th scope="col">Order ID</th>
            <th scope="col">Decision</th>
            <th scope="col">Probability</th>
            <th scope="col">Zone</th>
            <th scope="col">Weather</th>
            <th scope="col">Weight / Dist</th>
            <th scope="col">Stock</th>
            <th scope="col">Customer</th>
            <th scope="col">Prep Action</th>
          </tr>
        </thead>
        <tbody id="deliveries-body"></tbody>
      </table>
    </div>
  </main>

  <script>
    const deliveries = [];
    const preparedIds = new Set();
    let currentFilter = "all";

    function updateSummary(summary) {
      document.getElementById("kpi-total").textContent = summary.total ?? deliveries.length;
      document.getElementById("kpi-express").textContent = summary.express_count ?? 0;
      document.getElementById("kpi-standard").textContent = summary.standard_count ?? 0;
      document.getElementById("kpi-stock").textContent = summary.out_of_stock_count ?? 0;
    }

    function recomputeSummary() {
      const expressCount = deliveries.filter((d) => d.decision === "oui").length;
      const stockAlerts = deliveries.filter((d) => d.stock_available === 0).length;
      updateSummary({
        total: deliveries.length,
        express_count: expressCount,
        standard_count: deliveries.length - expressCount,
        out_of_stock_count: stockAlerts,
      });
    }

    function notifyOperator(item) {
      const banner = document.getElementById("live-alert");
      if (item.decision === "oui") {
        banner.className = "alert-banner express-hit";
        banner.textContent =
          "EXPRESS ALERT: Order " + item.order_id + " (" + item.delivery_zone +
          ", prob=" + (item.probability * 100).toFixed(1) + "%) — prioritize dispatch!";
      } else {
        banner.className = "alert-banner";
        banner.textContent =
          "Order " + item.order_id + " received (Standard delivery, prob=" +
          (item.probability * 100).toFixed(1) + "%).";
      }
    }

    function addCell(row, label, text) {
      const td = document.createElement("td");
      td.setAttribute("data-label", label);
      td.textContent = text;
      row.appendChild(td);
      return td;
    }

    function renderTable() {
      const tbody = document.getElementById("deliveries-body");
      tbody.replaceChildren();
      const filtered = deliveries.filter((d) => {
        if (currentFilter === "all") return true;
        return d.decision === currentFilter;
      });
      for (const item of filtered) {
        const tr = document.createElement("tr");
        if (preparedIds.has(item.order_id)) tr.classList.add("prepared");

        const th = document.createElement("th");
        th.setAttribute("scope", "row");
        th.textContent = item.order_id;
        tr.appendChild(th);

        const decTd = document.createElement("td");
        decTd.setAttribute("data-label", "Decision");
        const badge = document.createElement("span");
        badge.className = "badge " + (item.decision === "oui" ? "badge-oui" : "badge-non");
        badge.textContent = item.decision === "oui" ? "EXPRESS (OUI)" : "STANDARD (NON)";
        decTd.appendChild(badge);
        tr.appendChild(decTd);

        addCell(tr, "Probability", (item.probability * 100).toFixed(1) + "%");
        addCell(tr, "Zone", item.delivery_zone);
        addCell(tr, "Weather", item.weather);
        addCell(tr, "Weight / Dist", item.weight_kg + "kg / " + item.distance_km + "km");

        const stockTd = addCell(tr, "Stock", item.stock_available ? "OK" : "OUT OF STOCK");
        if (!item.stock_available) stockTd.className = "badge-warn";

        addCell(tr, "Customer", item.customer_type);

        const actionTd = document.createElement("td");
        actionTd.setAttribute("data-label", "Prep Action");
        const btn = document.createElement("button");
        btn.type = "button";
        const isDone = preparedIds.has(item.order_id);
        btn.setAttribute("aria-pressed", String(isDone));
        btn.textContent = isDone ? "Prepared" : "Mark Prepared";
        btn.addEventListener("click", () => {
          if (preparedIds.has(item.order_id)) preparedIds.delete(item.order_id);
          else preparedIds.add(item.order_id);
          renderTable();
        });
        actionTd.appendChild(btn);
        tr.appendChild(actionTd);
        tbody.appendChild(tr);
      }
    }

    function ingestDelivery(item, notify) {
      if (deliveries.some((d) => d.order_id === item.order_id)) return;
      deliveries.unshift(item);
      if (deliveries.length > 100) deliveries.pop();
      if (notify) notifyOperator(item);
      recomputeSummary();
      renderTable();
    }

    async function loadRecent() {
      const resp = await fetch("/v1/stream/deliveries/recent?limit=25");
      if (!resp.ok) return;
      const data = await resp.json();
      for (const item of data.deliveries.slice().reverse()) ingestDelivery(item, false);
      updateSummary(data.summary);
      document.getElementById("live-alert").textContent =
        "Connected to RabbitMQ live queue (" + deliveries.length + " recent orders loaded).";
    }

    document.querySelectorAll(".filter-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        currentFilter = btn.dataset.filter;
        document.querySelectorAll(".filter-btn").forEach((b) => {
          b.setAttribute("aria-pressed", String(b === btn));
        });
        renderTable();
      });
    });

    document.getElementById("simulate-btn").addEventListener("click", async () => {
      const resp = await fetch("/v1/stream/simulate", { method: "POST" });
      if (resp.ok) ingestDelivery(await resp.json(), true);
    });

    const evtSource = new EventSource("/v1/stream/deliveries");
    evtSource.onmessage = (event) => {
      const item = JSON.parse(event.data);
      ingestDelivery(item, true);
    };
    evtSource.onerror = () => {
      document.getElementById("stream-status").textContent = "Stream: reconnecting...";
    };
    evtSource.onopen = () => {
      document.getElementById("stream-status").textContent = "Stream: active";
    };

    loadRecent();
  </script>
</body>
</html>
"""
