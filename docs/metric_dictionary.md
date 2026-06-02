# Metric Dictionary

## Data Grain

All core metrics are computed at the merchant-month grain:

```text
seller_id + order_month
```

The base table is first built at the order-seller grain to avoid duplicating customer and review signals when one order contains multiple items.

## Merchant Health Components

### Fulfillment

- `delivered_rate`: Share of merchant orders that were delivered.
- `on_time_rate`: Share of delivered merchant orders delivered on or before the estimated delivery date.
- `avg_late_days`: Average number of days late, where early/on-time deliveries contribute zero late days.

### Satisfaction

- `avg_review_score`: Average customer review score from 1 to 5.
- `good_review_rate`: Share of reviews with score 4 or 5.
- `bad_review_rate`: Share of reviews with score 1 or 2.

### Retention

- `repeat_order_rate`: Share of merchant-month orders from customers who previously bought from the same merchant.

Olist has a sparse repeat-purchase signal, so this metric is kept as the north-star retention metric but interpreted cautiously. Fulfillment and review quality are treated as leading indicators of future retention.

### Growth

- `gmv`: Gross merchandise value, calculated from item price.
- `gmv_momentum`: Month-over-month change in log GMV, clipped to reduce outlier volatility.
- `order_momentum`: Month-over-month change in log order count, clipped to reduce outlier volatility.

## Health Score

Each raw metric is standardized with a z-score. Metrics where lower is better, such as `avg_late_days`, are directionally inverted before scoring.

Component weights:

- Fulfillment score: delivered rate, on-time rate, average late days.
- Satisfaction score: average review score, good-review rate.
- Retention score: repeat order rate.
- Growth score: GMV momentum, order momentum.

Overall health score:

```text
health_z =
    0.30 * fulfillment_z
  + 0.30 * satisfaction_z
  + 0.20 * retention_z
  + 0.20 * growth_z
```

The final `health_score` is the percentile rank of `health_z`, scaled from 0 to 100.

## Driver Decomposition

For each merchant-month, the pipeline computes month-over-month deltas for:

- `fulfillment_score`
- `satisfaction_score`
- `retention_score`
- `growth_score`
- `health_score`

If health drops, `health_drop_driver` is assigned to the component with the largest negative delta. `dominant_issue` is assigned to the currently weakest component, even when health did not drop.

## Segments And Actions

Merchants are clustered on latest health, component scores, lifetime scale, review quality, repeat behavior, and GMV momentum. Cluster centroids are translated into business-readable segment labels.

Recommended actions are assigned from the weakest current component:

- Fulfillment: shipping diagnostics and carrier SLA tooling.
- Satisfaction: product quality, listing accuracy, and support workflow audits.
- Retention: win-back offers, lifecycle campaigns, and loyalty incentives.
- Growth: merchandising and demand-generation support.

