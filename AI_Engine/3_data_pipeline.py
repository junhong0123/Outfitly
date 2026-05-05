"""Prepare Outfitly training artifacts and refresh demo database data.

Training artifacts are generated from the full H&M parquet files. Database
inserts are intentionally limited to a deduplicated storefront subset so the
MVC app stays usable.
"""

from __future__ import annotations

import argparse
import json
import numpy as np
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
PARQUET_DIR = PROJECT_ROOT / "wwwroot"
DATA_DIR = SCRIPT_DIR / "data"
ODBC_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=(localdb)\\mssqllocaldb;"
    "DATABASE=Outfitly;"
    "Trusted_Connection=yes;"
    "Encrypt=No;"
    "TrustServerCertificate=Yes;"
)


def normalize_text(value: object) -> str:
    """Clean text so duplicate products can be compared consistently."""
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def read_parquet(name: str) -> pd.DataFrame:
    """Load one H&M parquet file from the project wwwroot folder."""
    path = PARQUET_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing parquet file: {path}")
    return pd.read_parquet(path)


def get_engine():
    """Create a SQL Server database connection for the Outfitly LocalDB."""
    url = URL.create("mssql+pyodbc", query={"odbc_connect": ODBC_CONNECTION_STRING})
    return create_engine(url, fast_executemany=True)


def prepare_training_artifacts(
    articles: pd.DataFrame,
    transactions: pd.DataFrame,
    interaction_limit: int | None,
    seed: int,
) -> None:
    """Create CSV and pickle files used later by the two-tower model."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    articles = articles.drop_duplicates(subset=["article_id"], keep="first").copy()
    transaction_view = transactions[["customer_id", "article_id", "price"]]
    if interaction_limit is not None and len(transaction_view) > interaction_limit:
        transaction_view = transaction_view.sample(interaction_limit, random_state=seed)
        print(f"Training artifacts limited to {interaction_limit:,} sampled interactions.")

    article_ids = transaction_view["article_id"].astype("int64", copy=False)
    prices = transaction_view["price"].astype("float64", copy=False)

    price_by_article = prices.groupby(article_ids).median().mul(1000).clip(2, 500)
    product_prices = articles["article_id"].map(price_by_article).fillna(29.99)
    popularity_by_article = article_ids.value_counts()
    product_popularity = articles["article_id"].map(popularity_by_article).fillna(0)

    style_tags = articles[
        [
            "article_id",
            "colour_group_name",
            "graphical_appearance_name",
            "product_group_name",
            "index_group_name",
            "section_name",
            "garment_group_name",
        ]
    ].rename(columns={"article_id": "Id"})
    style_tags.to_csv(DATA_DIR / "style_tags.csv", index=False)

    item_source = pd.DataFrame(
        {
            "Id": articles["article_id"].astype(int),
            "Category": articles["product_type_name"].fillna("Unknown"),
            "Price": product_prices.astype(float),
            "Popularity": np.log1p(product_popularity.astype(float)),
            "colour_group_name": articles["colour_group_name"].fillna("Unknown"),
            "graphical_appearance_name": articles["graphical_appearance_name"].fillna("Unknown"),
            "product_group_name": articles["product_group_name"].fillna("Unknown"),
            "section_name": articles["section_name"].fillna("Unknown"),
            "garment_group_name": articles["garment_group_name"].fillna("Unknown"),
        }
    )

    item_le = LabelEncoder()
    cat_le = LabelEncoder()
    color_le = LabelEncoder()
    graphic_le = LabelEncoder()
    product_group_le = LabelEncoder()
    section_le = LabelEncoder()
    garment_group_le = LabelEncoder()
    price_scaler = MinMaxScaler()
    popularity_scaler = MinMaxScaler()

    item_source["ItemIndex"] = item_le.fit_transform(item_source["Id"])
    item_source["CategoryIdx"] = cat_le.fit_transform(item_source["Category"])
    item_source["ColorIdx"] = color_le.fit_transform(item_source["colour_group_name"])
    item_source["GraphicIdx"] = graphic_le.fit_transform(item_source["graphical_appearance_name"])
    item_source["ProductGroupIdx"] = product_group_le.fit_transform(item_source["product_group_name"])
    item_source["SectionIdx"] = section_le.fit_transform(item_source["section_name"])
    item_source["GarmentGroupIdx"] = garment_group_le.fit_transform(item_source["garment_group_name"])
    item_source["NormPrice"] = price_scaler.fit_transform(item_source[["Price"]].fillna(0))
    item_source["NormPopularity"] = popularity_scaler.fit_transform(item_source[["Popularity"]].fillna(0))

    user_agg = (
        transaction_view.groupby("customer_id", as_index=False, sort=False)["price"]
        .mean()
        .rename(columns={"customer_id": "UserId", "price": "AvgPurchasePrice"})
    )
    user_le = LabelEncoder()
    user_agg["UserId"] = user_agg["UserId"].astype("string")
    user_agg["UserIndex"] = user_le.fit_transform(user_agg["UserId"])
    user_price_scaler = MinMaxScaler()
    user_agg["NormAvgPrice"] = user_price_scaler.fit_transform(user_agg[["AvgPurchasePrice"]].fillna(0))

    train_data = transaction_view[["customer_id", "article_id"]].rename(
        columns={"customer_id": "UserId", "article_id": "ProductId"}
    )
    train_data["UserId"] = train_data["UserId"].astype("string")
    train_data["ProductId"] = train_data["ProductId"].astype("int64", copy=False)
    train_data["UserIndex"] = user_le.transform(train_data["UserId"])
    train_data["ItemIndex"] = item_le.transform(train_data["ProductId"])
    train_data = train_data[["UserIndex", "ItemIndex"]]

    item_source[
        [
            "ItemIndex",
            "Id",
            "CategoryIdx",
            "ColorIdx",
            "GraphicIdx",
            "ProductGroupIdx",
            "SectionIdx",
            "GarmentGroupIdx",
            "NormPrice",
            "NormPopularity",
        ]
    ].to_csv(
        DATA_DIR / "item_features.csv",
        index=False,
    )
    user_agg[["UserIndex", "UserId", "NormAvgPrice"]].to_csv(DATA_DIR / "user_features.csv", index=False)
    train_data.to_csv(DATA_DIR / "train_interactions.csv", index=False)

    encoders = {
        "item_le": item_le,
        "cat_le": cat_le,
        "color_le": color_le,
        "graphic_le": graphic_le,
        "product_group_le": product_group_le,
        "section_le": section_le,
        "garment_group_le": garment_group_le,
        "user_le": user_le,
        "price_scaler": price_scaler,
        "popularity_scaler": popularity_scaler,
        "user_price_scaler": user_price_scaler,
    }
    pd.to_pickle(encoders, DATA_DIR / "encoders.pkl")


def prepare_storefront_products(
    articles: pd.DataFrame,
    transactions: pd.DataFrame,
    limit: int,
) -> pd.DataFrame:
    """Build a small deduplicated product list for inserting into the website database."""
    purchase_counts = transactions["article_id"].astype(int).value_counts().rename("PurchaseCount")
    prices = transactions.groupby("article_id")["price"].median().mul(1000).clip(2, 500).rename("Price")

    products = articles.copy()
    products["Id"] = products["article_id"].astype(int)
    products["Name"] = products["prod_name"].fillna("Unknown")
    products["Description"] = products["detail_desc"].fillna("")
    products["Category"] = products["product_type_name"].fillna("Unknown")
    products["Price"] = products["Id"].map(prices).fillna(29.99).round(2)
    products["ImageUrls"] = ""
    products["AvailableColors"] = ""
    products["CreatedAt"] = datetime.now()
    products["PurchaseCount"] = products["Id"].map(purchase_counts).fillna(0).astype(int)
    products["_dedupe_key"] = (
        products["Name"].map(normalize_text)
        + "|"
        + products["Description"].map(normalize_text)
        + "|"
        + products["Category"].map(normalize_text)
    )
    products = products.sort_values(["PurchaseCount", "Id"], ascending=[False, True])
    products = products.drop_duplicates(subset=["_dedupe_key"], keep="first")
    products = products.head(limit)
    products[["Id"]].to_csv(DATA_DIR / "storefront_product_ids.csv", index=False)
    return products[["Id", "Name", "Description", "Category", "Price", "ImageUrls", "AvailableColors", "CreatedAt"]]


def prepare_storefront_users(transactions: pd.DataFrame, limit: int) -> pd.DataFrame:
    """Create demo ASP.NET Identity users from the most active H&M customers."""
    top_users = transactions["customer_id"].astype(str).value_counts().head(limit).index.to_series()
    users = pd.DataFrame({"Id": top_users.astype(str)})
    users["UserName"] = users["Id"]
    users["NormalizedUserName"] = users["UserName"].str.upper()
    users["Email"] = users["Id"].str[:16] + "@hm-import.local"
    users["NormalizedEmail"] = users["Email"].str.upper()
    users["EmailConfirmed"] = False
    users["PasswordHash"] = None
    users["SecurityStamp"] = [str(uuid.uuid4()) for _ in range(len(users))]
    users["ConcurrencyStamp"] = [str(uuid.uuid4()) for _ in range(len(users))]
    users["PhoneNumber"] = None
    users["PhoneNumberConfirmed"] = False
    users["TwoFactorEnabled"] = False
    users["LockoutEnd"] = None
    users["LockoutEnabled"] = True
    users["AccessFailedCount"] = 0
    return users


def prepare_storefront_interactions(
    transactions: pd.DataFrame,
    product_ids: set[int],
    user_ids: set[str],
    limit: int,
) -> pd.DataFrame:
    """Create purchase interaction rows only for users and products inserted into the website DB."""
    data = transactions[
        transactions["article_id"].astype(int).isin(product_ids)
        & transactions["customer_id"].astype(str).isin(user_ids)
    ].copy()
    data = data.head(limit)
    return pd.DataFrame(
        {
            "UserId": data["customer_id"].astype(str),
            "ProductId": data["article_id"].astype(int),
            "InteractionType": "Purchase",
            "Price": data["price"].astype(float),
            "Timestamp": pd.to_datetime(data["t_dat"]),
        }
    )


def execute_batches(df: pd.DataFrame, table: str, engine, batch_size: int, identity_insert: bool = False) -> None:
    """Insert a DataFrame into SQL Server in smaller batches to avoid memory/log issues."""
    for start in range(0, len(df), batch_size):
        batch = df.iloc[start : start + batch_size]
        with engine.begin() as conn:
            if identity_insert:
                conn.execute(text(f"SET IDENTITY_INSERT [{table}] ON"))
            batch.to_sql(table, conn, if_exists="append", index=False)
            if identity_insert:
                conn.execute(text(f"SET IDENTITY_INSERT [{table}] OFF"))


def prepare_database_for_large_refresh(engine) -> None:
    """Switch the database to simple recovery so large refreshes use less transaction log space."""
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("ALTER DATABASE [Outfitly] SET RECOVERY SIMPLE"))
        conn.execute(text("CHECKPOINT"))


def delete_table_rows(engine, table: str, batch_size: int) -> None:
    """Delete rows in batches so big tables can be cleared safely."""
    total = 0
    batches = 0
    while True:
        with engine.begin() as conn:
            result = conn.execute(text(f"DELETE TOP ({batch_size}) FROM [{table}]"))
            deleted = result.rowcount or 0
        total += deleted
        batches += 1
        if batches % 10 == 0:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(text("CHECKPOINT"))
        if deleted == 0:
            break
        if total % 100000 == 0:
            print(f"  deleted {total:,} rows from {table}")
    if total:
        print(f"  deleted {total:,} rows from {table}")


def ensure_user_interactions_table(engine) -> None:
    """Create UserInteractions if the app database does not already have it."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                IF OBJECT_ID(N'[dbo].[UserInteractions]', N'U') IS NULL
                CREATE TABLE [dbo].[UserInteractions] (
                    [Id] INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                    [UserId] NVARCHAR(450) NOT NULL,
                    [ProductId] INT NOT NULL,
                    [InteractionType] NVARCHAR(50) NOT NULL,
                    [Price] FLOAT NULL,
                    [Timestamp] DATETIME2 NULL
                )
                """
            )
        )


def reset_database(
    products: pd.DataFrame,
    users: pd.DataFrame,
    interactions: pd.DataFrame,
    transactions: pd.DataFrame,
    batch_size: int,
    sample_order_count: int,
) -> None:
    """Delete old demo data and insert fresh products, users, interactions, sizes, and orders."""
    engine = get_engine()
    prepare_database_for_large_refresh(engine)
    ensure_user_interactions_table(engine)
    inspector = inspect(engine)
    required = ["Products", "AspNetUsers", "Orders", "OrderItems", "ProductSizes"]
    missing = [table for table in required if not inspector.has_table(table)]
    if missing:
        raise RuntimeError(f"Missing database tables: {', '.join(missing)}")

    delete_order = [
        "AspNetUserTokens",
        "AspNetUserLogins",
        "AspNetUserClaims",
        "AspNetUserRoles",
        "CartItems",
        "SavedAddresses",
        "OrderItems",
        "Orders",
        "ProductSizes",
        "UserInteractions",
        "Products",
        "AspNetUsers",
    ]
    for table in delete_order:
        if inspector.has_table(table):
            delete_table_rows(engine, table, batch_size)

    execute_batches(products, "Products", engine, batch_size, identity_insert=True)
    execute_batches(users, "AspNetUsers", engine, batch_size)

    sizes = pd.DataFrame(
        [
            {"ProductId": int(product_id), "Size": size, "Quantity": quantity}
            for product_id in products["Id"]
            for size, quantity in [("S", 15), ("M", 20), ("L", 15)]
        ]
    )
    execute_batches(sizes, "ProductSizes", engine, batch_size)
    execute_batches(interactions, "UserInteractions", engine, batch_size)
    insert_sample_orders(engine, products, users, transactions, sample_order_count, batch_size)


def insert_sample_orders(engine, products: pd.DataFrame, users: pd.DataFrame, transactions: pd.DataFrame, count: int, batch_size: int) -> None:
    """Generate realistic sample Orders and OrderItems from imported purchase history."""
    product_lookup = products.set_index("Id")[["Name", "Price"]].to_dict("index")
    eligible = transactions[
        transactions["article_id"].astype(int).isin(product_lookup.keys())
        & transactions["customer_id"].astype(str).isin(set(users["Id"]))
    ].copy()
    if eligible.empty:
        return

    orders = []
    order_items = []
    statuses = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]
    now = datetime.now()
    order_id = 1
    item_id = 1
    for user_id, group in eligible.groupby("customer_id", sort=False):
        if len(orders) >= count:
            break
        item_rows = group.drop_duplicates(subset=["article_id"]).head(3)
        if item_rows.empty:
            continue
        status = statuses[len(orders) % len(statuses)]
        subtotal = 0.0
        order_number = f"SEED-{now.strftime('%Y%m%d')}-{order_id:04d}"
        order_date = now - timedelta(days=len(orders) % 45)
        for _, row in item_rows.iterrows():
            product_id = int(row["article_id"])
            product = product_lookup[product_id]
            quantity = 1 + (item_id % 2)
            price = float(product["Price"])
            subtotal += price * quantity
            order_items.append(
                {
                    "Id": item_id,
                    "OrderId": order_id,
                    "ProductId": product_id,
                    "ProductName": product["Name"],
                    "Price": price,
                    "Quantity": quantity,
                    "Color": None,
                    "Size": "M",
                    "ImageUrl": None,
                }
            )
            item_id += 1

        shipping = 0.0 if subtotal >= 100 else 10.0
        tax = round(subtotal * 0.10, 2)
        total = round(subtotal + shipping + tax, 2)
        orders.append(
            {
                "Id": order_id,
                "OrderNumber": order_number,
                "OrderDate": order_date,
                "CustomerId": str(user_id),
                "CustomerName": f"Imported Customer {order_id}",
                "CustomerEmail": f"{str(user_id)[:16]}@hm-import.local",
                "ShippingAddressLine1": f"{100 + order_id} Market Street",
                "ShippingAddressLine2": None,
                "ShippingCity": "Kuala Lumpur",
                "ShippingState": "Wilayah Persekutuan",
                "ShippingZipCode": "50000",
                "ShippingCountry": "Malaysia",
                "PaymentMethod": "card",
                "TransactionId": str(uuid.uuid4()),
                "Subtotal": round(subtotal, 2),
                "ShippingCost": shipping,
                "Tax": tax,
                "Discount": 0.0,
                "Total": total,
                "Status": status,
                "ShippedDate": order_date + timedelta(days=1) if status in {"Shipped", "Delivered"} else None,
                "DeliveredDate": order_date + timedelta(days=4) if status == "Delivered" else None,
                "TrackingNumber": f"TRK{order_id:09d}" if status in {"Shipped", "Delivered"} else None,
            }
        )
        order_id += 1

    if not orders:
        return
    execute_batches(pd.DataFrame(orders), "Orders", engine, batch_size, identity_insert=True)
    execute_batches(pd.DataFrame(order_items), "OrderItems", engine, batch_size, identity_insert=True)


def parse_args() -> argparse.Namespace:
    """Read command-line options for data preparation and optional DB refresh."""
    parser = argparse.ArgumentParser(description="Prepare Outfitly data")
    parser.add_argument("--execute", action="store_true", help="Actually reset and insert database data")
    parser.add_argument("--skip-training-artifacts", action="store_true")
    parser.add_argument(
        "--training-interaction-limit",
        type=int,
        default=1000000,
        help="Number of sampled interactions to use for training artifacts. Use 0 for all 31M rows.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--storefront-product-limit", type=int, default=3000)
    parser.add_argument("--storefront-user-limit", type=int, default=1000)
    parser.add_argument("--storefront-interaction-limit", type=int, default=100000)
    parser.add_argument("--sample-order-count", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=5000)
    return parser.parse_args()


def main() -> None:
    """Run the full data preparation workflow from parquet files to optional DB insert."""
    args = parse_args()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading parquet data...")
    articles = read_parquet("articles.parquet")
    customers = read_parquet("customers.parquet")
    transactions = read_parquet("transactions_train.parquet")
    print(
        json.dumps(
            {
                "articles": len(articles),
                "customers": len(customers),
                "transactions": len(transactions),
            },
            indent=2,
        )
    )

    if not args.skip_training_artifacts:
        print("Writing full training artifacts...")
        training_limit = None if args.training_interaction_limit == 0 else args.training_interaction_limit
        prepare_training_artifacts(articles, transactions, training_limit, args.seed)

    print("Preparing deduplicated storefront subset...")
    products = prepare_storefront_products(articles, transactions, args.storefront_product_limit)
    users = prepare_storefront_users(transactions, args.storefront_user_limit)
    interactions = prepare_storefront_interactions(
        transactions,
        set(products["Id"].astype(int)),
        set(users["Id"].astype(str)),
        args.storefront_interaction_limit,
    )
    print(
        json.dumps(
            {
                "db_products": len(products),
                "db_users": len(users),
                "db_interactions": len(interactions),
                "sample_orders": args.sample_order_count,
                "execute": args.execute,
            },
            indent=2,
        )
    )

    if args.execute:
        reset_database(products, users, interactions, transactions, args.batch_size, args.sample_order_count)
        print("Database reset and seed complete.")
    else:
        print("Dry run complete. Re-run with --execute to reset database data.")


if __name__ == "__main__":
    main()
