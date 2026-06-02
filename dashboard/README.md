# Merchant Health Dashboard

## Local Tableau/Power BI Alternative

This project includes a static interactive dashboard built with Plotly:

```bash
python3 scripts/build_dashboard_html.py
```

Open `dashboard/merchant_health_dashboard.html` in a browser. It does not require Tableau, Power BI, Streamlit, or a local server.

The HTML dashboard includes:

- KPI cards for merchant count, median health, GMV at risk, and high-priority merchants.
- Segment and intervention-priority filters.
- Health trend, segment mix, driver mix, component scores, and feature-importance views.
- A recommended intervention queue for product action planning.

## Tableau Or Power BI Option

Use `dashboard/merchant_health_dashboard.csv` as the main Tableau or Power BI data source.

Recommended dashboard layout:

1. Merchant risk overview
   - KPI cards: active merchants, at-risk merchants, median health score, GMV at risk.
   - Filters: month, segment, seller state, product category.

2. Health over time
   - Line chart: average health score by month.
   - Stacked bars: merchant count by health band.

3. Why health changed
   - Decomposition view: fulfillment, satisfaction, retention, and growth scores.
   - Driver field: `health_drop_driver`.

4. Who needs intervention
   - Table: seller ID, segment, health score, dominant issue, intervention priority, recommended action.
   - Use conditional color on `intervention_priority`.

5. Product recommendation view
   - Bar chart: feature importance from `outputs/driver_feature_importance.csv`.
   - Regression summary table from `outputs/regression_summaries.csv`.
