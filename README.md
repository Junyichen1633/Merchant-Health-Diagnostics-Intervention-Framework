# Merchant Health Diagnostics & Intervention Framework

This repository implements a merchant health decision system for a marketplace product team. It uses public Olist marketplace data as a proxy environment to define merchant health, diagnose risk drivers, recommend interventions, and plan a 30-day measurement loop.

Live dashboard: https://junyichen1633.github.io/Merchant-Health-Diagnostics-Intervention-Framework/docs/index.html

## Project Snapshot

- **Problem:** Identify which marketplace merchants need help, why they are at risk, and what intervention should happen next.
- **Scale:** 100K+ orders, 3,095 merchants, merchant-month analytical grain.
- **System:** Health scoring → risk diagnosis → segmentation → intervention recommendation → 30-day measurement plan.
- **Key finding:** Fulfillment delays were associated with lower customer reviews and weaker merchant health.
- **Tools:** Python, pandas, scikit-learn, statsmodels, Plotly.

![Merchant Health Dashboard Preview](dashboard/dashboard_preview.png)

## Business Problem

The motivation behind this project was simple.

Marketplace teams often have many merchant metrics, but they don't have a simple way to decide which merchants need attention first.

I wanted to build a framework that combines operational metrics into a single health score, explains why a merchant is unhealthy, and recommends what the product team should do next.

This project answers five product questions:

1. Which merchants are currently healthy, watch-listed, or at risk?
2. Which driver explains the risk: fulfillment, satisfaction, retention, or growth?
3. Which merchants should be prioritized first based on health, trend, and GMV exposure?
4. What product intervention should be recommended for each merchant?
5. How should the team evaluate whether the intervention improved health after 30 days?

## Metric Design

The core analytical grain is merchant-month:

```text
seller_id + order_month
```

The pipeline first collapses order-item data to the order-seller grain so review and customer signals are not duplicated when an order contains multiple items.

Merchant health is measured through four interpretable components:

- Fulfillment: delivered rate, on-time rate, average late days.
- Satisfaction: average review score, good-review rate.
- Retention: repeat order rate from buyers returning to the same merchant.
- Growth: GMV momentum and order-count momentum.

The primary score design is `business_calibrated_v1`:

- Fulfillment: 30%
- Satisfaction: 35%
- Retention: 15%
- Growth: 20%

Satisfaction was assigned a higher weight because customer review signals are available at a higher frequency and better reflect merchant quality in the Olist dataset.

The pipeline also runs sensitivity checks across alternative designs:

- `balanced`
- `experience_led`
- `retention_led`
- `growth_led`

The sensitivity output reports rank correlation, at-risk overlap, median score movement, and p90 score movement. This makes the metric governable: a PM can see whether merchant prioritization is stable when reasonable business assumptions change.

## Decision Framework

The goal of this project is not just to score merchants, but to support product decisions.

For each merchant-month, the pipeline follows a simple decision process:

1. Calculate fulfillment, satisfaction, retention, and growth metrics.
2. Combine them into an overall merchant health score.
3. Identify the weakest health component driving the score.
4. Prioritize merchants based on current health, recent deterioration, and GMV exposure.
5. Recommend a targeted intervention based on the dominant issue.
6. Define a 30-day evaluation plan to measure whether the intervention improved merchant health.

Rather than predicting outcomes with a black-box model, the framework emphasizes interpretability. A product manager should be able to understand why a merchant was flagged, what action is recommended, and how success will be measured after the intervention.

Intervention priority is based on current health and recent deterioration:

- High: severe current risk or sharp recent health decline.
- Medium: watch-list risk or moderate decline.
- Low: stable merchants that should be monitored or used as benchmarks.

The 30-day evaluation layer is a planning estimate, not a claimed experiment result. It uses the observational health-driver model plus bounded product assumptions to estimate expected lift, then recommends a matched-control or staggered-rollout readout.

## Dashboard

The interactive dashboard is built as a static Plotly HTML file, so it works as a Tableau or Power BI alternative without requiring local BI software.

Local dashboard:

```bash
python3 scripts/build_dashboard_html.py
```

Open:

```text
dashboard/merchant_health_dashboard.html
```

Published dashboard:

```text
https://junyichen1633.github.io/Merchant-Health-Diagnostics-Intervention-Framework/docs/index.html
```

Dashboard views:

- Merchant risk KPIs and GMV at risk.
- Health score trend over time.
- Latest segment mix.
- Weakest driver distribution.
- Component score comparison.
- Model driver importance.
- 30-day intervention evaluation.
- Health score sensitivity.
- Recommended intervention queue.

## Product Recommendations

The strongest product signal is that delivery delays are associated with lower review scores and lower merchant health. The recommended product direction is a merchant intervention system that routes merchants to driver-specific actions:

- Fulfillment issue: shipping diagnostics, carrier SLA monitoring, and fulfillment workflow guidance.
- Satisfaction issue: product quality, listing accuracy, and post-purchase support review.
- Retention issue: lifecycle campaigns, win-back offers, and loyalty tooling.
- Growth issue: merchandising support, demand-generation prompts, and assortment guidance.

The dashboard should be used as an operating loop:

1. Detect merchant risk.
2. Diagnose the dominant issue.
3. Trigger the recommended playbook.
4. Re-measure health after 30 days against a matched control or rollout holdout.
5. Promote interventions that lift health without hurting guardrail metrics.

## Limitations

- Olist is public marketplace data, not internal Shopify data.
- Subscription churn, merchant support tickets, app adoption, and actual intervention assignments are not observed.
- Repeat purchase is very sparse, so retention should be interpreted carefully.
- Regression outputs are observational and should be described as associations, not causal proof.
- The 30-day intervention lift is a decision-planning estimate until validated with an experiment or quasi-experiment.

## Future Work

This project uses the public Olist dataset as a proxy for a real marketplace, so several important signals are unavailable.

If Shopify merchant data were available, I would extend the framework by:

- Incorporating merchant support tickets, app adoption, subscription status, and fulfillment-provider data.
- Measuring intervention effectiveness with randomized rollouts or matched control groups instead of observational estimates.
- Tracking merchant health continuously through an automated monitoring pipeline instead of periodic offline analysis.
- Estimating confidence intervals for expected health improvements to better communicate uncertainty.

The current framework focuses on building a practical decision system. A production implementation would place greater emphasis on experimentation, continuous monitoring, and integration with operational workflows.

## How To Run

Raw Olist CSV files are not included in this repository. Download the Olist Brazilian E-commerce dataset from Kaggle and place the required files in `Dataset/`. See `Dataset/README.md` for the file list.

```bash
pip install -r requirements.txt
```

```bash
python3 src/run_pipeline.py
```

```bash
python3 scripts/build_dashboard_html.py
```

Main generated outputs:

- `outputs/merchant_month_metrics.csv`
- `outputs/merchant_health_scores.csv`
- `outputs/merchant_segments.csv`
- `outputs/driver_feature_importance.csv`
- `outputs/regression_summaries.csv`
- `outputs/health_score_sensitivity.csv`
- `outputs/intervention_evaluation_plan.csv`
- `outputs/intervention_evaluation_summary.csv`
- `dashboard/merchant_health_dashboard.csv`
- `dashboard/merchant_interventions.csv`
- `dashboard/merchant_health_dashboard.html`
- `docs/index.html`

Generated CSV outputs are excluded from GitHub so the repository stays lightweight and reproducible. The static dashboard HTML is included for review.
