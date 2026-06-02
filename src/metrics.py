from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


RAW_FILES = {
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

COMPONENT_COLUMNS = [
    "fulfillment_score",
    "satisfaction_score",
    "retention_score",
    "growth_score",
]

HEALTH_WEIGHTS = {
    "fulfillment_z": 0.30,
    "satisfaction_z": 0.30,
    "retention_z": 0.20,
    "growth_z": 0.20,
}


def load_olist_data(data_dir: str | Path = "Dataset") -> Dict[str, pd.DataFrame]:
    """Load the Olist CSV files used by the merchant health project."""
    data_path = Path(data_dir)
    data = {}

    for key, filename in RAW_FILES.items():
        path = data_path / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing required data file: {path}")
        data[key] = pd.read_csv(path)

    return data


def _mode_or_unknown(series: pd.Series) -> str:
    values = series.dropna()
    if values.empty:
        return "Unknown"
    return values.mode().iloc[0]


def _safe_percentile(series: pd.Series) -> pd.Series:
    if series.nunique(dropna=True) <= 1:
        return pd.Series(50.0, index=series.index)
    return series.rank(pct=True, method="average") * 100


def _standardize(df: pd.DataFrame, column: str, positive: bool = True) -> pd.Series:
    values = df[column].replace([np.inf, -np.inf], np.nan)
    fill_value = values.median()
    if pd.isna(fill_value):
        fill_value = 0

    filled = values.fillna(fill_value).to_frame()
    if filled[column].nunique(dropna=True) <= 1:
        z = pd.Series(0.0, index=df.index)
    else:
        z = pd.Series(
            StandardScaler().fit_transform(filled).ravel(),
            index=df.index,
        )

    return z if positive else -z


def build_order_seller_frame(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Create an order-seller grain table.

    Olist order reviews and customers live at the order grain, while products and
    sellers live at the order-item grain. Aggregating items to order-seller first
    avoids duplicating customer/review signals when an order has multiple items.
    """
    orders = data["orders"].copy()
    items = data["items"].copy()
    reviews = data["reviews"].copy()
    customers = data["customers"].copy()
    sellers = data["sellers"].copy()
    products = data["products"].copy()
    translation = data["category_translation"].copy()

    timestamp_cols = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for col in timestamp_cols:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")

    reviews = (
        reviews.groupby("order_id", as_index=False)
        .agg(
            review_score=("review_score", "mean"),
            review_count=("review_id", "nunique"),
        )
    )

    products = products.merge(
        translation,
        on="product_category_name",
        how="left",
    )
    products["product_category_name_english"] = products[
        "product_category_name_english"
    ].fillna(products["product_category_name"])

    items = items.merge(
        products[["product_id", "product_category_name_english"]],
        on="product_id",
        how="left",
    )

    order_seller = (
        items.groupby(["order_id", "seller_id"], as_index=False)
        .agg(
            gmv=("price", "sum"),
            freight_value=("freight_value", "sum"),
            item_count=("order_item_id", "count"),
            product_count=("product_id", "nunique"),
            primary_category=("product_category_name_english", _mode_or_unknown),
        )
    )

    df = (
        order_seller.merge(orders, on="order_id", how="left")
        .merge(reviews, on="order_id", how="left")
        .merge(
            customers[["customer_id", "customer_unique_id", "customer_state"]],
            on="customer_id",
            how="left",
        )
        .merge(
            sellers[["seller_id", "seller_city", "seller_state"]],
            on="seller_id",
            how="left",
        )
    )

    df["order_month"] = df["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    df = df.dropna(subset=["order_month", "seller_id"])

    df["is_delivered"] = (
        (df["order_status"] == "delivered")
        & df["order_delivered_customer_date"].notna()
    )
    df["delivery_days"] = (
        df["order_delivered_customer_date"] - df["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    df["delay_days"] = (
        df["order_delivered_customer_date"] - df["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400
    df["delay_days_clipped"] = df["delay_days"].clip(-30, 60)
    df["late_days"] = df["delay_days"].clip(lower=0)
    df["on_time_delivery"] = np.where(
        df["is_delivered"],
        df["delay_days"] <= 0,
        np.nan,
    )

    df["review_score"] = df["review_score"].clip(1, 5)
    has_review = df["review_score"].notna()
    df["good_review"] = np.where(has_review, df["review_score"] >= 4, np.nan)
    df["bad_review"] = np.where(has_review, df["review_score"] <= 2, np.nan)

    df = df.sort_values(["seller_id", "customer_unique_id", "order_purchase_timestamp"])
    df["customer_seller_order_number"] = (
        df.groupby(["seller_id", "customer_unique_id"]).cumcount() + 1
    )
    df["is_repeat_order"] = df["customer_seller_order_number"] > 1

    return df


def build_merchant_month_metrics(order_seller: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the order-seller table to the merchant-month grain."""
    monthly = (
        order_seller.groupby(["seller_id", "order_month"], as_index=False)
        .agg(
            seller_state=("seller_state", _mode_or_unknown),
            seller_city=("seller_city", _mode_or_unknown),
            primary_category=("primary_category", _mode_or_unknown),
            gmv=("gmv", "sum"),
            order_count=("order_id", "nunique"),
            unique_customers=("customer_unique_id", "nunique"),
            item_count=("item_count", "sum"),
            avg_order_value=("gmv", "mean"),
            avg_freight_value=("freight_value", "mean"),
            delivered_rate=("is_delivered", "mean"),
            on_time_rate=("on_time_delivery", "mean"),
            avg_delivery_days=("delivery_days", "mean"),
            avg_delay_days=("delay_days_clipped", "mean"),
            avg_late_days=("late_days", "mean"),
            avg_review_score=("review_score", "mean"),
            good_review_rate=("good_review", "mean"),
            bad_review_rate=("bad_review", "mean"),
            repeat_order_rate=("is_repeat_order", "mean"),
        )
    )

    monthly = monthly.sort_values(["seller_id", "order_month"]).reset_index(drop=True)
    monthly["order_month_str"] = monthly["order_month"].dt.strftime("%Y-%m")
    monthly["merchant_age_months"] = monthly.groupby("seller_id").cumcount() + 1

    monthly["log_gmv"] = np.log1p(monthly["gmv"])
    monthly["prev_log_gmv"] = monthly.groupby("seller_id")["log_gmv"].shift(1)
    monthly["gmv_momentum"] = (monthly["log_gmv"] - monthly["prev_log_gmv"]).clip(-2, 2)
    monthly["gmv_momentum"] = monthly["gmv_momentum"].fillna(0)

    monthly["log_order_count"] = np.log1p(monthly["order_count"])
    monthly["prev_log_order_count"] = monthly.groupby("seller_id")[
        "log_order_count"
    ].shift(1)
    monthly["order_momentum"] = (
        monthly["log_order_count"] - monthly["prev_log_order_count"]
    ).clip(-2, 2)
    monthly["order_momentum"] = monthly["order_momentum"].fillna(0)

    fill_zero_cols = [
        "avg_late_days",
        "avg_delay_days",
        "repeat_order_rate",
        "good_review_rate",
        "bad_review_rate",
    ]
    for col in fill_zero_cols:
        monthly[col] = monthly[col].fillna(0)

    return monthly


def score_merchant_months(monthly: pd.DataFrame) -> pd.DataFrame:
    """Compute health components and a 0-100 merchant health score."""
    scored = monthly.copy()

    scored["delivered_rate_z"] = _standardize(scored, "delivered_rate", positive=True)
    scored["on_time_rate_z"] = _standardize(scored, "on_time_rate", positive=True)
    scored["avg_late_days_z"] = _standardize(scored, "avg_late_days", positive=False)
    scored["avg_review_score_z"] = _standardize(
        scored, "avg_review_score", positive=True
    )
    scored["good_review_rate_z"] = _standardize(
        scored, "good_review_rate", positive=True
    )
    scored["repeat_order_rate_z"] = _standardize(
        scored, "repeat_order_rate", positive=True
    )
    scored["gmv_momentum_z"] = _standardize(scored, "gmv_momentum", positive=True)
    scored["order_momentum_z"] = _standardize(scored, "order_momentum", positive=True)

    scored["fulfillment_z"] = (
        0.35 * scored["delivered_rate_z"]
        + 0.35 * scored["on_time_rate_z"]
        + 0.30 * scored["avg_late_days_z"]
    )
    scored["satisfaction_z"] = (
        0.60 * scored["avg_review_score_z"] + 0.40 * scored["good_review_rate_z"]
    )
    scored["retention_z"] = scored["repeat_order_rate_z"]
    scored["growth_z"] = (
        0.70 * scored["gmv_momentum_z"] + 0.30 * scored["order_momentum_z"]
    )

    scored["health_z"] = sum(
        weight * scored[column] for column, weight in HEALTH_WEIGHTS.items()
    )

    scored["fulfillment_score"] = _safe_percentile(scored["fulfillment_z"])
    scored["satisfaction_score"] = _safe_percentile(scored["satisfaction_z"])
    scored["retention_score"] = _safe_percentile(scored["retention_z"])
    scored["growth_score"] = _safe_percentile(scored["growth_z"])
    scored["health_score"] = _safe_percentile(scored["health_z"])

    scored["health_band"] = pd.cut(
        scored["health_score"],
        bins=[0, 25, 50, 75, 100],
        labels=["At-Risk", "Watch", "Healthy", "Strong"],
        include_lowest=True,
    ).astype(str)

    scored = _add_driver_decomposition(scored)
    return scored


def _add_driver_decomposition(scored: pd.DataFrame) -> pd.DataFrame:
    scored = scored.sort_values(["seller_id", "order_month"]).copy()

    for col in COMPONENT_COLUMNS + ["health_score"]:
        scored[f"{col}_delta"] = scored.groupby("seller_id")[col].diff()

    delta_cols = [f"{col}_delta" for col in COMPONENT_COLUMNS]
    driver_labels = {
        "fulfillment_score_delta": "fulfillment",
        "satisfaction_score_delta": "satisfaction",
        "retention_score_delta": "retention",
        "growth_score_delta": "growth",
    }
    issue_labels = {
        "fulfillment_score": "fulfillment",
        "satisfaction_score": "satisfaction",
        "retention_score": "retention",
        "growth_score": "growth",
    }

    scored["health_drop_driver"] = scored[delta_cols].idxmin(axis=1).map(driver_labels)
    scored.loc[scored["health_score_delta"].fillna(0) >= 0, "health_drop_driver"] = (
        "no_decline"
    )
    scored["dominant_issue"] = scored[COMPONENT_COLUMNS].idxmin(axis=1).map(issue_labels)

    return scored


def latest_merchant_snapshot(scored: pd.DataFrame) -> pd.DataFrame:
    """Return one row per merchant with latest health and lifetime context."""
    idx = scored.groupby("seller_id")["order_month"].idxmax()
    latest = scored.loc[idx].copy()

    lifetime = (
        scored.groupby("seller_id", as_index=False)
        .agg(
            active_months=("order_month", "nunique"),
            lifetime_gmv=("gmv", "sum"),
            lifetime_orders=("order_count", "sum"),
            avg_health_score=("health_score", "mean"),
            avg_monthly_gmv=("gmv", "mean"),
        )
    )
    latest = latest.merge(lifetime, on="seller_id", how="left")
    latest["lifetime_gmv_log"] = np.log1p(latest["lifetime_gmv"])

    return latest
