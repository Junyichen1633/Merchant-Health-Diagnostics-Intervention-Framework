# Merchant Health Dashboard

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

