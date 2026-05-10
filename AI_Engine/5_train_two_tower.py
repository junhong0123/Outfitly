"""Train the Outfitly two-tower retrieval model.

This script uses in-batch negatives instead of random one-by-one negatives.
It generally gives better retrieval quality and avoids recommending accidental
positive items as negatives during training.
"""

from __future__ import annotations

import argparse
import shutil
import importlib.util
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, Subset


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

USER_FLOAT_COLUMNS = [
    ("user_norm_price", "NormAvgPrice"),
    ("user_norm_age", "NormAge"),
    ("user_fn", "FNFlag"),
    ("user_active", "ActiveFlag"),
    ("user_norm_purchase_count", "NormPurchaseCount"),
    ("user_norm_unique_item_count", "NormUniqueItemCount"),
    ("user_norm_avg_item_popularity", "NormAvgItemPopularity"),
]
USER_LONG_COLUMNS = [
    ("user_club_status", "ClubStatusIdx"),
    ("user_fashion_frequency", "FashionFrequencyIdx"),
    ("user_recent_category", "RecentCategoryIdx"),
    ("user_recent_color", "RecentColorIdx"),
    ("user_recent_product_group", "RecentProductGroupIdx"),
    ("user_recent_section", "RecentSectionIdx"),
    ("user_recent_garment_group", "RecentGarmentGroupIdx"),
    ("user_recent_sales_channel", "RecentSalesChannelIdx"),
]


def _load_two_tower_model_class():
    """Load TwoTowerModel from 4_modeling.py even though the filename starts with a number."""
    module_path = SCRIPT_DIR / "4_modeling.py"
    spec = importlib.util.spec_from_file_location("outfitly_modeling", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load model module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TwoTowerModel


TwoTowerModel = _load_two_tower_model_class()


@dataclass
class ModelConfig:
    emb_dim: int = 64
    out_dim: int = 128
    hidden_dim: int = 256
    tag_emb_dim: int = 32
    dropout: float = 0.1


class PositivePairDataset(Dataset):
    def __init__(
        self,
        interactions: pd.DataFrame,
        user_features: pd.DataFrame,
        item_features: pd.DataFrame,
    ) -> None:
        """Store positive user-item purchases and lookup features for fast training batches."""
        self.user_idx = torch.tensor(interactions["UserIndex"].to_numpy(), dtype=torch.long)
        self.item_idx = torch.tensor(interactions["ItemIndex"].to_numpy(), dtype=torch.long)

        max_user_idx = int(user_features["UserIndex"].max())
        self.user_price = torch.zeros(max_user_idx + 1, dtype=torch.float32)
        self.user_price[
            torch.tensor(user_features["UserIndex"].to_numpy(), dtype=torch.long)
        ] = torch.tensor(user_features["NormAvgPrice"].to_numpy(), dtype=torch.float32)
        self.user_float_features: dict[str, torch.Tensor] = {"user_norm_price": self.user_price}
        self.user_long_features: dict[str, torch.Tensor] = {}
        user_indices = torch.tensor(user_features["UserIndex"].to_numpy(), dtype=torch.long)
        for key, column in USER_FLOAT_COLUMNS:
            if key == "user_norm_price":
                continue
            values = torch.zeros(max_user_idx + 1, dtype=torch.float32)
            if column in user_features:
                values[user_indices] = torch.tensor(user_features[column].fillna(0).to_numpy(), dtype=torch.float32)
            self.user_float_features[key] = values
        for key, column in USER_LONG_COLUMNS:
            values = torch.zeros(max_user_idx + 1, dtype=torch.long)
            if column in user_features:
                values[user_indices] = torch.tensor(user_features[column].fillna(0).to_numpy(), dtype=torch.long)
            self.user_long_features[key] = values

        max_item_idx = int(item_features["ItemIndex"].max())
        self.item_cat = torch.zeros(max_item_idx + 1, dtype=torch.long)
        self.item_color = torch.zeros(max_item_idx + 1, dtype=torch.long)
        self.item_graphic = torch.zeros(max_item_idx + 1, dtype=torch.long)
        self.item_product_group = torch.zeros(max_item_idx + 1, dtype=torch.long)
        self.item_section = torch.zeros(max_item_idx + 1, dtype=torch.long)
        self.item_garment_group = torch.zeros(max_item_idx + 1, dtype=torch.long)
        self.item_price = torch.zeros(max_item_idx + 1, dtype=torch.float32)
        self.item_popularity = torch.zeros(max_item_idx + 1, dtype=torch.float32)

        item_indices = torch.tensor(item_features["ItemIndex"].to_numpy(), dtype=torch.long)
        self.item_cat[item_indices] = torch.tensor(item_features["CategoryIdx"].to_numpy(), dtype=torch.long)
        self.item_color[item_indices] = torch.tensor(item_features["ColorIdx"].to_numpy(), dtype=torch.long)
        self.item_graphic[item_indices] = torch.tensor(item_features["GraphicIdx"].to_numpy(), dtype=torch.long)
        if "ProductGroupIdx" in item_features:
            self.item_product_group[item_indices] = torch.tensor(
                item_features["ProductGroupIdx"].to_numpy(),
                dtype=torch.long,
            )
        if "SectionIdx" in item_features:
            self.item_section[item_indices] = torch.tensor(item_features["SectionIdx"].to_numpy(), dtype=torch.long)
        if "GarmentGroupIdx" in item_features:
            self.item_garment_group[item_indices] = torch.tensor(
                item_features["GarmentGroupIdx"].to_numpy(),
                dtype=torch.long,
            )
        self.item_price[item_indices] = torch.tensor(item_features["NormPrice"].to_numpy(), dtype=torch.float32)
        if "NormPopularity" in item_features:
            self.item_popularity[item_indices] = torch.tensor(
                item_features["NormPopularity"].to_numpy(),
                dtype=torch.float32,
            )

    def __len__(self) -> int:
        """Return how many positive purchase pairs are available."""
        return len(self.user_idx)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        """Return one training example with user features and item features."""
        user_idx = self.user_idx[index]
        item_idx = self.item_idx[index]
        example = {
            "user_idx": user_idx,
            "user_norm_price": self.user_price[user_idx],
            "item_idx": item_idx,
            "item_cat": self.item_cat[item_idx],
            "item_color": self.item_color[item_idx],
            "item_graphic": self.item_graphic[item_idx],
            "item_product_group": self.item_product_group[item_idx],
            "item_section": self.item_section[item_idx],
            "item_garment_group": self.item_garment_group[item_idx],
            "item_norm_price": self.item_price[item_idx],
            "item_popularity": self.item_popularity[item_idx],
        }
        for key, values in self.user_float_features.items():
            if key != "user_norm_price":
                example[key] = values[user_idx]
        for key, values in self.user_long_features.items():
            example[key] = values[user_idx]
        return example


def parse_args() -> argparse.Namespace:
    """Read command-line options for model training."""
    parser = argparse.ArgumentParser(description="Train Outfitly two-tower model")
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--max-interactions", type=int, default=0, help="0 means use all prepared interactions")
    parser.add_argument("--validation-ratio", type=float, default=0.05)
    parser.add_argument("--min-user-interactions", type=int, default=3)
    parser.add_argument("--min-item-interactions", type=int, default=5)
    parser.add_argument(
        "--validation-strategy",
        choices=["user-holdout", "random", "temporal"],
        default="temporal",
        help="Hold out purchases from users that remain represented in training.",
    )
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--output", default=str(DATA_DIR / "two_tower_model.pth"))
    parser.add_argument("--checkpoint-dir", default=str(DATA_DIR / "checkpoints"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--temperature", type=float, default=0.10)
    parser.add_argument("--recall-k", type=int, default=10, help="Legacy single Recall@K value.")
    parser.add_argument(
        "--recall-ks",
        default="10,50,100",
        help="Comma-separated Recall@K values to calculate after each epoch. Use 0 to disable.",
    )
    parser.add_argument(
        "--map-ks",
        default="12",
        help="Comma-separated MAP@K values to calculate after each epoch. Use 0 to disable.",
    )
    parser.add_argument(
        "--recall-batch-size",
        type=int,
        default=128,
        help="Validation batch size used for Recall@K scoring against all items.",
    )
    parser.add_argument(
        "--max-metric-validation-pairs",
        type=int,
        default=50000,
        help="Maximum validation rows used for expensive Recall/MAP metrics. Use 0 for all rows.",
    )
    parser.add_argument(
        "--max-validation-loss-pairs",
        type=int,
        default=100000,
        help="Maximum validation rows used for validation loss. Use 0 for all rows.",
    )
    parser.add_argument(
        "--selection-metric",
        default="storefront_recall@10",
        help="Metric used to save the best checkpoint. Use validation_loss or a recall metric like storefront_recall@10.",
    )
    parser.add_argument(
        "--popularity-rerank-weight",
        type=float,
        default=0.80,
        help="Weight added to candidate scores from normalized item popularity during Recall@K reranking.",
    )
    parser.add_argument(
        "--rerank-candidate-pool",
        type=int,
        default=3000,
        help="Number of two-tower candidates to rerank with popularity before computing top K.",
    )
    parser.add_argument(
        "--early-stopping-patience",
        type=int,
        default=3,
        help="Stop training after this many epochs without validation improvement. Use 0 to disable.",
    )
    parser.add_argument(
        "--min-delta",
        type=float,
        default=0.001,
        help="Minimum validation loss improvement required to reset early stopping.",
    )
    parser.add_argument("--amp", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--hard-negative-count", type=int, default=128)
    parser.add_argument("--hard-negative-pool-size", type=int, default=4096)
    return parser.parse_args()


def parse_recall_ks(value: str | None, fallback_k: int) -> list[int]:
    """Convert a comma-separated K list like '10,50,100' into sorted integer values."""
    if value is None:
        return [fallback_k] if fallback_k > 0 else []
    cleaned = value.strip().lower()
    if cleaned in {"", "0", "none", "off", "false"}:
        return []
    recall_ks = sorted({int(part.strip()) for part in cleaned.split(",") if part.strip()})
    return [k for k in recall_ks if k > 0]


def parse_metric_ks(value: str | None) -> list[int]:
    """Convert a comma-separated K list like '12' into sorted integer values."""
    if value is None:
        return []
    cleaned = value.strip().lower()
    if cleaned in {"", "0", "none", "off", "false"}:
        return []
    metric_ks = sorted({int(part.strip()) for part in cleaned.split(",") if part.strip()})
    return [k for k in metric_ks if k > 0]


def move_batch(batch: dict[str, torch.Tensor], device: torch.device) -> dict[str, torch.Tensor]:
    """Move every tensor in a training batch to CPU or GPU."""
    return {key: value.to(device, non_blocking=True) for key, value in batch.items()}


def optional_feature_count(item_features: pd.DataFrame, column: str) -> int | None:
    """Return the number of encoded values for an optional item feature column."""
    if column not in item_features:
        return None
    return int(item_features[column].max()) + 1


def scale_series(values: pd.Series) -> pd.Series:
    """Min-max scale a numeric series, returning zeros for constant input."""
    values = values.astype(float).fillna(0)
    minimum = float(values.min()) if len(values) else 0.0
    maximum = float(values.max()) if len(values) else 0.0
    if maximum <= minimum:
        return pd.Series(0.0, index=values.index)
    return (values - minimum) / (maximum - minimum)


def build_training_user_features(
    user_features: pd.DataFrame,
    interactions: pd.DataFrame,
    train_indices: list[int],
    item_features: pd.DataFrame,
) -> pd.DataFrame:
    """Recompute history-derived user features from train rows only to avoid validation leakage."""
    features = user_features.copy()
    user_index = features["UserIndex"].astype(int)

    dynamic_float_columns = [
        "NormAvgPrice",
        "NormPurchaseCount",
        "NormUniqueItemCount",
        "NormAvgItemPopularity",
    ]
    dynamic_long_columns = [
        "RecentCategoryIdx",
        "RecentColorIdx",
        "RecentProductGroupIdx",
        "RecentSectionIdx",
        "RecentGarmentGroupIdx",
        "RecentSalesChannelIdx",
    ]
    for column in dynamic_float_columns:
        if column in features:
            features[column] = 0.0
    for column in dynamic_long_columns:
        if column in features:
            features[column] = 0

    if not train_indices:
        return features

    history = interactions.iloc[train_indices].copy()
    if history.empty:
        return features

    history["UserIndex"] = history["UserIndex"].astype(int)
    history["ItemIndex"] = history["ItemIndex"].astype(int)
    user_to_row = pd.Series(features.index.to_numpy(), index=user_index)

    if "Price" in history and "NormAvgPrice" in features:
        avg_price = history.groupby("UserIndex", sort=False)["Price"].mean()
        scaled_price = scale_series(avg_price)
        rows = avg_price.index.map(user_to_row).dropna().astype(int)
        features.loc[rows, "NormAvgPrice"] = scaled_price.loc[avg_price.index].to_numpy()

    purchase_count = history.groupby("UserIndex", sort=False).size()
    if "NormPurchaseCount" in features:
        scaled_count = scale_series(np.log1p(purchase_count))
        rows = purchase_count.index.map(user_to_row).dropna().astype(int)
        features.loc[rows, "NormPurchaseCount"] = scaled_count.loc[purchase_count.index].to_numpy()

    unique_count = history.groupby("UserIndex", sort=False)["ItemIndex"].nunique()
    if "NormUniqueItemCount" in features:
        scaled_unique_count = scale_series(np.log1p(unique_count))
        rows = unique_count.index.map(user_to_row).dropna().astype(int)
        features.loc[rows, "NormUniqueItemCount"] = scaled_unique_count.loc[unique_count.index].to_numpy()

    item_lookup = item_features.set_index("ItemIndex")
    if "NormAvgItemPopularity" in features and "NormPopularity" in item_lookup:
        popularity = history["ItemIndex"].map(item_lookup["NormPopularity"]).fillna(0)
        avg_popularity = popularity.groupby(history["UserIndex"], sort=False).mean()
        scaled_popularity = scale_series(avg_popularity)
        rows = avg_popularity.index.map(user_to_row).dropna().astype(int)
        features.loc[rows, "NormAvgItemPopularity"] = scaled_popularity.loc[avg_popularity.index].to_numpy()

    if "TDat" in history:
        history["_TDat"] = pd.to_datetime(history["TDat"])
        latest = history.sort_values(["_TDat", "UserIndex"]).drop_duplicates("UserIndex", keep="last")
        latest_users = latest["UserIndex"].astype(int)
        rows = latest_users.map(user_to_row).dropna().astype(int)
        recent_mappings = {
            "RecentCategoryIdx": "CategoryIdx",
            "RecentColorIdx": "ColorIdx",
            "RecentProductGroupIdx": "ProductGroupIdx",
            "RecentSectionIdx": "SectionIdx",
            "RecentGarmentGroupIdx": "GarmentGroupIdx",
        }
        for user_column, item_column in recent_mappings.items():
            if user_column in features and item_column in item_lookup:
                values = latest["ItemIndex"].map(item_lookup[item_column]).fillna(0).astype(int).to_numpy()
                features.loc[rows, user_column] = values
        if "RecentSalesChannelIdx" in features and "SalesChannelId" in latest:
            features.loc[rows, "RecentSalesChannelIdx"] = latest["SalesChannelId"].fillna(0).astype(int).to_numpy()

    return features


def filter_interactions_by_activity(
    interactions: pd.DataFrame,
    min_user_interactions: int,
    min_item_interactions: int,
) -> pd.DataFrame:
    """Remove very sparse users/items so the model trains on stronger recommendation signals."""
    filtered = interactions.copy()
    while True:
        before = len(filtered)
        if min_user_interactions > 1:
            user_counts = filtered["UserIndex"].value_counts()
            filtered = filtered[filtered["UserIndex"].isin(user_counts[user_counts >= min_user_interactions].index)]
        if min_item_interactions > 1:
            item_counts = filtered["ItemIndex"].value_counts()
            filtered = filtered[filtered["ItemIndex"].isin(item_counts[item_counts >= min_item_interactions].index)]
        if len(filtered) == before:
            break
    return filtered.reset_index(drop=True)


def make_train_validation_indices(
    interactions: pd.DataFrame,
    validation_ratio: float,
    seed: int,
    strategy: str,
) -> tuple[list[int], list[int]]:
    """Split pairs while keeping validation users represented in the training set."""
    rng = np.random.default_rng(seed)
    row_count = len(interactions)
    target_validation_size = max(1, int(row_count * validation_ratio))

    if strategy == "random":
        indices = rng.permutation(row_count).tolist()
        validation_indices = sorted(indices[:target_validation_size])
        validation_set = set(validation_indices)
        train_indices = [index for index in range(row_count) if index not in validation_set]
        return train_indices, validation_indices

    if strategy == "temporal":
        if "TDat" not in interactions:
            raise RuntimeError("Temporal validation requires a TDat column in train_interactions.csv.")
        dated = interactions[["UserIndex", "TDat"]].copy()
        dated["_row_index"] = np.arange(row_count)
        dated["TDat"] = pd.to_datetime(dated["TDat"])
        latest_by_user = dated.sort_values("TDat").drop_duplicates("UserIndex", keep="last")
        if latest_by_user.empty:
            raise RuntimeError("No temporal validation candidates were found.")
        target_validation_size = min(target_validation_size, len(latest_by_user))
        latest_by_user = latest_by_user.sort_values(["TDat", "_row_index"], ascending=[False, True])
        validation_indices = sorted(latest_by_user["_row_index"].head(target_validation_size).astype(int).tolist())
        validation_set = set(validation_indices)
        train_indices = [index for index in range(row_count) if index not in validation_set]
        return train_indices, validation_indices

    validation_candidates = []
    for group_indices in interactions.groupby("UserIndex", sort=False).indices.values():
        if len(group_indices) > 1:
            validation_candidates.append(int(rng.choice(group_indices)))

    if not validation_candidates:
        raise RuntimeError("No users have enough interactions for user-holdout validation.")

    target_validation_size = min(target_validation_size, len(validation_candidates))
    validation_indices = sorted(
        rng.choice(validation_candidates, size=target_validation_size, replace=False).astype(int).tolist()
    )
    validation_set = set(validation_indices)
    train_indices = [index for index in range(row_count) if index not in validation_set]
    return train_indices, validation_indices


def encode_user_from_batch(model: TwoTowerModel, batch: dict[str, torch.Tensor]) -> torch.Tensor:
    """Encode users from the standard batch dictionary."""
    return model.encode_user(
        batch["user_idx"],
        batch["user_norm_price"],
        batch.get("user_norm_age"),
        batch.get("user_fn"),
        batch.get("user_active"),
        batch.get("user_club_status"),
        batch.get("user_fashion_frequency"),
        batch.get("user_recent_category"),
        batch.get("user_recent_color"),
        batch.get("user_recent_product_group"),
        batch.get("user_recent_section"),
        batch.get("user_recent_garment_group"),
        batch.get("user_recent_sales_channel"),
        batch.get("user_norm_purchase_count"),
        batch.get("user_norm_unique_item_count"),
        batch.get("user_norm_avg_item_popularity"),
    )


def multi_positive_loss(logits: torch.Tensor, positive_mask: torch.Tensor) -> torch.Tensor:
    """Compute softmax loss where each row can have multiple positive columns."""
    valid_rows = positive_mask.any(dim=1)
    if not bool(valid_rows.any()):
        return logits.sum() * 0
    row_logits = logits[valid_rows]
    row_mask = positive_mask[valid_rows]
    positive_logits = row_logits.masked_fill(~row_mask, float("-inf"))
    return (torch.logsumexp(row_logits, dim=1) - torch.logsumexp(positive_logits, dim=1)).mean()


def gather_item_batch(item_tensors: dict[str, torch.Tensor], positions: torch.Tensor) -> dict[str, torch.Tensor]:
    """Gather item feature tensors by row position from a candidate pool."""
    return {key: value[positions] for key, value in item_tensors.items()}


def batch_loss(
    model: TwoTowerModel,
    batch: dict[str, torch.Tensor],
    temperature: float,
    hard_negative_tensors: dict[str, torch.Tensor] | None = None,
    hard_negative_count: int = 0,
) -> torch.Tensor:
    """Calculate multi-positive contrastive loss with optional popular hard negatives."""
    user_vectors = encode_user_from_batch(model, batch)
    item_vectors = model.encode_item(
        batch["item_idx"],
        batch["item_cat"],
        batch["item_color"],
        batch["item_graphic"],
        batch["item_norm_price"],
        batch.get("item_product_group"),
        batch.get("item_section"),
        batch.get("item_garment_group"),
        batch.get("item_popularity"),
    )
    logits = torch.matmul(user_vectors, item_vectors.t()) / temperature
    user_positive_mask = batch["user_idx"].unsqueeze(1) == batch["user_idx"].unsqueeze(0)
    if hard_negative_tensors is not None and hard_negative_count > 0 and len(hard_negative_tensors["item_idx"]) > 0:
        negative_positions = torch.randint(
            0,
            len(hard_negative_tensors["item_idx"]),
            (hard_negative_count,),
            device=batch["user_idx"].device,
        )
        negative_batch = gather_item_batch(hard_negative_tensors, negative_positions)
        negative_vectors = model.encode_item(
            negative_batch["item_idx"],
            negative_batch["item_cat"],
            negative_batch["item_color"],
            negative_batch["item_graphic"],
            negative_batch["item_norm_price"],
            negative_batch["item_product_group"],
            negative_batch["item_section"],
            negative_batch["item_garment_group"],
            negative_batch["item_popularity"],
        )
        negative_logits = torch.matmul(user_vectors, negative_vectors.t()) / temperature
        target_matches = negative_batch["item_idx"].unsqueeze(0) == batch["item_idx"].unsqueeze(1)
        negative_logits = negative_logits.masked_fill(target_matches, float("-inf"))
        logits = torch.cat([logits, negative_logits], dim=1)
        user_positive_mask = torch.cat(
            [
                user_positive_mask,
                torch.zeros(
                    (user_positive_mask.size(0), negative_logits.size(1)),
                    dtype=torch.bool,
                    device=user_positive_mask.device,
                ),
            ],
            dim=1,
        )
    user_to_item = multi_positive_loss(logits, user_positive_mask)
    item_positive_mask = batch["item_idx"].unsqueeze(1) == batch["item_idx"].unsqueeze(0)
    item_to_user = multi_positive_loss(torch.matmul(item_vectors, user_vectors.t()) / temperature, item_positive_mask)
    return (user_to_item + item_to_user) / 2


@torch.no_grad()
def evaluate(model: TwoTowerModel, loader: DataLoader, device: torch.device, temperature: float) -> float:
    """Measure average validation loss without updating model weights."""
    model.eval()
    total_loss = 0.0
    batches = 0
    for batch in loader:
        batch = move_batch(batch, device)
        total_loss += batch_loss(model, batch, temperature).item()
        batches += 1
    return total_loss / max(batches, 1)


def build_item_tensors(
    item_features: pd.DataFrame,
    device: torch.device,
    candidate_item_indices: set[int] | None = None,
) -> dict[str, torch.Tensor]:
    """Prepare all item feature tensors so Recall@K can score every candidate item."""
    ordered_items = item_features.sort_values("ItemIndex")
    if candidate_item_indices is not None:
        ordered_items = ordered_items[ordered_items["ItemIndex"].astype(int).isin(candidate_item_indices)]
    return {
        "item_idx": torch.tensor(ordered_items["ItemIndex"].to_numpy(), dtype=torch.long, device=device),
        "item_cat": torch.tensor(ordered_items["CategoryIdx"].to_numpy(), dtype=torch.long, device=device),
        "item_color": torch.tensor(ordered_items["ColorIdx"].to_numpy(), dtype=torch.long, device=device),
        "item_graphic": torch.tensor(ordered_items["GraphicIdx"].to_numpy(), dtype=torch.long, device=device),
        "item_product_group": torch.tensor(
            ordered_items.get("ProductGroupIdx", pd.Series(0, index=ordered_items.index)).to_numpy(),
            dtype=torch.long,
            device=device,
        ),
        "item_section": torch.tensor(
            ordered_items.get("SectionIdx", pd.Series(0, index=ordered_items.index)).to_numpy(),
            dtype=torch.long,
            device=device,
        ),
        "item_garment_group": torch.tensor(
            ordered_items.get("GarmentGroupIdx", pd.Series(0, index=ordered_items.index)).to_numpy(),
            dtype=torch.long,
            device=device,
        ),
        "item_norm_price": torch.tensor(ordered_items["NormPrice"].to_numpy(), dtype=torch.float32, device=device),
        "item_popularity": torch.tensor(
            ordered_items.get("NormPopularity", pd.Series(0.0, index=ordered_items.index)).to_numpy(),
            dtype=torch.float32,
            device=device,
        ),
    }


def build_seen_lookup(dataset: PositivePairDataset, indices: list[int]) -> dict[int, set[int]]:
    """Record training items per user so Recall@K does not reward already-seen items."""
    seen: dict[int, set[int]] = {}
    for index in indices:
        user_idx = int(dataset.user_idx[index])
        item_idx = int(dataset.item_idx[index])
        seen.setdefault(user_idx, set()).add(item_idx)
    return seen


def build_user_feature_batch(
    dataset: PositivePairDataset,
    user_idx_cpu: torch.Tensor,
    device: torch.device,
) -> dict[str, torch.Tensor]:
    """Build a model-ready user feature batch from user indices."""
    batch = {"user_idx": user_idx_cpu.to(device)}
    for key, values in dataset.user_float_features.items():
        batch[key] = values[user_idx_cpu].to(device)
    for key, values in dataset.user_long_features.items():
        batch[key] = values[user_idx_cpu].to(device)
    return batch


def load_storefront_item_indices(data_dir: Path, item_features: pd.DataFrame) -> set[int]:
    """Load website product IDs and map them to model ItemIndex values for storefront-only metrics."""
    storefront_path = data_dir / "storefront_product_ids.csv"
    if not storefront_path.exists():
        return set()

    storefront_ids = set(pd.read_csv(storefront_path)["Id"].astype(int).tolist())
    storefront_rows = item_features[item_features["Id"].astype(int).isin(storefront_ids)]
    return set(storefront_rows["ItemIndex"].astype(int).tolist())


def filter_validation_indices_by_items(
    dataset: PositivePairDataset,
    validation_indices: list[int],
    candidate_item_indices: set[int],
) -> list[int]:
    """Keep validation rows whose target item exists in the candidate item set."""
    if not candidate_item_indices:
        return []
    return [
        index
        for index in validation_indices
        if int(dataset.item_idx[index]) in candidate_item_indices
    ]


def format_recall_metrics(prefix: str, metrics: dict[int, float]) -> str:
    """Format Recall@K values for readable training logs."""
    return " ".join(f"{prefix}@{k}={value:.4f}" for k, value in sorted(metrics.items()))


def format_at_k_metrics(prefix: str, metrics: dict[int, float]) -> str:
    """Format at-K metric values for readable training logs."""
    return " ".join(f"{prefix}@{k}={value:.4f}" for k, value in sorted(metrics.items()))


def metric_is_better(metric_name: str, value: float, best_value: float, min_delta: float) -> bool:
    """Return True when the current metric improves enough to save a new checkpoint."""
    if metric_name == "validation_loss":
        return value < best_value - min_delta
    return value > best_value


def initial_best_metric_value(metric_name: str) -> float:
    """Pick the correct starting best value depending on metric direction."""
    return math.inf if metric_name == "validation_loss" else -math.inf


def selected_metric_value(
    metric_name: str,
    validation_loss: float,
    validation_recall: dict[int, float],
    storefront_recall: dict[int, float],
    validation_map: dict[int, float],
    storefront_map: dict[int, float],
) -> float:
    """Read the metric chosen for checkpoint selection from the current epoch results."""
    if metric_name == "validation_loss":
        return validation_loss

    if "@" not in metric_name:
        raise ValueError(f"Unsupported selection metric: {metric_name}")

    prefix, k_text = metric_name.split("@", 1)
    k = int(k_text)
    if prefix == "recall":
        return validation_recall.get(k, 0.0)
    if prefix == "storefront_recall":
        return storefront_recall.get(k, 0.0)
    if prefix == "map":
        return validation_map.get(k, 0.0)
    if prefix == "storefront_map":
        return storefront_map.get(k, 0.0)
    raise ValueError(f"Unsupported selection metric: {metric_name}")


def safe_metric_name(metric_name: str) -> str:
    """Convert a metric name into a filesystem-safe filename part."""
    return metric_name.replace("@", "_at_").replace("/", "_").replace("\\", "_")


def archive_checkpoint(output_path: Path, checkpoint_dir: Path, metric_name: str, metric_value: float, epoch: int) -> Path:
    """Copy the current best checkpoint into a timestamped archive file."""
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = safe_metric_name(metric_name)
    archive_path = checkpoint_dir / f"two_tower_{safe_name}_{metric_value:.4f}_epoch{epoch}_{timestamp}.pth"
    shutil.copy2(output_path, archive_path)
    return archive_path


@torch.no_grad()
def recall_at_ks(
    model: TwoTowerModel,
    dataset: PositivePairDataset,
    validation_indices: list[int],
    all_item_tensors: dict[str, torch.Tensor],
    train_seen_items: dict[int, set[int]],
    device: torch.device,
    ks: list[int],
    batch_size: int,
    popularity_rerank_weight: float,
    rerank_candidate_pool: int,
) -> dict[int, float]:
    """Measure how often the held-out purchased item appears in top K recommendations."""
    if not ks or not validation_indices or len(all_item_tensors["item_idx"]) == 0:
        return {k: 0.0 for k in ks}

    model.eval()
    item_vectors = model.encode_item(
        all_item_tensors["item_idx"],
        all_item_tensors["item_cat"],
        all_item_tensors["item_color"],
        all_item_tensors["item_graphic"],
        all_item_tensors["item_norm_price"],
        all_item_tensors["item_product_group"],
        all_item_tensors["item_section"],
        all_item_tensors["item_garment_group"],
        all_item_tensors["item_popularity"],
    )
    candidate_item_indices = all_item_tensors["item_idx"]
    item_index_to_position = {
        int(item_idx): position
        for position, item_idx in enumerate(candidate_item_indices.detach().cpu().tolist())
    }

    hit_counts = {k: 0 for k in ks}
    total = 0
    max_k = min(max(ks), len(candidate_item_indices))
    for start in range(0, len(validation_indices), batch_size):
        batch_indices = validation_indices[start : start + batch_size]
        batch_index_tensor = torch.tensor(batch_indices, dtype=torch.long)
        user_idx_cpu = dataset.user_idx[batch_index_tensor]
        target_item_cpu = dataset.item_idx[batch_index_tensor]
        user_vectors = encode_user_from_batch(model, build_user_feature_batch(dataset, user_idx_cpu, device))
        scores = torch.matmul(user_vectors, item_vectors.t())

        for row, user_idx in enumerate(user_idx_cpu.tolist()):
            target_item = int(target_item_cpu[row])
            seen_positions = [
                item_index_to_position[item_idx]
                for item_idx in train_seen_items.get(int(user_idx), set())
                if item_idx != target_item and item_idx in item_index_to_position
            ]
            if seen_positions:
                scores[row, torch.tensor(seen_positions, dtype=torch.long, device=device)] = float("-inf")

        if popularity_rerank_weight > 0:
            pool_size = min(max(max_k, rerank_candidate_pool), len(candidate_item_indices))
            pool_scores, pool_positions = torch.topk(scores, pool_size, dim=1)
            popularity_scores = all_item_tensors["item_popularity"][pool_positions]
            rerank_scores = pool_scores + popularity_rerank_weight * popularity_scores
            rerank_order = torch.topk(rerank_scores, max_k, dim=1).indices
            top_positions = pool_positions.gather(1, rerank_order)
        else:
            top_positions = torch.topk(scores, max_k, dim=1).indices
        top_item_indices = candidate_item_indices[top_positions]
        target_items = target_item_cpu.to(device).unsqueeze(1)
        matches = top_item_indices == target_items
        for k in ks:
            effective_k = min(k, max_k)
            hit_counts[k] += matches[:, :effective_k].any(dim=1).sum().item()
        total += len(batch_indices)

    return {k: hit_counts[k] / max(total, 1) for k in ks}


def build_validation_targets(
    dataset: PositivePairDataset,
    validation_indices: list[int],
) -> dict[int, set[int]]:
    """Group held-out validation items by user for MAP@K evaluation."""
    targets: dict[int, set[int]] = {}
    for index in validation_indices:
        user_idx = int(dataset.user_idx[index])
        item_idx = int(dataset.item_idx[index])
        targets.setdefault(user_idx, set()).add(item_idx)
    return targets


@torch.no_grad()
def map_at_ks(
    model: TwoTowerModel,
    dataset: PositivePairDataset,
    validation_indices: list[int],
    all_item_tensors: dict[str, torch.Tensor],
    train_seen_items: dict[int, set[int]],
    device: torch.device,
    ks: list[int],
    batch_size: int,
    popularity_rerank_weight: float,
    rerank_candidate_pool: int,
) -> dict[int, float]:
    """Measure mean average precision by user, using held-out items as relevant items."""
    if not ks or not validation_indices or len(all_item_tensors["item_idx"]) == 0:
        return {k: 0.0 for k in ks}

    validation_targets = build_validation_targets(dataset, validation_indices)
    if not validation_targets:
        return {k: 0.0 for k in ks}

    model.eval()
    item_vectors = model.encode_item(
        all_item_tensors["item_idx"],
        all_item_tensors["item_cat"],
        all_item_tensors["item_color"],
        all_item_tensors["item_graphic"],
        all_item_tensors["item_norm_price"],
        all_item_tensors["item_product_group"],
        all_item_tensors["item_section"],
        all_item_tensors["item_garment_group"],
        all_item_tensors["item_popularity"],
    )
    candidate_item_indices = all_item_tensors["item_idx"]
    item_index_to_position = {
        int(item_idx): position
        for position, item_idx in enumerate(candidate_item_indices.detach().cpu().tolist())
    }

    user_indices = sorted(validation_targets)
    precision_sums = {k: 0.0 for k in ks}
    max_k = min(max(ks), len(candidate_item_indices))
    evaluated_users = 0
    for start in range(0, len(user_indices), batch_size):
        batch_users = user_indices[start : start + batch_size]
        user_idx_cpu = torch.tensor(batch_users, dtype=torch.long)
        user_vectors = encode_user_from_batch(model, build_user_feature_batch(dataset, user_idx_cpu, device))
        scores = torch.matmul(user_vectors, item_vectors.t())

        for row, user_idx in enumerate(batch_users):
            relevant_items = validation_targets[user_idx]
            seen_positions = [
                item_index_to_position[item_idx]
                for item_idx in train_seen_items.get(int(user_idx), set())
                if item_idx not in relevant_items and item_idx in item_index_to_position
            ]
            if seen_positions:
                scores[row, torch.tensor(seen_positions, dtype=torch.long, device=device)] = float("-inf")

        if popularity_rerank_weight > 0:
            pool_size = min(max(max_k, rerank_candidate_pool), len(candidate_item_indices))
            pool_scores, pool_positions = torch.topk(scores, pool_size, dim=1)
            popularity_scores = all_item_tensors["item_popularity"][pool_positions]
            rerank_scores = pool_scores + popularity_rerank_weight * popularity_scores
            rerank_order = torch.topk(rerank_scores, max_k, dim=1).indices
            top_positions = pool_positions.gather(1, rerank_order)
        else:
            top_positions = torch.topk(scores, max_k, dim=1).indices

        top_item_indices = candidate_item_indices[top_positions].detach().cpu().tolist()
        for user_idx, recommended_items in zip(batch_users, top_item_indices):
            relevant_items = validation_targets[user_idx]
            evaluated_users += 1
            for k in ks:
                hits = 0
                precision_sum = 0.0
                for rank, item_idx in enumerate(recommended_items[: min(k, max_k)], start=1):
                    if int(item_idx) in relevant_items:
                        hits += 1
                        precision_sum += hits / rank
                precision_sums[k] += precision_sum / min(len(relevant_items), k)

    return {k: precision_sums[k] / max(evaluated_users, 1) for k in ks}


def main() -> None:
    """Load prepared CSV data, train the two-tower model, and save the best checkpoint."""
    args = parse_args()
    recall_ks = parse_recall_ks(args.recall_ks, args.recall_k)
    map_ks = parse_metric_ks(args.map_ks)
    torch.manual_seed(args.seed)
    data_dir = Path(args.data_dir)

    user_features = pd.read_csv(data_dir / "user_features.csv")
    item_features = pd.read_csv(data_dir / "item_features.csv")
    interactions = pd.read_csv(data_dir / "train_interactions.csv")
    extended_feature_columns = ["ProductGroupIdx", "SectionIdx", "GarmentGroupIdx", "NormPopularity"]
    enabled_extended_features = [column for column in extended_feature_columns if column in item_features]
    if enabled_extended_features:
        print(f"Extended item features enabled: {', '.join(enabled_extended_features)}")
    else:
        print("Extended item features disabled. Re-run 3_data_pipeline.py to regenerate item_features.csv.")

    if args.max_interactions > 0 and len(interactions) > args.max_interactions:
        interactions = interactions.sample(args.max_interactions, random_state=args.seed)

    interactions = interactions.drop_duplicates(subset=["UserIndex", "ItemIndex"], keep="last")
    before_filter_rows = len(interactions)
    interactions = filter_interactions_by_activity(
        interactions,
        args.min_user_interactions,
        args.min_item_interactions,
    )
    print(
        "Interaction filtering: "
        f"{before_filter_rows:,} -> {len(interactions):,} pairs "
        f"(min_user={args.min_user_interactions}, min_item={args.min_item_interactions})"
    )
    if len(interactions) < 2:
        raise RuntimeError("Not enough interactions remain after filtering.")

    train_indices, validation_indices = make_train_validation_indices(
        interactions,
        args.validation_ratio,
        args.seed,
        args.validation_strategy,
    )
    user_features = build_training_user_features(user_features, interactions, train_indices, item_features)
    dataset = PositivePairDataset(interactions, user_features, item_features)
    rng = np.random.default_rng(args.seed)
    loss_validation_indices = validation_indices
    if args.max_validation_loss_pairs > 0 and len(loss_validation_indices) > args.max_validation_loss_pairs:
        loss_validation_indices = sorted(
            rng.choice(loss_validation_indices, size=args.max_validation_loss_pairs, replace=False).astype(int).tolist()
        )
    metric_validation_indices = validation_indices
    if args.max_metric_validation_pairs > 0 and len(metric_validation_indices) > args.max_metric_validation_pairs:
        metric_validation_indices = sorted(
            rng.choice(metric_validation_indices, size=args.max_metric_validation_pairs, replace=False).astype(int).tolist()
        )
    train_dataset = Subset(dataset, train_indices)
    validation_dataset = Subset(dataset, loss_validation_indices)

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        drop_last=True,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        drop_last=True,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    config = ModelConfig()
    model = TwoTowerModel(
        num_users=int(user_features["UserIndex"].max()) + 1,
        num_items=int(item_features["ItemIndex"].max()) + 1,
        num_categories=int(item_features["CategoryIdx"].max()) + 1,
        num_colors=int(item_features["ColorIdx"].max()) + 1,
        num_graphics=int(item_features["GraphicIdx"].max()) + 1,
        num_product_groups=optional_feature_count(item_features, "ProductGroupIdx"),
        num_sections=optional_feature_count(item_features, "SectionIdx"),
        num_garment_groups=optional_feature_count(item_features, "GarmentGroupIdx"),
        num_club_statuses=optional_feature_count(user_features, "ClubStatusIdx"),
        num_fashion_frequencies=optional_feature_count(user_features, "FashionFrequencyIdx"),
        num_recent_categories=optional_feature_count(user_features, "RecentCategoryIdx"),
        num_recent_colors=optional_feature_count(user_features, "RecentColorIdx"),
        num_recent_product_groups=optional_feature_count(user_features, "RecentProductGroupIdx"),
        num_recent_sections=optional_feature_count(user_features, "RecentSectionIdx"),
        num_recent_garment_groups=optional_feature_count(user_features, "RecentGarmentGroupIdx"),
        num_sales_channels=optional_feature_count(user_features, "RecentSalesChannelIdx"),
        use_item_popularity="NormPopularity" in item_features,
        **asdict(config),
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    all_item_tensors = build_item_tensors(item_features, device)
    hard_negative_tensors = None
    if args.hard_negative_count > 0 and args.hard_negative_pool_size > 0:
        hard_negative_item_indices = set(
            item_features.nlargest(args.hard_negative_pool_size, "NormPopularity")["ItemIndex"].astype(int).tolist()
        )
        hard_negative_tensors = build_item_tensors(item_features, device, hard_negative_item_indices)
    storefront_item_indices = load_storefront_item_indices(data_dir, item_features)
    storefront_item_tensors = (
        build_item_tensors(item_features, device, storefront_item_indices)
        if storefront_item_indices
        else None
    )
    storefront_validation_indices = filter_validation_indices_by_items(
        dataset,
        metric_validation_indices,
        storefront_item_indices,
    )
    train_seen_items = build_seen_lookup(dataset, train_indices)

    best_metric_value = initial_best_metric_value(args.selection_metric)
    output_path = Path(args.output)
    checkpoint_dir = Path(args.checkpoint_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(
        f"Training on {device}: {len(train_dataset):,} train pairs, "
        f"{len(validation_indices):,} validation pairs "
        f"({len(loss_validation_indices):,} loss, {len(metric_validation_indices):,} metric)"
    )
    if recall_ks:
        print(f"Recall metrics enabled for K={recall_ks}.")
        if args.popularity_rerank_weight > 0:
            print(
                "Popularity rerank enabled: "
                f"pool={args.rerank_candidate_pool}, weight={args.popularity_rerank_weight:.3f}"
            )
        print(f"All-item recall candidates: {len(all_item_tensors['item_idx']):,}")
        if storefront_item_tensors is not None:
            print(
                "Storefront recall candidates: "
                f"{len(storefront_item_tensors['item_idx']):,}; "
                f"eligible validation rows: {len(storefront_validation_indices):,}"
            )
        else:
            print("Storefront recall disabled because storefront_product_ids.csv was not found or empty.")
    if map_ks:
        print(f"MAP metrics enabled for K={map_ks}.")
    if hard_negative_tensors is not None:
        print(
            "Popular hard negatives enabled: "
            f"count={args.hard_negative_count}, pool={len(hard_negative_tensors['item_idx']):,}"
        )
    amp_enabled = bool(args.amp and device.type == "cuda")
    scaler = torch.cuda.amp.GradScaler(enabled=amp_enabled)
    epochs_without_improvement = 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        for step, batch in enumerate(train_loader, start=1):
            batch = move_batch(batch, device)
            optimizer.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=amp_enabled):
                loss = batch_loss(
                    model,
                    batch,
                    args.temperature,
                    hard_negative_tensors,
                    args.hard_negative_count,
                )
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()
            running_loss += loss.item()

            if step % 100 == 0:
                print(f"Epoch {epoch} step {step}/{len(train_loader)} loss={running_loss / step:.4f}")

        train_loss = running_loss / max(len(train_loader), 1)
        validation_loss = evaluate(model, validation_loader, device, args.temperature)
        validation_recall = (
            recall_at_ks(
                model,
                dataset,
                metric_validation_indices,
                all_item_tensors,
                train_seen_items,
                device,
                recall_ks,
                args.recall_batch_size,
                args.popularity_rerank_weight,
                args.rerank_candidate_pool,
            )
            if recall_ks
            else {}
        )
        storefront_recall = (
            recall_at_ks(
                model,
                dataset,
                storefront_validation_indices,
                storefront_item_tensors,
                train_seen_items,
                device,
                recall_ks,
                args.recall_batch_size,
                args.popularity_rerank_weight,
                args.rerank_candidate_pool,
            )
            if recall_ks and storefront_item_tensors is not None and storefront_validation_indices
            else {}
        )
        validation_map = (
            map_at_ks(
                model,
                dataset,
                metric_validation_indices,
                all_item_tensors,
                train_seen_items,
                device,
                map_ks,
                args.recall_batch_size,
                args.popularity_rerank_weight,
                args.rerank_candidate_pool,
            )
            if map_ks
            else {}
        )
        storefront_map = (
            map_at_ks(
                model,
                dataset,
                storefront_validation_indices,
                storefront_item_tensors,
                train_seen_items,
                device,
                map_ks,
                args.recall_batch_size,
                args.popularity_rerank_weight,
                args.rerank_candidate_pool,
            )
            if map_ks and storefront_item_tensors is not None and storefront_validation_indices
            else {}
        )
        recall_text = format_recall_metrics("recall", validation_recall)
        storefront_recall_text = format_recall_metrics("storefront_recall", storefront_recall)
        map_text = format_at_k_metrics("map", validation_map)
        storefront_map_text = format_at_k_metrics("storefront_map", storefront_map)
        print(
            f"Epoch {epoch} complete train_loss={train_loss:.4f} "
            f"validation_loss={validation_loss:.4f}"
            f"{(' ' + recall_text) if recall_text else ''}"
            f"{(' ' + storefront_recall_text) if storefront_recall_text else ''}"
            f"{(' ' + map_text) if map_text else ''}"
            f"{(' ' + storefront_map_text) if storefront_map_text else ''}"
        )

        current_metric_value = selected_metric_value(
            args.selection_metric,
            validation_loss,
            validation_recall,
            storefront_recall,
            validation_map,
            storefront_map,
        )

        if metric_is_better(args.selection_metric, current_metric_value, best_metric_value, args.min_delta):
            best_metric_value = current_metric_value
            epochs_without_improvement = 0
            checkpoint = {
                "model_state_dict": model.state_dict(),
                "model_config": asdict(config),
                "training_config": vars(args),
                "metrics": {
                    "selection_metric": args.selection_metric,
                    "selection_metric_value": best_metric_value,
                    "validation_loss": validation_loss,
                    "epoch": epoch,
                },
            }
            checkpoint["metrics"].update({f"recall@{k}": value for k, value in validation_recall.items()})
            checkpoint["metrics"].update(
                {f"storefront_recall@{k}": value for k, value in storefront_recall.items()}
            )
            checkpoint["metrics"].update({f"map@{k}": value for k, value in validation_map.items()})
            checkpoint["metrics"].update({f"storefront_map@{k}": value for k, value in storefront_map.items()})
            torch.save(checkpoint, output_path)
            archive_path = archive_checkpoint(
                output_path,
                checkpoint_dir,
                args.selection_metric,
                best_metric_value,
                epoch,
            )
            (output_path.parent / "two_tower_model_config.json").write_text(
                json.dumps(checkpoint["model_config"], indent=2),
                encoding="utf-8",
            )
            print(f"Saved best checkpoint to {output_path} using {args.selection_metric}={best_metric_value:.4f}")
            print(f"Archived best checkpoint to {archive_path}")
        else:
            epochs_without_improvement += 1
            if args.early_stopping_patience > 0:
                print(
                    "No validation improvement "
                    f"({epochs_without_improvement}/{args.early_stopping_patience} patience)."
                )
            else:
                print("No validation improvement.")
            if (
                args.early_stopping_patience > 0
                and epochs_without_improvement >= args.early_stopping_patience
            ):
                print(
                    "Early stopping triggered. "
                    f"Best {args.selection_metric}={best_metric_value:.4f}."
                )
                break


if __name__ == "__main__":
    main()
