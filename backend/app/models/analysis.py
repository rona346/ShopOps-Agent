"""
Pydantic Schemas for Inventory Analysis and Reorder Planning.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class StockStatus(str, Enum):
    """Classification of product inventory level."""
    OUT_OF_STOCK = "out_of_stock"
    LOW_STOCK = "low_stock"
    NORMAL = "normal"
    OVERSTOCK = "overstock"


class ProductAnalysisItem(BaseModel):
    """Detailed deterministic analysis of an individual product."""
    product_id: str = Field(..., description="Unique product document identifier")
    sku: str = Field(..., description="Stock Keeping Unit")
    name: str = Field(..., description="Product name")
    category: str = Field(..., description="Product category")
    current_quantity: int = Field(..., description="Current available stock")
    reorder_point: int = Field(..., description="Reorder trigger threshold")
    unit: str = Field(..., description="Unit of measurement")
    unit_cost: Optional[float] = Field(default=None, description="Cost per unit if recorded")
    status: StockStatus = Field(..., description="Deterministic stock status")
    recommended_reorder_quantity: int = Field(
        ..., description="Recommended replenishment units (0 if healthy or overstocked)"
    )
    estimated_reorder_cost: Optional[float] = Field(
        default=None, description="Estimated cost for recommended reorder quantity"
    )
    reason: str = Field(..., description="Deterministic rationale for recommendation and status")


class InventoryAnalysisSummary(BaseModel):
    """Aggregated metrics across analyzed inventory products."""
    total_products: int = Field(..., description="Total products evaluated")
    total_inventory_units: int = Field(..., description="Sum of all units on hand")
    out_of_stock_count: int = Field(..., description="Number of products with 0 stock")
    low_stock_count: int = Field(
        ..., description="Number of products with quantity <= reorder_point (including out of stock)"
    )
    normal_stock_count: int = Field(..., description="Number of products at healthy stock levels")
    overstock_count: int = Field(..., description="Number of products flagged as potential overstock")
    total_recommended_reorder_units: int = Field(
        ..., description="Sum of recommended reorder units across all items"
    )
    estimated_total_reorder_cost: float = Field(
        ..., description="Total cost required to replenish all recommended stock"
    )
    items: List[ProductAnalysisItem] = Field(..., description="Per-product analysis records")


class ReorderRecommendationsResponse(BaseModel):
    """Filtered response containing only products requiring replenishment."""
    total_items_to_reorder: int = Field(..., description="Count of products needing reorder")
    total_recommended_units: int = Field(..., description="Total replenishment units recommended")
    estimated_total_cost: float = Field(..., description="Estimated total replenishment cost")
    items: List[ProductAnalysisItem] = Field(
        ..., description="Items with recommended_reorder_quantity > 0"
    )
