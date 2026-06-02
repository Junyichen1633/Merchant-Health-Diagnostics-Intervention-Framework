# Data

This project uses the public Olist Brazilian E-commerce dataset from Kaggle.

Raw CSV files are intentionally not committed to GitHub. To reproduce the project:

1. Download the Olist dataset from Kaggle.
2. Place the CSV files in this `Dataset/` directory.
3. Run:

```bash
python3 src/run_pipeline.py
```

Required files:

- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_order_reviews_dataset.csv`
- `olist_customers_dataset.csv`
- `olist_sellers_dataset.csv`
- `olist_products_dataset.csv`
- `product_category_name_translation.csv`

