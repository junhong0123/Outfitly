"""Evaluate a saved Outfitly two-tower checkpoint with report-friendly metrics."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import torch


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"


def load_training_module():
    """Load helpers from 5_train_two_tower.py even though the filename starts with a number."""
    module_path = SCRIPT_DIR / "5_train_two_tower.py"
    spec = importlib.util.spec_from_file_location("outfitly_train_two_tower", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load training module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


train = load_training_module()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a saved Outfitly two-tower model")
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--checkpoint", default=str(DATA_DIR / "two_tower_model.pth"))
    parser.add_argument("--validation-ratio", type=float, default=0.05)
    parser.add_argument("--validation-strategy", choices=["user-holdout", "random", "temporal"], default="temporal")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-user-interactions", type=int, default=3)
    parser.add_argument("--min-item-interactions", type=int, default=5)
    parser.add_argument("--max-interactions", type=int, default=0)
    parser.add_argument("--recall-ks", default="10,50,100")
    parser.add_argument("--map-ks", default="12")
    parser.add_argument(
        "--popular-candidate-counts",
        default="100",
        help="Comma-separated top-popular candidate pool sizes to evaluate, or 0 to disable.",
    )
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--max-metric-validation-pairs", type=int, default=50000)
    parser.add_argument("--popularity-rerank-weight", type=float, default=0.80)
    parser.add_argument("--rerank-candidate-pool", type=int, default=3000)
    parser.add_argument("--output-json", default="")
    return parser.parse_args()


def ranked_popular_items(
    dataset,
    train_indices: list[int],
    candidate_item_indices: set[int],
) -> list[int]:
    """Rank candidate items by training-set popularity without validation leakage."""
    counts: dict[int, int] = {}
    for index in train_indices:
        item_idx = int(dataset.item_idx[index])
        if item_idx in candidate_item_indices:
            counts[item_idx] = counts.get(item_idx, 0) + 1
    return sorted(candidate_item_indices, key=lambda item_idx: (-counts.get(item_idx, 0), item_idx))


def top_popular_item_indices(dataset, train_indices: list[int], count: int) -> set[int]:
    """Select the top-N most popular training items."""
    all_items = set(int(item_idx) for item_idx in dataset.item_idx.tolist())
    return set(ranked_popular_items(dataset, train_indices, all_items)[:count])


def recommendations_from_ranked_items(
    ranked_items: list[int],
    seen_items: set[int],
    relevant_items: set[int],
    max_k: int,
) -> list[int]:
    """Return the first max_k popular items after removing training-seen items."""
    recommendations = []
    for item_idx in ranked_items:
        if item_idx in seen_items and item_idx not in relevant_items:
            continue
        recommendations.append(item_idx)
        if len(recommendations) >= max_k:
            break
    return recommendations


def popular_recall_at_ks(
    dataset,
    validation_indices: list[int],
    ranked_items: list[int],
    train_seen_items: dict[int, set[int]],
    ks: list[int],
) -> dict[int, float]:
    """Calculate row-level Recall@K for a static popularity recommender."""
    if not ks or not validation_indices:
        return {k: 0.0 for k in ks}

    max_k = max(ks)
    cache: dict[int, list[int]] = {}
    hit_counts = {k: 0 for k in ks}
    for index in validation_indices:
        user_idx = int(dataset.user_idx[index])
        target_item = int(dataset.item_idx[index])
        if user_idx not in cache:
            cache[user_idx] = recommendations_from_ranked_items(
                ranked_items,
                train_seen_items.get(user_idx, set()),
                set(),
                max_k,
            )
        recommendations = cache[user_idx]
        for k in ks:
            hit_counts[k] += int(target_item in recommendations[:k])
    return {k: hit_counts[k] / len(validation_indices) for k in ks}


def popular_map_at_ks(
    dataset,
    validation_indices: list[int],
    ranked_items: list[int],
    train_seen_items: dict[int, set[int]],
    ks: list[int],
) -> dict[int, float]:
    """Calculate user-level MAP@K for a static popularity recommender."""
    if not ks or not validation_indices:
        return {k: 0.0 for k in ks}

    validation_targets = train.build_validation_targets(dataset, validation_indices)
    max_k = max(ks)
    precision_sums = {k: 0.0 for k in ks}
    for user_idx, relevant_items in validation_targets.items():
        recommendations = recommendations_from_ranked_items(
            ranked_items,
            train_seen_items.get(user_idx, set()),
            relevant_items,
            max_k,
        )
        for k in ks:
            hits = 0
            precision_sum = 0.0
            for rank, item_idx in enumerate(recommendations[:k], start=1):
                if item_idx in relevant_items:
                    hits += 1
                    precision_sum += hits / rank
            precision_sums[k] += precision_sum / min(len(relevant_items), k)
    return {k: precision_sums[k] / max(len(validation_targets), 1) for k in ks}


def add_popular_baseline_metrics(
    metrics: dict,
    prefix: str,
    dataset,
    validation_indices: list[int],
    ranked_items: list[int],
    train_seen_items: dict[int, set[int]],
    recall_ks: list[int],
    map_ks: list[int],
) -> None:
    """Add popularity baseline metrics to the JSON report."""
    if recall_ks:
        metrics.update(
            {
                f"{prefix}_popular_recall@{k}": value
                for k, value in popular_recall_at_ks(
                    dataset,
                    validation_indices,
                    ranked_items,
                    train_seen_items,
                    recall_ks,
                ).items()
            }
        )
    if map_ks:
        metrics.update(
            {
                f"{prefix}_popular_map@{k}": value
                for k, value in popular_map_at_ks(
                    dataset,
                    validation_indices,
                    ranked_items,
                    train_seen_items,
                    map_ks,
                ).items()
            }
        )


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir)
    checkpoint_path = Path(args.checkpoint)

    user_features = pd.read_csv(data_dir / "user_features.csv")
    item_features = pd.read_csv(data_dir / "item_features.csv")
    interactions = pd.read_csv(data_dir / "train_interactions.csv")
    if args.max_interactions > 0 and len(interactions) > args.max_interactions:
        interactions = interactions.sample(args.max_interactions, random_state=args.seed)
    interactions = interactions.drop_duplicates(subset=["UserIndex", "ItemIndex"], keep="last")
    interactions = train.filter_interactions_by_activity(
        interactions,
        args.min_user_interactions,
        args.min_item_interactions,
    )

    train_indices, validation_indices = train.make_train_validation_indices(
        interactions,
        args.validation_ratio,
        args.seed,
        args.validation_strategy,
    )
    user_features = train.build_training_user_features(user_features, interactions, train_indices, item_features)
    dataset = train.PositivePairDataset(interactions, user_features, item_features)
    if args.max_metric_validation_pairs > 0 and len(validation_indices) > args.max_metric_validation_pairs:
        rng = np.random.default_rng(args.seed)
        validation_indices = sorted(
            rng.choice(validation_indices, size=args.max_metric_validation_pairs, replace=False).astype(int).tolist()
        )
    train_seen_items = train.build_seen_lookup(dataset, train_indices)

    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    model_config = checkpoint.get("model_config") or asdict(train.ModelConfig())
    model = train.TwoTowerModel(
        num_users=int(user_features["UserIndex"].max()) + 1,
        num_items=int(item_features["ItemIndex"].max()) + 1,
        num_categories=int(item_features["CategoryIdx"].max()) + 1,
        num_colors=int(item_features["ColorIdx"].max()) + 1,
        num_graphics=int(item_features["GraphicIdx"].max()) + 1,
        num_product_groups=train.optional_feature_count(item_features, "ProductGroupIdx"),
        num_sections=train.optional_feature_count(item_features, "SectionIdx"),
        num_garment_groups=train.optional_feature_count(item_features, "GarmentGroupIdx"),
        num_club_statuses=train.optional_feature_count(user_features, "ClubStatusIdx"),
        num_fashion_frequencies=train.optional_feature_count(user_features, "FashionFrequencyIdx"),
        num_recent_categories=train.optional_feature_count(user_features, "RecentCategoryIdx"),
        num_recent_colors=train.optional_feature_count(user_features, "RecentColorIdx"),
        num_recent_product_groups=train.optional_feature_count(user_features, "RecentProductGroupIdx"),
        num_recent_sections=train.optional_feature_count(user_features, "RecentSectionIdx"),
        num_recent_garment_groups=train.optional_feature_count(user_features, "RecentGarmentGroupIdx"),
        num_sales_channels=train.optional_feature_count(user_features, "RecentSalesChannelIdx"),
        use_item_popularity="NormPopularity" in item_features,
        **model_config,
    )
    model.load_state_dict(checkpoint["model_state_dict"])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    all_item_tensors = train.build_item_tensors(item_features, device)
    storefront_item_indices = train.load_storefront_item_indices(data_dir, item_features)
    storefront_item_tensors = (
        train.build_item_tensors(item_features, device, storefront_item_indices)
        if storefront_item_indices
        else None
    )
    storefront_validation_indices = train.filter_validation_indices_by_items(
        dataset,
        validation_indices,
        storefront_item_indices,
    )

    recall_ks = train.parse_metric_ks(args.recall_ks)
    map_ks = train.parse_metric_ks(args.map_ks)
    popular_candidate_counts = train.parse_metric_ks(args.popular_candidate_counts)
    metrics = {
        "checkpoint": str(checkpoint_path),
        "device": str(device),
        "validation_pairs": len(validation_indices),
        "storefront_validation_pairs": len(storefront_validation_indices),
        "checkpoint_metrics": checkpoint.get("metrics", {}),
    }

    if recall_ks:
        metrics.update(
            {
                f"recall@{k}": value
                for k, value in train.recall_at_ks(
                    model,
                    dataset,
                    validation_indices,
                    all_item_tensors,
                    train_seen_items,
                    device,
                    recall_ks,
                    args.batch_size,
                    args.popularity_rerank_weight,
                    args.rerank_candidate_pool,
                ).items()
            }
        )
        if storefront_item_tensors is not None and storefront_validation_indices:
            metrics.update(
                {
                    f"storefront_recall@{k}": value
                    for k, value in train.recall_at_ks(
                        model,
                        dataset,
                        storefront_validation_indices,
                        storefront_item_tensors,
                        train_seen_items,
                        device,
                        recall_ks,
                        args.batch_size,
                        args.popularity_rerank_weight,
                        args.rerank_candidate_pool,
                    ).items()
                }
            )

    if map_ks:
        metrics.update(
            {
                f"map@{k}": value
                for k, value in train.map_at_ks(
                    model,
                    dataset,
                    validation_indices,
                    all_item_tensors,
                    train_seen_items,
                    device,
                    map_ks,
                    args.batch_size,
                    args.popularity_rerank_weight,
                    args.rerank_candidate_pool,
                ).items()
            }
        )
        if storefront_item_tensors is not None and storefront_validation_indices:
            metrics.update(
                {
                    f"storefront_map@{k}": value
                    for k, value in train.map_at_ks(
                        model,
                        dataset,
                        storefront_validation_indices,
                        storefront_item_tensors,
                        train_seen_items,
                        device,
                        map_ks,
                        args.batch_size,
                        args.popularity_rerank_weight,
                        args.rerank_candidate_pool,
                    ).items()
                }
            )

    all_item_indices = set(item_features["ItemIndex"].astype(int).tolist())
    add_popular_baseline_metrics(
        metrics,
        "all",
        dataset,
        validation_indices,
        ranked_popular_items(dataset, train_indices, all_item_indices),
        train_seen_items,
        recall_ks,
        map_ks,
    )
    if storefront_item_indices and storefront_validation_indices:
        add_popular_baseline_metrics(
            metrics,
            "storefront",
            dataset,
            storefront_validation_indices,
            ranked_popular_items(dataset, train_indices, storefront_item_indices),
            train_seen_items,
            recall_ks,
            map_ks,
        )

    for count in popular_candidate_counts:
        candidate_indices = top_popular_item_indices(dataset, train_indices, count)
        candidate_validation_indices = train.filter_validation_indices_by_items(
            dataset,
            validation_indices,
            candidate_indices,
        )
        if not candidate_indices or not candidate_validation_indices:
            continue

        label = f"top{count}_popular_candidates"
        candidate_item_tensors = train.build_item_tensors(item_features, device, candidate_indices)
        metrics[f"{label}_validation_pairs"] = len(candidate_validation_indices)
        if recall_ks:
            metrics.update(
                {
                    f"{label}_recall@{k}": value
                    for k, value in train.recall_at_ks(
                        model,
                        dataset,
                        candidate_validation_indices,
                        candidate_item_tensors,
                        train_seen_items,
                        device,
                        recall_ks,
                        args.batch_size,
                        args.popularity_rerank_weight,
                        args.rerank_candidate_pool,
                    ).items()
                }
            )
        if map_ks:
            metrics.update(
                {
                    f"{label}_map@{k}": value
                    for k, value in train.map_at_ks(
                        model,
                        dataset,
                        candidate_validation_indices,
                        candidate_item_tensors,
                        train_seen_items,
                        device,
                        map_ks,
                        args.batch_size,
                        args.popularity_rerank_weight,
                        args.rerank_candidate_pool,
                    ).items()
                }
            )
        add_popular_baseline_metrics(
            metrics,
            label,
            dataset,
            candidate_validation_indices,
            ranked_popular_items(dataset, train_indices, candidate_indices),
            train_seen_items,
            recall_ks,
            map_ks,
        )

    report = json.dumps(metrics, indent=2)
    print(report)
    if args.output_json:
        Path(args.output_json).write_text(report + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
