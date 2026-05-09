"""Shared Two-Tower model used by training and the FastAPI service."""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class TwoTowerModel(nn.Module):
    def __init__(
        self,
        num_users: int,
        num_items: int,
        num_categories: int,
        num_colors: int,
        num_graphics: int,
        num_product_groups: int | None = None,
        num_sections: int | None = None,
        num_garment_groups: int | None = None,
        num_club_statuses: int | None = None,
        num_fashion_frequencies: int | None = None,
        num_recent_categories: int | None = None,
        num_recent_colors: int | None = None,
        num_recent_product_groups: int | None = None,
        num_recent_sections: int | None = None,
        num_recent_garment_groups: int | None = None,
        num_sales_channels: int | None = None,
        use_item_popularity: bool = False,
        emb_dim: int = 64,
        out_dim: int = 128,
        hidden_dim: int = 256,
        tag_emb_dim: int = 32,
        dropout: float = 0.1,
    ) -> None:
        """Create the user tower and item tower layers used for recommendation matching."""
        super().__init__()
        self.user_emb = nn.Embedding(num_users, emb_dim)
        self.use_extended_user_features = all(
            value is not None and value > 0
            for value in [
                num_club_statuses,
                num_fashion_frequencies,
                num_recent_categories,
                num_recent_colors,
                num_recent_product_groups,
                num_recent_sections,
                num_recent_garment_groups,
                num_sales_channels,
            ]
        )
        user_tag_count = 0
        user_numeric_count = 1
        if self.use_extended_user_features:
            self.club_status_emb = nn.Embedding(num_club_statuses, tag_emb_dim)
            self.fashion_frequency_emb = nn.Embedding(num_fashion_frequencies, tag_emb_dim)
            self.recent_category_emb = nn.Embedding(num_recent_categories, tag_emb_dim)
            self.recent_color_emb = nn.Embedding(num_recent_colors, tag_emb_dim)
            self.recent_product_group_emb = nn.Embedding(num_recent_product_groups, tag_emb_dim)
            self.recent_section_emb = nn.Embedding(num_recent_sections, tag_emb_dim)
            self.recent_garment_group_emb = nn.Embedding(num_recent_garment_groups, tag_emb_dim)
            self.recent_sales_channel_emb = nn.Embedding(num_sales_channels, tag_emb_dim)
            user_tag_count = 8
            user_numeric_count = 7
        self.user_dense = nn.Sequential(
            nn.Linear(emb_dim + tag_emb_dim * user_tag_count + user_numeric_count, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, out_dim),
        )

        self.item_emb = nn.Embedding(num_items, emb_dim)
        self.cat_emb = nn.Embedding(num_categories, tag_emb_dim)
        self.color_emb = nn.Embedding(num_colors, tag_emb_dim)
        self.graphic_emb = nn.Embedding(num_graphics, tag_emb_dim)
        self.use_extended_item_features = all(
            value is not None and value > 0
            for value in [num_product_groups, num_sections, num_garment_groups]
        )
        item_tag_count = 3
        if self.use_extended_item_features:
            self.product_group_emb = nn.Embedding(num_product_groups, tag_emb_dim)
            self.section_emb = nn.Embedding(num_sections, tag_emb_dim)
            self.garment_group_emb = nn.Embedding(num_garment_groups, tag_emb_dim)
            item_tag_count = 6
        self.use_item_popularity = use_item_popularity
        item_numeric_count = 2 if self.use_item_popularity else 1
        self.item_dense = nn.Sequential(
            nn.Linear(emb_dim + tag_emb_dim * item_tag_count + item_numeric_count, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, out_dim),
        )

    def forward_user(
        self,
        user_idx: torch.Tensor,
        user_norm_price: torch.Tensor,
        user_norm_age: torch.Tensor | None = None,
        user_fn: torch.Tensor | None = None,
        user_active: torch.Tensor | None = None,
        user_club_status: torch.Tensor | None = None,
        user_fashion_frequency: torch.Tensor | None = None,
        user_recent_category: torch.Tensor | None = None,
        user_recent_color: torch.Tensor | None = None,
        user_recent_product_group: torch.Tensor | None = None,
        user_recent_section: torch.Tensor | None = None,
        user_recent_garment_group: torch.Tensor | None = None,
        user_recent_sales_channel: torch.Tensor | None = None,
        user_norm_purchase_count: torch.Tensor | None = None,
        user_norm_unique_item_count: torch.Tensor | None = None,
        user_norm_avg_item_popularity: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Convert user IDs and user price preference into dense user vectors."""
        user_embedding = self.user_emb(user_idx)
        user_parts = [user_embedding, user_norm_price.unsqueeze(1)]
        if self.use_extended_user_features:
            if user_norm_age is None:
                user_norm_age = torch.zeros_like(user_norm_price)
            if user_fn is None:
                user_fn = torch.zeros_like(user_norm_price)
            if user_active is None:
                user_active = torch.zeros_like(user_norm_price)
            if user_club_status is None:
                user_club_status = torch.zeros_like(user_idx)
            if user_fashion_frequency is None:
                user_fashion_frequency = torch.zeros_like(user_idx)
            if user_recent_category is None:
                user_recent_category = torch.zeros_like(user_idx)
            if user_recent_color is None:
                user_recent_color = torch.zeros_like(user_idx)
            if user_recent_product_group is None:
                user_recent_product_group = torch.zeros_like(user_idx)
            if user_recent_section is None:
                user_recent_section = torch.zeros_like(user_idx)
            if user_recent_garment_group is None:
                user_recent_garment_group = torch.zeros_like(user_idx)
            if user_recent_sales_channel is None:
                user_recent_sales_channel = torch.zeros_like(user_idx)
            if user_norm_purchase_count is None:
                user_norm_purchase_count = torch.zeros_like(user_norm_price)
            if user_norm_unique_item_count is None:
                user_norm_unique_item_count = torch.zeros_like(user_norm_price)
            if user_norm_avg_item_popularity is None:
                user_norm_avg_item_popularity = torch.zeros_like(user_norm_price)
            user_parts.extend(
                [
                    user_norm_age.unsqueeze(1),
                    user_fn.unsqueeze(1),
                    user_active.unsqueeze(1),
                    self.club_status_emb(user_club_status),
                    self.fashion_frequency_emb(user_fashion_frequency),
                    self.recent_category_emb(user_recent_category),
                    self.recent_color_emb(user_recent_color),
                    self.recent_product_group_emb(user_recent_product_group),
                    self.recent_section_emb(user_recent_section),
                    self.recent_garment_group_emb(user_recent_garment_group),
                    self.recent_sales_channel_emb(user_recent_sales_channel),
                    user_norm_purchase_count.unsqueeze(1),
                    user_norm_unique_item_count.unsqueeze(1),
                    user_norm_avg_item_popularity.unsqueeze(1),
                ]
            )
        user_input = torch.cat(user_parts, dim=1)
        return self.user_dense(user_input)

    def forward_item(
        self,
        item_idx: torch.Tensor,
        item_cat: torch.Tensor,
        item_color: torch.Tensor,
        item_graphic: torch.Tensor,
        item_norm_price: torch.Tensor,
        item_product_group: torch.Tensor | None = None,
        item_section: torch.Tensor | None = None,
        item_garment_group: torch.Tensor | None = None,
        item_popularity: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Convert item IDs, item tags, and item price into dense item vectors."""
        item_embedding = self.item_emb(item_idx)
        category_embedding = self.cat_emb(item_cat)
        color_embedding = self.color_emb(item_color)
        graphic_embedding = self.graphic_emb(item_graphic)
        item_parts = [
            item_embedding,
            category_embedding,
            color_embedding,
            graphic_embedding,
        ]
        if self.use_extended_item_features:
            if item_product_group is None:
                item_product_group = torch.zeros_like(item_idx)
            if item_section is None:
                item_section = torch.zeros_like(item_idx)
            if item_garment_group is None:
                item_garment_group = torch.zeros_like(item_idx)
            item_parts.extend(
                [
                    self.product_group_emb(item_product_group),
                    self.section_emb(item_section),
                    self.garment_group_emb(item_garment_group),
                ]
            )
        item_parts.append(item_norm_price.unsqueeze(1))
        if self.use_item_popularity:
            if item_popularity is None:
                item_popularity = torch.zeros_like(item_norm_price)
            item_parts.append(item_popularity.unsqueeze(1))
        item_input = torch.cat(item_parts, dim=1)
        return self.item_dense(item_input)

    def encode_user(
        self,
        user_idx: torch.Tensor,
        user_norm_price: torch.Tensor,
        user_norm_age: torch.Tensor | None = None,
        user_fn: torch.Tensor | None = None,
        user_active: torch.Tensor | None = None,
        user_club_status: torch.Tensor | None = None,
        user_fashion_frequency: torch.Tensor | None = None,
        user_recent_category: torch.Tensor | None = None,
        user_recent_color: torch.Tensor | None = None,
        user_recent_product_group: torch.Tensor | None = None,
        user_recent_section: torch.Tensor | None = None,
        user_recent_garment_group: torch.Tensor | None = None,
        user_recent_sales_channel: torch.Tensor | None = None,
        user_norm_purchase_count: torch.Tensor | None = None,
        user_norm_unique_item_count: torch.Tensor | None = None,
        user_norm_avg_item_popularity: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Return normalized user vectors so dot products behave like similarity scores."""
        return F.normalize(
            self.forward_user(
                user_idx,
                user_norm_price,
                user_norm_age,
                user_fn,
                user_active,
                user_club_status,
                user_fashion_frequency,
                user_recent_category,
                user_recent_color,
                user_recent_product_group,
                user_recent_section,
                user_recent_garment_group,
                user_recent_sales_channel,
                user_norm_purchase_count,
                user_norm_unique_item_count,
                user_norm_avg_item_popularity,
            ),
            p=2,
            dim=1,
        )

    def encode_item(
        self,
        item_idx: torch.Tensor,
        item_cat: torch.Tensor,
        item_color: torch.Tensor,
        item_graphic: torch.Tensor,
        item_norm_price: torch.Tensor,
        item_product_group: torch.Tensor | None = None,
        item_section: torch.Tensor | None = None,
        item_garment_group: torch.Tensor | None = None,
        item_popularity: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Return normalized item vectors so they can be compared with user vectors."""
        return F.normalize(
            self.forward_item(
                item_idx,
                item_cat,
                item_color,
                item_graphic,
                item_norm_price,
                item_product_group,
                item_section,
                item_garment_group,
                item_popularity,
            ),
            p=2,
            dim=1,
        )

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        """Score each user-item pair in a batch by vector similarity."""
        user_vector = self.encode_user(
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
        item_vector = self.encode_item(
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
        return torch.sum(user_vector * item_vector, dim=1)
