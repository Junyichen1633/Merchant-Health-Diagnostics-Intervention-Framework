# Merchant Health Diagnostics & Intervention Framework

This project simulates a Shopify product data scientist workflow: define merchant health, identify at-risk merchants, diagnose the drivers of health changes, and recommend targeted product interventions.

The project uses the public Olist Brazilian E-commerce dataset. In this framing, Olist sellers are treated as Shopify merchants and Olist customers are treated as buyers. All core metrics are computed at the merchant-month grain.

## Problem

Merchant performance varies widely across fulfillment reliability, customer satisfaction, repeat purchase behavior, and GMV momentum. A product team needs a repeatable way to answer three questions:

1. Which merchants are healthy or at risk?
2. Why did merchant health change?
3. What intervention should Shopify prioritize?

## Approach

The pipeline builds a merchant-month health score from four components:

- Fulfillment: delivered rate, on-time rate, and average late days.
- Satisfaction: average review score and good-review rate.
- Retention: repeat order rate for customers buying again from the same merchant.
- Growth: GMV momentum and order-count momentum.

The components are standardized with z-scores, combined with explicit product weights, and converted to a 0-100 percentile health score:

- Fulfillment: 30%
- Satisfaction: 30%
- Retention: 20%
- Growth: 20%

The project also includes:

- Driver decomposition for month-over-month health drops.
- Merchant segmentation with business labels such as `Champions`, `At-Risk`, and `Logistics Issue`.
- Regression models for product hypotheses.
- Random forest feature importance for driver ranking.
- Tableau/Power BI-ready dashboard exports.

## Key Findings

The generated pipeline covers 16,441 merchant-month rows, 3,095 merchants, and about $13.6M in GMV.

Latest merchant segmentation:

- Stable Core: 1,113 merchants
- Logistics Issue: 758 merchants
- Champions: 705 merchants
- At-Risk: 519 merchants

Driver analysis:

- One additional late day is associated with a 0.091-point lower review score, controlling for merchant size, category, and month.
- One additional late day is associated with a 1.71-point lower health score.
- The strongest model drivers of health are average review score, GMV momentum, good-review rate, and on-time rate.
- Repeat purchase is very sparse in Olist: average repeat order rate is 0.69%, and only 4.31% of merchant-months have any repeat orders. I keep repeat purchase as the north-star retention signal, but treat review and fulfillment metrics as stronger observable leading indicators.

## Product Recommendation

Shopify should prioritize a merchant intervention system that first flags low-health merchants, then routes each merchant to a driver-specific playbook:

- Fulfillment issue: shipping diagnostics, carrier SLA monitoring, and fulfillment workflow guidance.
- Satisfaction issue: product quality, listing accuracy, and support workflow audits.
- Retention issue: win-back offers, email campaigns, and loyalty incentives.
- Growth issue: merchandising and demand-generation support.

The strongest evidence from this dataset is that fulfillment delays damage customer satisfaction, which then weakens merchant health. For a Shopify PM, the product bet would be: improve shipping reliability tooling for merchants with low fulfillment scores and monitor whether review score, repeat rate, and GMV momentum recover over subsequent months.

## How To Run

Raw Olist CSV files are not included in this repository. Download the Olist Brazilian E-commerce dataset from Kaggle and place the required files in `Dataset/`. See `Dataset/README.md` for the file list.

```bash
pip install -r requirements.txt
```

```bash
python3 src/run_pipeline.py
```

Main outputs:

- `outputs/merchant_month_metrics.csv`
- `outputs/merchant_health_scores.csv`
- `outputs/merchant_segments.csv`
- `outputs/driver_feature_importance.csv`
- `outputs/regression_summaries.csv`
- `dashboard/merchant_health_dashboard.csv`
- `dashboard/merchant_interventions.csv`

Generated CSV outputs are intentionally excluded from GitHub. Run the pipeline locally to recreate them.

## Interview Story

I built a merchant health diagnostics system using seller, order, delivery, review, and customer behavior data. I defined a merchant-month health score, decomposed health drops into fulfillment, satisfaction, retention, and growth drivers, segmented merchants into business-readable cohorts, and translated the outputs into targeted product interventions. The analysis found that delivery delays are strongly associated with lower customer reviews and lower overall merchant health, while repeat purchase is too sparse in Olist to be used alone. My recommendation is to prioritize shipping reliability and review-quality interventions for at-risk merchants, then measure downstream movement in repeat rate and GMV momentum.
