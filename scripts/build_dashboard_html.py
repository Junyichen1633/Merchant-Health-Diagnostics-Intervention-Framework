from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from plotly.offline import get_plotlyjs


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "dashboard"
OUTPUT_HTML = DASHBOARD_DIR / "merchant_health_dashboard.html"


def _latest_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["seller_id", "order_month_str"]).copy()
    return df.groupby("seller_id", as_index=False).tail(1).copy()


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records"))


def _load_data() -> dict:
    dashboard = pd.read_csv(DASHBOARD_DIR / "merchant_health_dashboard.csv")
    interventions = pd.read_csv(DASHBOARD_DIR / "merchant_interventions.csv")
    importance = pd.read_csv(ROOT / "outputs" / "driver_feature_importance.csv")
    regressions = pd.read_csv(ROOT / "outputs" / "regression_summaries.csv")

    latest = _latest_snapshot(dashboard)
    month_order = sorted(dashboard["order_month_str"].dropna().unique())

    monthly = (
        dashboard.groupby("order_month_str", as_index=False)
        .agg(
            avg_health=("health_score", "mean"),
            median_health=("health_score", "median"),
            gmv=("gmv", "sum"),
            orders=("order_count", "sum"),
            active_merchants=("seller_id", "nunique"),
            at_risk_merchants=("health_band", lambda s: (s == "At-Risk").sum()),
            avg_review_score=("avg_review_score", "mean"),
            on_time_rate=("on_time_rate", "mean"),
        )
        .sort_values("order_month_str")
    )

    monthly_segment = (
        dashboard.groupby(["order_month_str", "segment"], as_index=False)
        .agg(avg_health=("health_score", "mean"), merchant_months=("seller_id", "nunique"))
        .sort_values(["order_month_str", "segment"])
    )

    latest_small = latest[
        [
            "seller_id",
            "seller_state",
            "primary_category",
            "segment",
            "health_score",
            "health_band",
            "fulfillment_score",
            "satisfaction_score",
            "retention_score",
            "growth_score",
            "dominant_issue",
            "intervention_priority",
            "recommended_action",
            "gmv",
            "order_count",
            "lifetime_gmv",
            "lifetime_orders",
        ]
    ].copy()

    importance_small = importance.head(8).copy()
    regressions_small = regressions[
        regressions["model"].isin(["H1_review_delay", "Health_driver_model"])
        & regressions["term"].isin(["avg_late_days", "avg_review_score", "gmv_momentum"])
    ][["model", "term", "coefficient", "p_value", "interpretation"]].copy()

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "month_order": month_order,
        "monthly": _records(monthly),
        "monthly_segment": _records(monthly_segment),
        "latest": _records(latest_small),
        "interventions": _records(interventions),
        "importance": _records(importance_small),
        "regressions": _records(regressions_small),
    }


def build_html(data: dict) -> str:
    plotly_js = get_plotlyjs()
    payload = json.dumps(data, ensure_ascii=False)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Merchant Health Diagnostics Dashboard</title>
  <style>
    :root {{
      --ink: #172033;
      --muted: #667085;
      --line: #d9e2ec;
      --panel: #ffffff;
      --page: #f5f7fb;
      --blue: #215aa8;
      --green: #267a5e;
      --amber: #b76e00;
      --red: #b42318;
      --teal: #087f8c;
      --purple: #6941c6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--page);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }}
    header {{
      background: #ffffff;
      border-bottom: 1px solid var(--line);
      padding: 24px 32px 20px;
      position: sticky;
      top: 0;
      z-index: 10;
    }}
    h1 {{
      font-size: 26px;
      margin: 0 0 6px;
      font-weight: 750;
    }}
    .subtitle {{
      color: var(--muted);
      font-size: 14px;
      line-height: 1.45;
      max-width: 980px;
    }}
    main {{
      padding: 24px 32px 36px;
      max-width: 1480px;
      margin: 0 auto;
    }}
    .toolbar {{
      display: flex;
      gap: 14px;
      align-items: end;
      flex-wrap: wrap;
      margin-bottom: 18px;
    }}
    label {{
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin: 0 0 6px;
      font-weight: 650;
      text-transform: uppercase;
    }}
    select, button {{
      min-height: 40px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      padding: 0 12px;
      font-size: 14px;
    }}
    button {{
      cursor: pointer;
      background: var(--blue);
      border-color: var(--blue);
      color: #fff;
      font-weight: 650;
    }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(4, minmax(180px, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }}
    .kpi, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }}
    .kpi {{
      padding: 16px 18px;
      min-height: 104px;
    }}
    .kpi .label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      font-weight: 700;
    }}
    .kpi .value {{
      font-size: 28px;
      font-weight: 780;
      margin-top: 8px;
    }}
    .kpi .hint {{
      color: var(--muted);
      font-size: 12px;
      margin-top: 4px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1.35fr 0.9fr;
      gap: 16px;
      margin-bottom: 16px;
    }}
    .grid.three {{
      grid-template-columns: 1fr 1fr 1fr;
    }}
    .panel {{
      padding: 14px 14px 8px;
      min-height: 360px;
    }}
    .panel h2 {{
      font-size: 15px;
      margin: 2px 4px 8px;
      font-weight: 760;
    }}
    .chart {{
      width: 100%;
      height: 320px;
    }}
    .table-panel {{
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    .table-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
    }}
    .table-head h2 {{
      margin: 0;
      font-size: 15px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      border-bottom: 1px solid #eef2f6;
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      background: #f8fafc;
      position: sticky;
      top: 0;
    }}
    .badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid transparent;
      white-space: nowrap;
    }}
    .High {{ color: var(--red); background: #fff1f0; border-color: #ffd5d2; }}
    .Medium {{ color: var(--amber); background: #fff7e6; border-color: #ffe0a3; }}
    .Low {{ color: var(--green); background: #ecfdf3; border-color: #b8f0ce; }}
    .note {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      padding: 12px 4px 2px;
    }}
    @media (max-width: 980px) {{
      header, main {{ padding-left: 18px; padding-right: 18px; }}
      .kpis, .grid, .grid.three {{ grid-template-columns: 1fr; }}
      .chart {{ height: 300px; }}
      table {{ min-width: 900px; }}
      .table-panel {{ overflow-x: auto; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Merchant Health Diagnostics Dashboard</h1>
    <div class="subtitle">
      Tableau/Power BI alternative built with Plotly. The dashboard flags merchant risk, decomposes health drivers, and turns findings into intervention actions. Generated {data["generated_at"]}.
    </div>
  </header>
  <main>
    <section class="toolbar" aria-label="Dashboard filters">
      <div>
        <label for="segmentFilter">Segment</label>
        <select id="segmentFilter"></select>
      </div>
      <div>
        <label for="priorityFilter">Priority</label>
        <select id="priorityFilter"></select>
      </div>
      <button id="resetFilters" type="button">Reset Filters</button>
    </section>

    <section class="kpis">
      <div class="kpi"><div class="label">Merchants</div><div id="kpiMerchants" class="value"></div><div class="hint">latest merchant snapshot</div></div>
      <div class="kpi"><div class="label">Median Health</div><div id="kpiHealth" class="value"></div><div class="hint">0-100 percentile score</div></div>
      <div class="kpi"><div class="label">GMV At Risk</div><div id="kpiGmv" class="value"></div><div class="hint">High/Medium priority merchants</div></div>
      <div class="kpi"><div class="label">High Priority</div><div id="kpiPriority" class="value"></div><div class="hint">needs immediate diagnosis</div></div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>Health Score Over Time</h2>
        <div id="healthTrend" class="chart"></div>
      </div>
      <div class="panel">
        <h2>Latest Segment Mix</h2>
        <div id="segmentMix" class="chart"></div>
      </div>
    </section>

    <section class="grid three">
      <div class="panel">
        <h2>Current Weakest Driver</h2>
        <div id="driverMix" class="chart"></div>
      </div>
      <div class="panel">
        <h2>Component Scores</h2>
        <div id="componentScores" class="chart"></div>
      </div>
      <div class="panel">
        <h2>Model Driver Importance</h2>
        <div id="featureImportance" class="chart"></div>
      </div>
    </section>

    <section class="table-panel">
      <div class="table-head">
        <h2>Recommended Intervention Queue</h2>
        <div class="note" id="tableCount"></div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Seller</th>
            <th>Segment</th>
            <th>Priority</th>
            <th>Health</th>
            <th>Dominant Issue</th>
            <th>GMV</th>
            <th>Recommended Action</th>
          </tr>
        </thead>
        <tbody id="interventionRows"></tbody>
      </table>
    </section>

    <div class="note">
      Method note: regression findings are observational and should be described as associations, not causal proof. Repeat purchase is sparse in Olist, so review and fulfillment metrics are used as leading indicators.
    </div>
  </main>

  <script>{plotly_js}</script>
  <script>
    const DATA = {payload};
    const palette = {{
      "Champions": "#267a5e",
      "Stable Core": "#215aa8",
      "At-Risk": "#b42318",
      "Logistics Issue": "#b76e00",
      "fulfillment": "#087f8c",
      "satisfaction": "#6941c6",
      "retention": "#215aa8",
      "growth": "#267a5e"
    }};
    function layoutBase() {{
      return {{
        margin: {{ l: 48, r: 20, t: 18, b: 48 }},
        paper_bgcolor: "#ffffff",
        plot_bgcolor: "#ffffff",
        font: {{ family: "Inter, system-ui, sans-serif", color: "#172033" }},
        xaxis: {{ gridcolor: "#edf2f7", zeroline: false }},
        yaxis: {{ gridcolor: "#edf2f7", zeroline: false }},
        hoverlabel: {{ bgcolor: "#172033", font: {{ color: "#ffffff" }} }}
      }};
    }}
    const config = {{ displayModeBar: false, responsive: true }};

    function fmtInt(value) {{
      return Math.round(value || 0).toLocaleString();
    }}
    function fmtMoney(value) {{
      if (!value) return "$0";
      if (value >= 1_000_000) return "$" + (value / 1_000_000).toFixed(1) + "M";
      if (value >= 1_000) return "$" + (value / 1_000).toFixed(1) + "K";
      return "$" + Math.round(value).toLocaleString();
    }}
    function median(values) {{
      const clean = values.filter(v => Number.isFinite(v)).sort((a, b) => a - b);
      if (!clean.length) return 0;
      const mid = Math.floor(clean.length / 2);
      return clean.length % 2 ? clean[mid] : (clean[mid - 1] + clean[mid]) / 2;
    }}
    function filteredLatest() {{
      const segment = document.getElementById("segmentFilter").value;
      const priority = document.getElementById("priorityFilter").value;
      return DATA.latest.filter(row =>
        (segment === "All" || row.segment === segment) &&
        (priority === "All" || row.intervention_priority === priority)
      );
    }}
    function groupCount(rows, field) {{
      const out = {{}};
      rows.forEach(row => {{ out[row[field]] = (out[row[field]] || 0) + 1; }});
      return out;
    }}
    function setupFilters() {{
      const segments = ["All", ...Array.from(new Set(DATA.latest.map(d => d.segment))).sort()];
      const priorities = ["All", "High", "Medium", "Low"];
      const segmentEl = document.getElementById("segmentFilter");
      const priorityEl = document.getElementById("priorityFilter");
      segmentEl.innerHTML = segments.map(s => `<option value="${{s}}">${{s}}</option>`).join("");
      priorityEl.innerHTML = priorities.map(s => `<option value="${{s}}">${{s}}</option>`).join("");
      segmentEl.addEventListener("change", render);
      priorityEl.addEventListener("change", render);
      document.getElementById("resetFilters").addEventListener("click", () => {{
        segmentEl.value = "All";
        priorityEl.value = "All";
        render();
      }});
    }}
    function renderKpis(rows) {{
      const highMedium = rows.filter(d => d.intervention_priority === "High" || d.intervention_priority === "Medium");
      document.getElementById("kpiMerchants").textContent = fmtInt(rows.length);
      document.getElementById("kpiHealth").textContent = median(rows.map(d => d.health_score)).toFixed(1);
      document.getElementById("kpiGmv").textContent = fmtMoney(highMedium.reduce((acc, d) => acc + (d.lifetime_gmv || 0), 0));
      document.getElementById("kpiPriority").textContent = fmtInt(rows.filter(d => d.intervention_priority === "High").length);
    }}
    function renderHealthTrend() {{
      const selected = document.getElementById("segmentFilter").value;
      let traces = [];
      if (selected === "All") {{
        traces.push({{
          x: DATA.monthly.map(d => d.order_month_str),
          y: DATA.monthly.map(d => d.avg_health),
          type: "scatter",
          mode: "lines+markers",
          name: "Average health",
          line: {{ color: "#215aa8", width: 3 }},
          hovertemplate: "%{{x}}<br>Avg health: %{{y:.1f}}<extra></extra>"
        }});
        traces.push({{
          x: DATA.monthly.map(d => d.order_month_str),
          y: DATA.monthly.map(d => d.at_risk_merchants),
          type: "bar",
          name: "At-risk merchant-months",
          marker: {{ color: "rgba(180,35,24,0.22)" }},
          yaxis: "y2",
          hovertemplate: "%{{x}}<br>At-risk rows: %{{y}}<extra></extra>"
        }});
      }} else {{
        const segRows = DATA.monthly_segment.filter(d => d.segment === selected);
        traces.push({{
          x: segRows.map(d => d.order_month_str),
          y: segRows.map(d => d.avg_health),
          type: "scatter",
          mode: "lines+markers",
          name: selected,
          line: {{ color: palette[selected] || "#215aa8", width: 3 }},
          hovertemplate: "%{{x}}<br>Avg health: %{{y:.1f}}<extra></extra>"
        }});
      }}
      const base = layoutBase();
      Plotly.newPlot("healthTrend", traces, {{
        ...base,
        yaxis: {{ ...base.yaxis, title: "Health score", range: [0, 100] }},
        yaxis2: {{ title: "At-risk", overlaying: "y", side: "right", showgrid: false }},
        legend: {{ orientation: "h", y: 1.08 }}
      }}, config);
    }}
    function renderSegmentMix(rows) {{
      const counts = groupCount(rows, "segment");
      const labels = Object.keys(counts).sort();
      const base = layoutBase();
      Plotly.newPlot("segmentMix", [{{
        x: labels,
        y: labels.map(k => counts[k]),
        type: "bar",
        marker: {{ color: labels.map(k => palette[k] || "#667085") }},
        hovertemplate: "%{{x}}<br>Merchants: %{{y}}<extra></extra>"
      }}], {{
        ...base,
        yaxis: {{ ...base.yaxis, title: "Merchants" }}
      }}, config);
    }}
    function renderDriverMix(rows) {{
      const counts = groupCount(rows, "dominant_issue");
      const labels = Object.keys(counts).sort();
      const base = layoutBase();
      Plotly.newPlot("driverMix", [{{
        labels,
        values: labels.map(k => counts[k]),
        type: "pie",
        hole: 0.54,
        marker: {{ colors: labels.map(k => palette[k] || "#667085") }},
        hovertemplate: "%{{label}}<br>Merchants: %{{value}}<extra></extra>"
      }}], {{
        ...base,
        showlegend: true,
        legend: {{ orientation: "h", y: -0.1 }}
      }}, config);
    }}
    function renderComponentScores(rows) {{
      const fields = [
        ["Fulfillment", "fulfillment_score", "#087f8c"],
        ["Satisfaction", "satisfaction_score", "#6941c6"],
        ["Retention", "retention_score", "#215aa8"],
        ["Growth", "growth_score", "#267a5e"]
      ];
      const y = fields.map(([label]) => label);
      const x = fields.map(([, key]) => rows.length ? rows.reduce((a, d) => a + (d[key] || 0), 0) / rows.length : 0);
      const base = layoutBase();
      Plotly.newPlot("componentScores", [{{
        x,
        y,
        type: "bar",
        orientation: "h",
        marker: {{ color: fields.map(([, , color]) => color) }},
        hovertemplate: "%{{y}}<br>Avg score: %{{x:.1f}}<extra></extra>"
      }}], {{
        ...base,
        xaxis: {{ ...base.xaxis, title: "Average score", range: [0, 100] }},
        margin: {{ l: 96, r: 20, t: 18, b: 48 }}
      }}, config);
    }}
    function renderFeatureImportance() {{
      const rows = [...DATA.importance].reverse();
      const base = layoutBase();
      Plotly.newPlot("featureImportance", [{{
        x: rows.map(d => d.importance),
        y: rows.map(d => d.feature.replaceAll("_", " ")),
        type: "bar",
        orientation: "h",
        marker: {{ color: "#215aa8" }},
        hovertemplate: "%{{y}}<br>Importance: %{{x:.3f}}<extra></extra>"
      }}], {{
        ...base,
        margin: {{ l: 128, r: 20, t: 18, b: 48 }},
        xaxis: {{ ...base.xaxis, title: "Importance" }}
      }}, config);
    }}
    function renderTable(rows) {{
      const sorted = [...rows]
        .sort((a, b) => {{
          const p = {{ High: 0, Medium: 1, Low: 2 }};
          return (p[a.intervention_priority] - p[b.intervention_priority]) || (a.health_score - b.health_score);
        }})
        .slice(0, 30);
      document.getElementById("tableCount").textContent = `Showing ${{sorted.length}} of ${{rows.length}} merchants`;
      document.getElementById("interventionRows").innerHTML = sorted.map(row => `
        <tr>
          <td>${{row.seller_id.slice(0, 10)}}...</td>
          <td>${{row.segment}}</td>
          <td><span class="badge ${{row.intervention_priority}}">${{row.intervention_priority}}</span></td>
          <td>${{row.health_score.toFixed(1)}}</td>
          <td>${{row.dominant_issue}}</td>
          <td>${{fmtMoney(row.lifetime_gmv || row.gmv)}}</td>
          <td>${{row.recommended_action}}</td>
        </tr>
      `).join("");
    }}
    function render() {{
      const rows = filteredLatest();
      renderKpis(rows);
      renderHealthTrend();
      renderSegmentMix(rows);
      renderDriverMix(rows);
      renderComponentScores(rows);
      renderFeatureImportance();
      renderTable(rows);
    }}
    setupFilters();
    render();
  </script>
</body>
</html>
"""


def main() -> None:
    data = _load_data()
    OUTPUT_HTML.write_text(build_html(data), encoding="utf-8")
    print(f"Dashboard written to: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
