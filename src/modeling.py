from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

try:
    from .metrics import COMPONENT_COLUMNS, latest_merchant_snapshot
except ImportError:  # Allows `python src/run_pipeline.py`.
    from metrics import COMPONENT_COLUMNS, latest_merchant_snapshot


ACTION_MAP: Dict[str, str] = {
    "fulfillment": "Offer shipping diagnostics, carrier SLA monitoring, and fulfillment workflow guidance.",
    "satisfaction": "Audit product quality, listing accuracy, and post-purchase support for low-review merchants.",
    "retention": "Recommend retention tools such as win-back offers, email campaigns, and loyalty incentives.",
    "growth": "Recommend merchandising and demand-generation support to rebuild GMV momentum.",
}

EVALUATION_METHOD = (
    "30-day post-intervention readout with matched historical controls or a "
    "staggered rollout holdout when product traffic allows."
)


def segment_merchants(scored: pd.DataFrame, n_clusters: int = 5) -> pd.DataFrame:
    """Cluster merchants and attach business-readable segment labels."""
    latest = latest_merchant_snapshot(scored)

    feature_cols = [
        "health_score",
        "fulfillment_score",
        "satisfaction_score",
        "retention_score",
        "growth_score",
        "lifetime_gmv_log",
        "active_months",
        "lifetime_orders",
        "avg_late_days",
        "avg_review_score",
        "repeat_order_rate",
        "gmv_momentum",
    ]

    features = latest[feature_cols].replace([np.inf, -np.inf], np.nan)
    features = features.fillna(features.median(numeric_only=True)).fillna(0)

    cluster_count = min(n_clusters, max(2, len(latest) // 50))
    scaled = StandardScaler().fit_transform(features)
    kmeans = KMeans(n_clusters=cluster_count, random_state=42, n_init=20)
    latest["cluster_id"] = kmeans.fit_predict(scaled)

    cluster_labels = _label_clusters(latest)
    latest["segment"] = latest["cluster_id"].map(cluster_labels)
    latest["recommended_action"] = latest.apply(_recommend_action, axis=1)
    latest["intervention_priority"] = latest.apply(_priority, axis=1)

    return latest


def _label_clusters(latest: pd.DataFrame) -> Dict[int, str]:
    centroids = (
        latest.groupby("cluster_id")
        .agg(
            health_score=("health_score", "mean"),
            fulfillment_score=("fulfillment_score", "mean"),
            satisfaction_score=("satisfaction_score", "mean"),
            retention_score=("retention_score", "mean"),
            growth_score=("growth_score", "mean"),
            lifetime_gmv=("lifetime_gmv", "median"),
        )
        .reset_index()
    )
    gmv_median = latest["lifetime_gmv"].median()

    labels = {}
    for row in centroids.itertuples(index=False):
        if row.health_score >= 70 and row.lifetime_gmv >= gmv_median:
            label = "Champions"
        elif row.growth_score >= 65 and row.health_score >= 55:
            label = "Rising Stars"
        elif row.fulfillment_score <= 40:
            label = "Logistics Issue"
        elif row.satisfaction_score <= 40:
            label = "Review Risk"
        elif row.health_score <= 40:
            label = "At-Risk"
        else:
            label = "Stable Core"
        labels[row.cluster_id] = label

    return labels


def _recommend_action(row: pd.Series) -> str:
    if row["health_score"] >= 75:
        return "Nurture with growth experiments and use as a benchmark cohort."

    driver = row.get("dominant_issue", "growth")
    return ACTION_MAP.get(driver, ACTION_MAP["growth"])


def _priority(row: pd.Series) -> str:
    if row["health_score"] < 25 or row.get("health_score_delta", 0) <= -20:
        return "High"
    if row["health_score"] < 50 or row.get("health_score_delta", 0) <= -10:
        return "Medium"
    return "Low"


def build_dashboard_dataset(scored: pd.DataFrame, segments: pd.DataFrame) -> pd.DataFrame:
    """Attach latest segment/action context to every merchant-month row."""
    segment_cols = [
        "seller_id",
        "cluster_id",
        "segment",
        "recommended_action",
        "intervention_priority",
        "active_months",
        "lifetime_gmv",
        "lifetime_orders",
    ]
    segment_context = segments[segment_cols].rename(
        columns={
            "recommended_action": "latest_recommended_action",
            "intervention_priority": "latest_intervention_priority",
        }
    )
    dashboard = scored.merge(segment_context, on="seller_id", how="left")
    dashboard["recommended_action"] = dashboard.apply(_recommend_action, axis=1)
    dashboard["intervention_priority"] = dashboard.apply(_priority, axis=1)

    return dashboard


def feature_importance(scored: pd.DataFrame) -> pd.DataFrame:
    """Estimate non-linear driver importance for the health score."""
    feature_cols = [
        "delivered_rate",
        "on_time_rate",
        "avg_late_days",
        "avg_review_score",
        "good_review_rate",
        "repeat_order_rate",
        "gmv_momentum",
        "order_momentum",
        "log_gmv",
        "order_count",
    ]

    model_df = scored[feature_cols + ["health_score"]].replace([np.inf, -np.inf], np.nan)
    model_df = model_df.fillna(model_df.median(numeric_only=True)).fillna(0)

    forest = RandomForestRegressor(
        n_estimators=300,
        min_samples_leaf=20,
        random_state=42,
        n_jobs=-1,
    )
    forest.fit(model_df[feature_cols], model_df["health_score"])

    return (
        pd.DataFrame(
            {
                "feature": feature_cols,
                "importance": forest.feature_importances_,
            }
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def regression_summaries(scored: pd.DataFrame) -> pd.DataFrame:
    """
    Run driver models for product hypotheses.

    These are observational models, not causal proof. They are meant to quantify
    directional product hypotheses after controlling for merchant size, category,
    and month fixed effects.
    """
    df = scored.copy()
    df = df[df["order_count"] >= 3].copy()
    df["category_group"] = _top_category_bucket(df)
    df["month"] = pd.to_datetime(df["order_month"]).dt.strftime("%Y-%m")

    formulas = {
        "H1_review_delay": (
            "avg_review_score ~ avg_late_days + np.log1p(gmv) + "
            "np.log1p(order_count) + C(category_group) + C(month)"
        ),
        "H2_repeat_review_delay": (
            "repeat_order_rate ~ avg_late_days + avg_review_score + "
            "np.log1p(gmv) + np.log1p(order_count) + C(category_group) + C(month)"
        ),
        "Health_driver_model": (
            "health_score ~ avg_late_days + avg_review_score + repeat_order_rate + "
            "gmv_momentum + np.log1p(gmv) + np.log1p(order_count) + "
            "C(category_group) + C(month)"
        ),
    }

    terms_to_keep = {
        "avg_late_days",
        "avg_review_score",
        "repeat_order_rate",
        "gmv_momentum",
        "np.log1p(gmv)",
        "np.log1p(order_count)",
    }

    rows = []
    for model_name, formula in formulas.items():
        model_df = df.dropna(
            subset=[
                "avg_late_days",
                "avg_review_score",
                "repeat_order_rate",
                "gmv",
                "order_count",
                "gmv_momentum",
                "category_group",
                "month",
            ]
        )
        result = smf.ols(formula=formula, data=model_df).fit(cov_type="HC3")

        for term in result.params.index:
            if term not in terms_to_keep:
                continue
            rows.append(
                {
                    "model": model_name,
                    "term": term,
                    "coefficient": result.params[term],
                    "std_error": result.bse[term],
                    "p_value": result.pvalues[term],
                    "n_obs": int(result.nobs),
                    "r_squared": result.rsquared,
                    "interpretation": _interpret_term(model_name, term, result.params[term]),
                }
            )

    return pd.DataFrame(rows)


def intervention_evaluation(
    scored: pd.DataFrame,
    segments: pd.DataFrame,
    regressions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build a 30-day intervention evaluation plan.

    Olist does not contain real intervention assignments, so this is a
    counterfactual planning layer. The estimated lift uses the observational
    health-driver model and bounded product assumptions; the recommended readout
    is a matched-control or staggered-rollout measurement.
    """
    del scored  # The latest segment snapshot already carries the baseline metrics.

    coeffs = (
        regressions[regressions["model"] == "Health_driver_model"]
        .set_index("term")["coefficient"]
        .to_dict()
    )

    rows = []
    for row in segments.itertuples(index=False):
        deltas = _intervention_metric_deltas(row)
        raw_lift = _expected_health_lift(deltas, coeffs)
        expected_lift = float(np.clip(raw_lift, 0, _lift_cap(row.intervention_priority)))
        expected_health = float(np.clip(row.health_score + expected_lift, 0, 100))

        rows.append(
            {
                "seller_id": row.seller_id,
                "segment": row.segment,
                "intervention_priority": row.intervention_priority,
                "dominant_issue": row.dominant_issue,
                "recommended_action": row.recommended_action,
                "baseline_health_score": row.health_score,
                "expected_30d_health_lift": expected_lift,
                "expected_30d_health_score": expected_health,
                "target_metric": deltas["target_metric"],
                "target_metric_delta_30d": deltas["target_metric_delta_30d"],
                "avg_late_days_delta": deltas["avg_late_days"],
                "avg_review_score_delta": deltas["avg_review_score"],
                "repeat_order_rate_delta": deltas["repeat_order_rate"],
                "gmv_momentum_delta": deltas["gmv_momentum"],
                "measurement_window_days": 30,
                "success_metric": "30-day health score lift versus matched controls",
                "guardrail_metric": _guardrail_metric(row.dominant_issue),
                "evaluation_method": EVALUATION_METHOD,
                "lifetime_gmv": row.lifetime_gmv,
                "lifetime_orders": row.lifetime_orders,
            }
        )

    plan = pd.DataFrame(rows)
    plan["_priority_rank"] = plan["intervention_priority"].map(
        {"High": 0, "Medium": 1, "Low": 2}
    ).fillna(3)
    plan = plan.sort_values(
        ["_priority_rank", "expected_30d_health_lift", "baseline_health_score"],
        ascending=[True, False, True],
    ).drop(columns="_priority_rank")

    summary = (
        plan.groupby(["dominant_issue", "intervention_priority"], as_index=False)
        .agg(
            merchants=("seller_id", "nunique"),
            avg_baseline_health=("baseline_health_score", "mean"),
            avg_expected_30d_lift=("expected_30d_health_lift", "mean"),
            median_expected_30d_health=("expected_30d_health_score", "median"),
            gmv_in_scope=("lifetime_gmv", "sum"),
        )
    )
    summary["_priority_rank"] = summary["intervention_priority"].map(
        {"High": 0, "Medium": 1, "Low": 2}
    ).fillna(3)
    summary = summary.sort_values(
        ["_priority_rank", "avg_expected_30d_lift"],
        ascending=[True, False],
    ).drop(columns="_priority_rank")
    summary["evaluation_method"] = EVALUATION_METHOD

    return plan, summary


def _top_category_bucket(df: pd.DataFrame, top_n: int = 10) -> pd.Series:
    top_categories = df["primary_category"].value_counts().head(top_n).index
    return df["primary_category"].where(df["primary_category"].isin(top_categories), "Other")


def _interpret_term(model_name: str, term: str, coefficient: float) -> str:
    if model_name == "H1_review_delay" and term == "avg_late_days":
        return f"One more late day is associated with {coefficient:.3f} review-score points."
    if model_name == "H2_repeat_review_delay" and term == "avg_late_days":
        return f"One more late day is associated with {100 * coefficient:.2f} percentage points of repeat rate."
    if model_name == "H2_repeat_review_delay" and term == "avg_review_score":
        return f"One additional review-score point is associated with {100 * coefficient:.2f} percentage points of repeat rate."
    if model_name == "Health_driver_model" and term == "avg_late_days":
        return f"One more late day is associated with {coefficient:.2f} health-score points."
    if model_name == "Health_driver_model" and term == "avg_review_score":
        return f"One additional review-score point is associated with {coefficient:.2f} health-score points."
    return "Control or supporting driver estimate."


def _intervention_metric_deltas(row: pd.Series) -> dict[str, float | str]:
    intensity = _priority_multiplier(row.intervention_priority)
    issue = row.dominant_issue

    deltas: dict[str, float | str] = {
        "target_metric": "health_score",
        "target_metric_delta_30d": 0.0,
        "avg_late_days": 0.0,
        "avg_review_score": 0.0,
        "repeat_order_rate": 0.0,
        "gmv_momentum": 0.0,
    }

    if issue == "fulfillment":
        current_late_days = _safe_value(row, "avg_late_days")
        late_reduction = min(max(current_late_days * 0.30, 0.25), 2.0) * intensity
        if current_late_days <= 0:
            late_reduction = 0.0
        review_lift = min(0.06 * intensity, max(0.0, 5 - _safe_value(row, "avg_review_score")))
        deltas.update(
            {
                "target_metric": "avg_late_days",
                "target_metric_delta_30d": -late_reduction,
                "avg_late_days": -late_reduction,
                "avg_review_score": review_lift,
            }
        )
    elif issue == "satisfaction":
        review_lift = min(0.25 * intensity, max(0.0, 5 - _safe_value(row, "avg_review_score")))
        deltas.update(
            {
                "target_metric": "avg_review_score",
                "target_metric_delta_30d": review_lift,
                "avg_review_score": review_lift,
            }
        )
    elif issue == "retention":
        repeat_lift = min(0.015 * intensity, max(0.0, 1 - _safe_value(row, "repeat_order_rate")))
        deltas.update(
            {
                "target_metric": "repeat_order_rate",
                "target_metric_delta_30d": repeat_lift,
                "repeat_order_rate": repeat_lift,
            }
        )
    else:
        momentum_lift = 0.12 * intensity
        deltas.update(
            {
                "target_metric": "gmv_momentum",
                "target_metric_delta_30d": momentum_lift,
                "gmv_momentum": momentum_lift,
            }
        )

    return deltas


def _expected_health_lift(deltas: dict[str, float | str], coeffs: dict[str, float]) -> float:
    term_map = {
        "avg_late_days": "avg_late_days",
        "avg_review_score": "avg_review_score",
        "repeat_order_rate": "repeat_order_rate",
        "gmv_momentum": "gmv_momentum",
    }
    lift = 0.0
    for delta_key, term in term_map.items():
        lift += float(deltas[delta_key]) * coeffs.get(term, 0.0)
    return lift


def _priority_multiplier(priority: str) -> float:
    return {"High": 1.00, "Medium": 0.65, "Low": 0.35}.get(priority, 0.50)


def _lift_cap(priority: str) -> float:
    return {"High": 18.0, "Medium": 12.0, "Low": 7.0}.get(priority, 10.0)


def _safe_value(row: pd.Series, field: str) -> float:
    value = getattr(row, field, 0.0)
    if pd.isna(value):
        return 0.0
    return float(value)


def _guardrail_metric(issue: str) -> str:
    return {
        "fulfillment": "review score and cancellation/delivery failures",
        "satisfaction": "return/refund pressure and review volume",
        "retention": "discount cost and unsubscribed buyers",
        "growth": "margin quality and support contact rate",
    }.get(issue, "merchant support contact rate")
