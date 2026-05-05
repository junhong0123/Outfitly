"""Outfitly retrieval API."""

from __future__ import annotations

import pickle
import importlib.util
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pandas as pd
import torch
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DEFAULT_TOP_K = 10
MAX_TOP_K = 50

def _load_two_tower_model_class():
    """Load TwoTowerModel from 4_modeling.py for the API service."""
    module_path = SCRIPT_DIR / "4_modeling.py"
    spec = importlib.util.spec_from_file_location("outfitly_modeling", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load model module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.TwoTowerModel


def _load_rag_chatbot_module():
    """Load the Gemini RAG chatbot from 7_rag_chatbot.py."""
    module_path = SCRIPT_DIR / "7_rag_chatbot.py"
    spec = importlib.util.spec_from_file_location("outfitly_rag_chatbot", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load RAG chatbot module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TwoTowerModel = _load_two_tower_model_class()
RagChatbot = _load_rag_chatbot_module()
app_state: dict[str, Any] = {}


class ChatRequest(BaseModel):
    """Request body for the Outfitly AI chat endpoint."""

    message: str = Field(..., min_length=1)
    user_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=8)


def _load_checkpoint(path: Path) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    """Load either a new checkpoint dict or an older raw model state dict."""
    try:
        loaded = torch.load(path, map_location=torch.device("cpu"), weights_only=False)
    except TypeError:
        loaded = torch.load(path, map_location=torch.device("cpu"))
    if isinstance(loaded, dict) and "model_state_dict" in loaded:
        return loaded["model_state_dict"], loaded.get("model_config", {})
    if isinstance(loaded, dict):
        return loaded, {}
    raise RuntimeError(f"Unsupported model checkpoint format: {path}")


def _infer_model_config(state_dict: dict[str, torch.Tensor]) -> dict[str, Any]:
    """Recover model size settings from a checkpoint when config metadata is missing."""
    user_emb = state_dict["user_emb.weight"]
    item_dense_weight = state_dict["item_dense.0.weight"]
    user_dense_hidden = state_dict["user_dense.0.weight"].shape[0]
    out_dim = state_dict["user_dense.3.weight"].shape[0]
    tag_emb_dim = state_dict["cat_emb.weight"].shape[1]
    emb_dim = user_emb.shape[1]
    tag_count = 6 if "product_group_emb.weight" in state_dict else 3
    numeric_count = 2 if item_dense_weight.shape[1] - emb_dim - tag_emb_dim * tag_count == 2 else 1
    # input = item emb + tag embeddings + normalized price
    expected_input = emb_dim + tag_emb_dim * tag_count + numeric_count
    if item_dense_weight.shape[1] != expected_input:
        tag_emb_dim = int((item_dense_weight.shape[1] - emb_dim - 1) / tag_count)
    return {
        "emb_dim": int(emb_dim),
        "out_dim": int(out_dim),
        "hidden_dim": int(user_dense_hidden),
        "tag_emb_dim": int(tag_emb_dim),
        "dropout": 0.0,
    }


def _extra_model_kwargs_from_checkpoint(state_dict: dict[str, torch.Tensor]) -> dict[str, int]:
    """Read optional item feature embedding sizes from newer model checkpoints."""
    required_keys = [
        "product_group_emb.weight",
        "section_emb.weight",
        "garment_group_emb.weight",
    ]
    if not all(key in state_dict for key in required_keys):
        extra_kwargs = {}
    else:
        extra_kwargs = {
            "num_product_groups": int(state_dict["product_group_emb.weight"].shape[0]),
            "num_sections": int(state_dict["section_emb.weight"].shape[0]),
            "num_garment_groups": int(state_dict["garment_group_emb.weight"].shape[0]),
        }

    emb_dim = state_dict["user_emb.weight"].shape[1]
    tag_emb_dim = state_dict["cat_emb.weight"].shape[1]
    tag_count = 6 if required_keys[0] in state_dict else 3
    dense_input_dim = state_dict["item_dense.0.weight"].shape[1]
    extra_kwargs["use_item_popularity"] = dense_input_dim - emb_dim - tag_emb_dim * tag_count == 2
    return extra_kwargs


def _load_storefront_filter(item_features: pd.DataFrame) -> torch.Tensor | None:
    """Build a boolean mask so recommendations can be limited to products in the website DB."""
    path = DATA_DIR / "storefront_product_ids.csv"
    if not path.exists():
        return None
    storefront_ids = set(pd.read_csv(path)["Id"].astype(int).tolist())
    mask = item_features["Id"].astype(int).isin(storefront_ids).to_numpy()
    if not mask.any():
        return None
    return torch.tensor(mask, dtype=torch.bool)


def _build_seen_items(train_interactions: pd.DataFrame) -> dict[int, set[int]]:
    """Create a lookup of items each user already purchased, so they can be excluded."""
    seen: dict[int, set[int]] = {}
    for row in train_interactions[["UserIndex", "ItemIndex"]].itertuples(index=False):
        seen.setdefault(int(row.UserIndex), set()).add(int(row.ItemIndex))
    return seen


def _item_feature_tensor(item_features: pd.DataFrame, column: str, dtype: torch.dtype) -> torch.Tensor:
    """Load an item feature column, or use zeros when running an older feature file."""
    if column in item_features:
        values = item_features[column].to_numpy()
    else:
        values = [0] * len(item_features)
    return torch.tensor(values, dtype=dtype)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model files once when FastAPI starts and clear them when the app stops."""
    required_files = [
        "encoders.pkl",
        "user_features.csv",
        "item_features.csv",
        "train_interactions.csv",
        "two_tower_model.pth",
    ]
    missing = [name for name in required_files if not (DATA_DIR / name).exists()]
    if missing:
        raise RuntimeError(f"Missing AI data files in {DATA_DIR}: {', '.join(missing)}")

    with open(DATA_DIR / "encoders.pkl", "rb") as file:
        encoders = pickle.load(file)

    user_features = pd.read_csv(DATA_DIR / "user_features.csv")
    item_features = pd.read_csv(DATA_DIR / "item_features.csv")
    train_interactions = pd.read_csv(DATA_DIR / "train_interactions.csv")

    state_dict, checkpoint_config = _load_checkpoint(DATA_DIR / "two_tower_model.pth")
    model_config = checkpoint_config or _infer_model_config(state_dict)

    model = TwoTowerModel(
        num_users=int(user_features["UserIndex"].max()) + 1,
        num_items=int(item_features["ItemIndex"].max()) + 1,
        num_categories=int(item_features["CategoryIdx"].max()) + 1,
        num_colors=int(item_features["ColorIdx"].max()) + 1,
        num_graphics=int(item_features["GraphicIdx"].max()) + 1,
        **_extra_model_kwargs_from_checkpoint(state_dict),
        **model_config,
    )
    model.load_state_dict(state_dict)
    model.eval()

    item_idx = torch.tensor(item_features["ItemIndex"].to_numpy(), dtype=torch.long)
    item_cat = torch.tensor(item_features["CategoryIdx"].to_numpy(), dtype=torch.long)
    item_color = torch.tensor(item_features["ColorIdx"].to_numpy(), dtype=torch.long)
    item_graphic = torch.tensor(item_features["GraphicIdx"].to_numpy(), dtype=torch.long)
    item_product_group = _item_feature_tensor(item_features, "ProductGroupIdx", torch.long)
    item_section = _item_feature_tensor(item_features, "SectionIdx", torch.long)
    item_garment_group = _item_feature_tensor(item_features, "GarmentGroupIdx", torch.long)
    item_price = torch.tensor(item_features["NormPrice"].to_numpy(), dtype=torch.float32)
    item_popularity = _item_feature_tensor(item_features, "NormPopularity", torch.float32)

    with torch.no_grad():
        item_vectors = model.encode_item(
            item_idx,
            item_cat,
            item_color,
            item_graphic,
            item_price,
            item_product_group,
            item_section,
            item_garment_group,
            item_popularity,
        )

    active_users = train_interactions["UserIndex"].value_counts()
    fallback_user_idx = int(active_users.index[0]) if not active_users.empty else 0
    user_price_map = {
        str(row.UserId): float(row.NormAvgPrice)
        for row in user_features[["UserId", "NormAvgPrice"]].itertuples(index=False)
    }
    user_idx_to_price = {
        int(row.UserIndex): float(row.NormAvgPrice)
        for row in user_features[["UserIndex", "NormAvgPrice"]].itertuples(index=False)
    }

    app_state.update(
        {
            "encoders": encoders,
            "user_le": encoders["user_le"],
            "model": model,
            "item_vectors": item_vectors,
            "item_popularity": item_popularity,
            "item_indices": item_features["ItemIndex"].astype(int).to_numpy(),
            "item_original_ids": item_features["Id"].astype(int).to_numpy(),
            "storefront_mask": _load_storefront_filter(item_features),
            "seen_items": _build_seen_items(train_interactions),
            "user_price_map": user_price_map,
            "user_idx_to_price": user_idx_to_price,
            "fallback_user_idx": fallback_user_idx,
        }
    )
    print(f"Outfitly Recommendation API ready. Items loaded: {len(item_features):,}")
    yield
    app_state.clear()


app = FastAPI(lifespan=lifespan, title="Outfitly Recommendation API")


@app.get("/health")
def health():
    """Return a quick status check for the recommendation service."""
    return {
        "status": "ok",
        "items_loaded": len(app_state.get("item_original_ids", [])),
        "storefront_filter": app_state.get("storefront_mask") is not None,
    }


@app.get("/recommend/{user_id}")
def recommend(
    user_id: str,
    top_k: int = Query(DEFAULT_TOP_K, ge=1, le=MAX_TOP_K),
    exclude_seen: bool = True,
    storefront_only: bool = True,
    rerank: bool = True,
    rerank_pool_size: int = Query(200, ge=1, le=1000),
    popularity_weight: float = Query(0.10, ge=0.0, le=1.0),
):
    """Return top product recommendations with optional popularity reranking."""
    if not app_state:
        raise HTTPException(status_code=503, detail="Recommendation service is still starting")

    model: TwoTowerModel = app_state["model"]
    user_le = app_state["user_le"]
    user_price_map: dict[str, float] = app_state["user_price_map"]
    user_idx_to_price: dict[int, float] = app_state["user_idx_to_price"]
    item_vectors: torch.Tensor = app_state["item_vectors"]
    item_popularity: torch.Tensor = app_state["item_popularity"]
    item_indices = app_state["item_indices"]
    item_original_ids = app_state["item_original_ids"]

    try:
        user_idx = int(user_le.transform([user_id])[0])
        norm_price = user_price_map.get(user_id, user_idx_to_price.get(user_idx, 0.0))
        cold_start = False
    except Exception:
        user_idx = int(app_state["fallback_user_idx"])
        norm_price = user_idx_to_price.get(user_idx, 0.0)
        cold_start = True

    with torch.no_grad():
        user_vector = model.encode_user(
            torch.tensor([user_idx], dtype=torch.long),
            torch.tensor([norm_price], dtype=torch.float32),
        )
        scores = torch.matmul(user_vector, item_vectors.t()).squeeze(0)

    if storefront_only and app_state.get("storefront_mask") is not None:
        scores = scores.masked_fill(~app_state["storefront_mask"], float("-inf"))

    if exclude_seen and not cold_start:
        seen_items = app_state["seen_items"].get(user_idx, set())
        if seen_items:
            item_index_to_row = {int(item_idx): row for row, item_idx in enumerate(item_indices)}
            seen_rows = [item_index_to_row[item_idx] for item_idx in seen_items if item_idx in item_index_to_row]
            if seen_rows:
                scores[torch.tensor(seen_rows, dtype=torch.long)] = float("-inf")

    valid_count = int(torch.isfinite(scores).sum().item())
    if valid_count == 0:
        raise HTTPException(status_code=404, detail="No recommendation candidates available")

    result_count = min(top_k, valid_count)
    if rerank and popularity_weight > 0:
        candidate_count = min(max(result_count, rerank_pool_size), valid_count)
        candidate_scores, candidate_indices = torch.topk(scores, candidate_count)
        rerank_scores = candidate_scores + popularity_weight * item_popularity[candidate_indices]
        top_scores, rerank_indices = torch.topk(rerank_scores, result_count)
        top_indices = candidate_indices[rerank_indices]
    else:
        top_scores, top_indices = torch.topk(scores, result_count)
    recommendations = [
        {"product_id": int(item_original_ids[idx.item()]), "score": float(score.item())}
        for score, idx in zip(top_scores, top_indices)
    ]

    return {
        "user_id": user_id,
        "cold_start": cold_start,
        "recommendations": recommendations,
    }


@app.post("/chat")
def chat(request: ChatRequest):
    """Answer product and policy questions using the Gemini RAG assistant."""
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    return RagChatbot.answer_chat(
        message=message,
        user_id=request.user_id,
        top_k=request.top_k,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
