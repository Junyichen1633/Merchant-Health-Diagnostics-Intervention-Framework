from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .metrics import (
        build_merchant_month_metrics,
        build_order_seller_frame,
        load_olist_data,
        score_merchant_months,
    )
    from .modeling import (
        build_dashboard_dataset,
        feature_importance,
        regression_summaries,
        segment_merchants,
    )
except ImportError:  # Allows `python src/run_pipeline.py`.
    from metrics import (
        build_merchant_month_metrics,
        build_order_seller_frame,
        load_olist_data,
        score_merchant_months,
    )
    from modeling import (
        build_dashboard_dataset,
        feature_importance,
        regression_summaries,
        segment_merchants,
    )


def run_pipeline(
    data_dir: str | Path = "Dataset",
    output_dir: str | Path = "outputs",
    dashboard_dir: str | Path = "dashboard",
) -> None:
    output_path = Path(output_dir)
    dashboard_path = Path(dashboard_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    dashboard_path.mkdir(parents=True, exist_ok=True)

    data = load_olist_data(data_dir)
    order_seller = build_order_seller_frame(data)
    monthly = build_merchant_month_metrics(order_seller)
    scored = score_merchant_months(monthly)
    segments = segment_merchants(scored)
    dashboard_data = build_dashboard_dataset(scored, segments)
    importance = feature_importance(scored)
    regressions = regression_summaries(scored)

    monthly.to_csv(output_path / "merchant_month_metrics.csv", index=False)
    scored.to_csv(output_path / "merchant_health_scores.csv", index=False)
    segments.to_csv(output_path / "merchant_segments.csv", index=False)
    importance.to_csv(output_path / "driver_feature_importance.csv", index=False)
    regressions.to_csv(output_path / "regression_summaries.csv", index=False)
    dashboard_data.to_csv(dashboard_path / "merchant_health_dashboard.csv", index=False)
    segments[
        [
            "seller_id",
            "seller_state",
            "seller_city",
            "segment",
            "health_score",
            "health_band",
            "dominant_issue",
            "recommended_action",
            "intervention_priority",
            "lifetime_gmv",
            "lifetime_orders",
        ]
    ].to_csv(dashboard_path / "merchant_interventions.csv", index=False)

    print("Pipeline complete")
    print(f"Merchant-month rows: {len(scored):,}")
    print(f"Merchants segmented: {segments['seller_id'].nunique():,}")
    print(f"Dashboard file: {dashboard_path / 'merchant_health_dashboard.csv'}")
    print(f"Interventions file: {dashboard_path / 'merchant_interventions.csv'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build merchant health analytics outputs.")
    parser.add_argument("--data-dir", default="Dataset")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--dashboard-dir", default="dashboard")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(args.data_dir, args.output_dir, args.dashboard_dir)

