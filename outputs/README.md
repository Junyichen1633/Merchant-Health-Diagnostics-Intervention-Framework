# Generated Outputs

Run the pipeline to regenerate these files locally:

```bash
python3 src/run_pipeline.py
```

Generated CSVs:

- `merchant_month_metrics.csv`: Merchant-month base metrics.
- `merchant_health_scores.csv`: Health score, component scores, and driver decomposition.
- `merchant_segments.csv`: Latest merchant snapshot with cluster labels and recommended interventions.
- `driver_feature_importance.csv`: Random forest driver ranking.
- `regression_summaries.csv`: Observational regression outputs for product hypotheses.
- `health_score_sensitivity.csv`: Sensitivity check for alternate health score designs.
- `intervention_evaluation_plan.csv`: Merchant 30-day intervention measurement plan.
- `intervention_evaluation_summary.csv`: Aggregated expected lift by issue and priority.

Large generated CSVs are excluded from GitHub so the repository stays lightweight and reproducible.
