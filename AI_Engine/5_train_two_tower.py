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
        return {
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


def parse_args() -> argparse.Namespace:
    """Read command-line options for model training."""
    parser = argparse.ArgumentParser(description="Train Outfitly two-tower model")
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--max-interactions", type=int, default=0, help="0 means use all prepared interactions")
    parser.add_argument("--validation-ratio", type=float, default=0.05)
    parser.add_argument("--min-user-interactions", type=int, default=1)
    parser.add_argument("--min-item-interactions", type=int, default=1)
    parser.add_argument(
        "--validation-strategy",
        choices=["user-holdout", "random"],
        default="random",
        help="Random validation worked better for the current sampled H&M data.",
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
        "--recall-batch-size",
        type=int,
        default=64,
        help="Validation batch size used for Recall@K scoring against all items.",
    )
    parser.add_argument(
        "--selection-metric",
        default="storefront_recall@10",
        help="Metric used to save the best checkpoint. Use validation_loss or a recall metric like storefront_recall@10.",
    )
    parser.add_argument(
        "--popularity-rerank-weight",
        type=float,
        default=0.10,
        help="Weight added to candidate scores from normalized item popularity during Recall@K reranking.",
    )
    parser.add_argument(
        "--rerank-candidate-pool",
        type=int,
        default=200,
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


def move_batch(batch: dict[str, torch.Tensor], device: torch.device) -> dict[str, torch.Tensor]:
    """Move every tensor in a training batch to CPU or GPU."""
    return {key: value.to(device, non_blocking=True) for key, value in batch.items()}


def optional_feature_count(item_features: pd.DataFrame, column: str) -> int | None:
    """Return the number of encoded values for an optional item feature column."""
    if column not in item_features:
        return None
    return int(item_features[column].max()) + 1


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


def batch_loss(model: TwoTowerModel, batch: dict[str, torch.Tensor], temperature: float) -> torch.Tensor:
    """Calculate in-batch contrastive loss for matching users to their purchased items."""
    user_vectors = model.encode_user(batch["user_idx"], batch["user_norm_price"])
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
    labels = torch.arange(logits.size(0), device=logits.device)
    user_to_item = nn.functional.cross_entropy(logits, labels)
    item_to_user = nn.functional.cross_entropy(logits.t(), labels)
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
        user_price_cpu = dataset.user_price[user_idx_cpu]

        user_vectors = model.encode_user(user_idx_cpu.to(device), user_price_cpu.to(device))
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


def main() -> None:
    """Load prepared CSV data, train the two-tower model, and save the best checkpoint."""
    args = parse_args()
    recall_ks = parse_recall_ks(args.recall_ks, args.recall_k)
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

    dataset = PositivePairDataset(interactions, user_features, item_features)

    train_indices, validation_indices = make_train_validation_indices(
        interactions,
        args.validation_ratio,
        args.seed,
        args.validation_strategy,
    )
    train_dataset = Subset(dataset, train_indices)
    validation_dataset = Subset(dataset, validation_indices)

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
        use_item_popularity="NormPopularity" in item_features,
        **asdict(config),
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    all_item_tensors = build_item_tensors(item_features, device)
    storefront_item_indices = load_storefront_item_indices(data_dir, item_features)
    storefront_item_tensors = (
        build_item_tensors(item_features, device, storefront_item_indices)
        if storefront_item_indices
        else None
    )
    storefront_validation_indices = filter_validation_indices_by_items(
        dataset,
        validation_indices,
        storefront_item_indices,
    )
    train_seen_items = build_seen_lookup(dataset, train_indices)

    best_metric_value = initial_best_metric_value(args.selection_metric)
    output_path = Path(args.output)
    checkpoint_dir = Path(args.checkpoint_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Training on {device}: {len(train_dataset):,} train pairs, {len(validation_dataset):,} validation pairs")
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
    epochs_without_improvement = 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        for step, batch in enumerate(train_loader, start=1):
            batch = move_batch(batch, device)
            optimizer.zero_grad(set_to_none=True)
            loss = batch_loss(model, batch, args.temperature)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            running_loss += loss.item()

            if step % 100 == 0:
                print(f"Epoch {epoch} step {step}/{len(train_loader)} loss={running_loss / step:.4f}")

        train_loss = running_loss / max(len(train_loader), 1)
        validation_loss = evaluate(model, validation_loader, device, args.temperature)
        validation_recall = (
            recall_at_ks(
                model,
                dataset,
                validation_indices,
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
        recall_text = format_recall_metrics("recall", validation_recall)
        storefront_recall_text = format_recall_metrics("storefront_recall", storefront_recall)
        print(
            f"Epoch {epoch} complete train_loss={train_loss:.4f} "
            f"validation_loss={validation_loss:.4f}"
            f"{(' ' + recall_text) if recall_text else ''}"
            f"{(' ' + storefront_recall_text) if storefront_recall_text else ''}"
        )

        current_metric_value = selected_metric_value(
            args.selection_metric,
            validation_loss,
            validation_recall,
            storefront_recall,
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
