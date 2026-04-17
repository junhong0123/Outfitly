"""
Outfitly Retrieval API
======================
FastAPI service exposing the Recommendation Engine.
"""

import os
import pickle
import pandas as pd
import torch
import torch.nn as nn
from fastapi import FastAPI, HTTPException
import uvicorn
from contextlib import asynccontextmanager

# -----------------
# 1. Model Definition (Must match TwoTowerModel exactly)
# -----------------
class TwoTowerModel(nn.Module):
    def __init__(self, num_users, num_items, num_categories, num_colors, num_graphics, emb_dim=32, out_dim=64):
        super(TwoTowerModel, self).__init__()
        self.user_emb = nn.Embedding(num_users, emb_dim)
        self.user_dense = nn.Sequential(nn.Linear(emb_dim + 1, 128), nn.ReLU(), nn.Dropout(0.2), nn.Linear(128, out_dim))
        
        self.item_emb = nn.Embedding(num_items, emb_dim)
        self.cat_emb = nn.Embedding(num_categories, 16)
        self.color_emb = nn.Embedding(num_colors, 16)
        self.graphic_emb = nn.Embedding(num_graphics, 16)
        self.item_dense = nn.Sequential(nn.Linear(emb_dim + 16 * 3 + 1, 128), nn.ReLU(), nn.Dropout(0.2), nn.Linear(128, out_dim))
        
    def forward_user(self, user_idx, user_norm_price):
        u_e = self.user_emb(user_idx)
        u_in = torch.cat([u_e, user_norm_price.unsqueeze(1)], dim=1)
        return self.user_dense(u_in)

    def forward_item(self, item_idx, item_cat, item_color, item_graphic, item_norm_price):
        i_e = self.item_emb(item_idx)
        c_e = self.cat_emb(item_cat)
        co_e = self.color_emb(item_color)
        g_e = self.graphic_emb(item_graphic)
        i_in = torch.cat([i_e, c_e, co_e, g_e, item_norm_price.unsqueeze(1)], dim=1)
        return self.item_dense(i_in)


# -----------------
# Global State
# -----------------
app_state = {}
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model and compute item embeddings at startup."""
    print("Starting Outfitly Recommendation Service...")
    
    # 1. Load encoders
    encoder_path = os.path.join(DATA_DIR, "encoders.pkl")
    if not os.path.exists(encoder_path):
        raise RuntimeError("encoders.pkl missing. Please run feature_engineering first.")
        
    with open(encoder_path, "rb") as f:
        encoders = pickle.load(f)
    app_state["encoders"] = encoders
    app_state["user_le"] = encoders["user_le"]
    app_state["item_le"] = encoders["item_le"]
    
    # 2. Load user and item data
    user_feats = pd.read_csv(os.path.join(DATA_DIR, "user_features.csv"))
    item_feats = pd.read_csv(os.path.join(DATA_DIR, "item_features.csv"))
    
    app_state["user_feats"] = user_feats
    app_state["item_feats"] = item_feats
    
    # Pre-lookup dictionary for fast user query
    # Str UserId -> NormAvgPrice
    app_state["user_price_map"] = {
        row.UserId: row.NormAvgPrice 
        for row in user_feats.itertuples()
    }
    
    # 3. Initialize Model Structure
    num_users = user_feats["UserIndex"].max() + 1
    num_items = item_feats["ItemIndex"].max() + 1
    num_categories = item_feats["CategoryIdx"].max() + 1
    num_colors = item_feats["ColorIdx"].max() + 1
    num_graphics = item_feats["GraphicIdx"].max() + 1
    
    model = TwoTowerModel(num_users, num_items, num_categories, num_colors, num_graphics)
    
    # Load Weights
    model_path = os.path.join(DATA_DIR, "two_tower_model.pth")
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
        model.eval()
        print(f"Loaded trained model weights: {model_path}")
    else:
        print("WARNING: two_tower_model.pth missing. Using untrained random weights.")
    
    app_state["model"] = model
    
    # 4. Precompute Item Embeddings for fast Cosine Similarity
    print("Precomputing all Item Embeddings...")
    with torch.no_grad():
        i_idx = torch.tensor(item_feats["ItemIndex"].values, dtype=torch.long)
        i_cat = torch.tensor(item_feats["CategoryIdx"].values, dtype=torch.long)
        i_col = torch.tensor(item_feats["ColorIdx"].values, dtype=torch.long)
        i_gra = torch.tensor(item_feats["GraphicIdx"].values, dtype=torch.long)
        i_pri = torch.tensor(item_feats["NormPrice"].values, dtype=torch.float)
        
        # This gives a [num_items, 64] matrix of all item embeddings
        item_embs = model.forward_item(i_idx, i_cat, i_col, i_gra, i_pri)
        # Normalize the item embeddings to make cosine similarity a simple dot product
        item_embs_norm = torch.nn.functional.normalize(item_embs, p=2, dim=1)
        app_state["item_embs_norm"] = item_embs_norm
        app_state["item_original_ids"] = item_feats["Id"].values
        
    print("Precomputation ready. API is now active.")
    yield

    # Shutdown
    print("Shutting down Notification Service.")
    app_state.clear()


app = FastAPI(lifespan=lifespan, title="Outfitly Recommendation API")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/recommend/{user_id}")
def recommend(user_id: str, top_k: int = 10):
    """
    Given a UserId (Guid string), generate Top-K ProductId recommendations.
    """
    model = app_state["model"]
    user_le = app_state["user_le"]
    user_price_map = app_state["user_price_map"]
    item_embs_norm = app_state["item_embs_norm"]
    item_original_ids = app_state["item_original_ids"]
    
    # 1. Look up User
    try:
        user_idx = user_le.transform([user_id])[0]
        norm_price = user_price_map.get(user_id, 0.0)
    except Exception:
        # Unknown user => Cold Start
        user_idx = 0  # fallback to an arbitrary user or average embedding
        norm_price = 0.0

    # 2. Compute User Embedding
    with torch.no_grad():
        u_idx_t = torch.tensor([user_idx], dtype=torch.long)
        u_pri_t = torch.tensor([norm_price], dtype=torch.float)
        
        user_emb = model.forward_user(u_idx_t, u_pri_t)  # [1, 64]
        user_emb_norm = torch.nn.functional.normalize(user_emb, p=2, dim=1)  # [1, 64]
        
    # 3. Cosine Similarity (Dot product of normalized vectors)
    # user_emb_norm: [1, 64], item_embs_norm: [num_items, 64]
    # Matrix multiplication -> [1, num_items]
    similarities = torch.mm(user_emb_norm, item_embs_norm.t()).squeeze(0)  # [num_items]
    
    # 4. Top K
    topk_sim, topk_indices = torch.topk(similarities, top_k)
    
    topk_product_ids = [int(item_original_ids[idx.item()]) for idx in topk_indices]
    
    return {
        "user_id": user_id,
        "recommendations": topk_product_ids
    }

if __name__ == "__main__":
    print("To run the server: uvicorn api:app --reload")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
