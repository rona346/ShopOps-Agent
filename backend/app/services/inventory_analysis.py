"""
Deterministic Inventory Analysis and Reorder Planning Engine.
Performs read-only evaluation of inventory stock levels, calculates deterministic
reorder recommendations, and detects overstock. Completely decoupled from Gemini.
"""

from typing import List, Optional, Tuple
from fastapi import Depends
from app.models.analysis import (
    InventoryAnalysisSummary,
    ProductAnalysisItem,
    ReorderRecommendationsResponse,
    StockStatus,
)
from app.models.inventory import Product
from app.services.inventory import (
    InventoryServiceInterface,
    get_inventory_service,
)


class InventoryAnalysisService:
    """
    Deterministic rules engine for inventory analysis and reorder planning.
    Rules:
    - OUT_OF_STOCK: quantity == 0
    - LOW_STOCK: 0 < quantity <= reorder_point
    - OVERSTOCK: quantity > (reorder_point * 3) if reorder_point > 0 else quantity > 50
    - NORMAL: reorder_point < quantity <= overstock threshold
    - TARGET_STOCK: max(reorder_point * 2, 10)
    - RECOMMENDED_REORDER: max(0, target_stock - quantity) when quantity <= reorder_point, else 0
    """

    OVERSTOCK_MULTIPLIER: int = 3
    DEFAULT_OVERSTOCK_THRESHOLD: int = 50
    TARGET_STOCK_MULTIPLIER: int = 2
    MIN_TARGET_STOCK: int = 10

    def __init__(self, inventory_service: InventoryServiceInterface):
        self.inventory_service = inventory_service

    def determine_stock_status(self, quantity: int, reorder_point: int) -> StockStatus:
        """Classify inventory level into a discrete deterministic stock status."""
        if quantity == 0:
            return StockStatus.OUT_OF_STOCK
        if quantity <= reorder_point:
            return StockStatus.LOW_STOCK

        threshold = (
            reorder_point * self.OVERSTOCK_MULTIPLIER
            if reorder_point > 0
            else self.DEFAULT_OVERSTOCK_THRESHOLD
        )
        if quantity > threshold:
            return StockStatus.OVERSTOCK

        return StockStatus.NORMAL

    def calculate_reorder_recommendation(
        self, quantity: int, reorder_point: int
    ) -> Tuple[int, str]:
        """
        Calculate deterministic replenishment units and explanation.
        Does not modify database records.
        """
        target_stock = max(reorder_point * self.TARGET_STOCK_MULTIPLIER, self.MIN_TARGET_STOCK)

        if quantity == 0:
            recommended = target_stock
            reason = (
                f"Product is completely out of stock (0 units on hand). "
                f"Urgent reorder of {recommended} units recommended to establish target stock of {target_stock}."
            )
            return recommended, reason

        if quantity <= reorder_point:
            recommended = max(0, target_stock - quantity)
            reason = (
                f"Stock level ({quantity}) is at or below reorder threshold ({reorder_point}). "
                f"Reorder of {recommended} units recommended to restore operating stock to {target_stock}."
            )
            return recommended, reason

        overstock_threshold = (
            reorder_point * self.OVERSTOCK_MULTIPLIER
            if reorder_point > 0
            else self.DEFAULT_OVERSTOCK_THRESHOLD
        )
        if quantity > overstock_threshold:
            reason = (
                f"Potential overstock: stock level ({quantity}) exceeds 3x reorder threshold ({overstock_threshold}). "
                f"Excess working capital tied up; no replenishment recommended."
            )
            return 0, reason

        reason = (
            f"Stock level ({quantity}) is healthy (above reorder threshold of {reorder_point}). "
            f"No replenishment needed."
        )
        return 0, reason

    def analyze_product(self, product: Product) -> ProductAnalysisItem:
        """Evaluate an individual product and compute metrics."""
        status = self.determine_stock_status(product.quantity, product.reorder_point)
        reorder_qty, reason = self.calculate_reorder_recommendation(
            product.quantity, product.reorder_point
        )

        estimated_cost: Optional[float] = None
        if product.unit_cost is not None and reorder_qty > 0:
            estimated_cost = round(reorder_qty * product.unit_cost, 2)

        return ProductAnalysisItem(
            product_id=product.id,
            sku=product.sku,
            name=product.name,
            category=product.category,
            current_quantity=product.quantity,
            reorder_point=product.reorder_point,
            unit=product.unit,
            unit_cost=product.unit_cost,
            status=status,
            recommended_reorder_quantity=reorder_qty,
            estimated_reorder_cost=estimated_cost,
            reason=reason,
        )

    def analyze_inventory(self, category: Optional[str] = None) -> InventoryAnalysisSummary:
        """
        Evaluate full inventory catalog and produce aggregated summary.
        Read-only; does not write to the database or trigger purchases.
        """
        products, _ = self.inventory_service.list_products(limit=1000, offset=0)

        if category:
            cat_norm = category.strip().lower()
            products = [p for p in products if p.category.lower() == cat_norm]

        items: List[ProductAnalysisItem] = []
        total_units = 0
        out_of_stock_count = 0
        low_stock_count = 0
        normal_stock_count = 0
        overstock_count = 0
        total_reorder_units = 0
        total_reorder_cost = 0.0

        for product in products:
            item = self.analyze_product(product)
            items.append(item)

            total_units += item.current_quantity

            if item.status == StockStatus.OUT_OF_STOCK:
                out_of_stock_count += 1
                low_stock_count += 1
            elif item.status == StockStatus.LOW_STOCK:
                low_stock_count += 1
            elif item.status == StockStatus.OVERSTOCK:
                overstock_count += 1
            else:
                normal_stock_count += 1

            total_reorder_units += item.recommended_reorder_quantity
            if item.estimated_reorder_cost is not None:
                total_reorder_cost += item.estimated_reorder_cost

        return InventoryAnalysisSummary(
            total_products=len(items),
            total_inventory_units=total_units,
            out_of_stock_count=out_of_stock_count,
            low_stock_count=low_stock_count,
            normal_stock_count=normal_stock_count,
            overstock_count=overstock_count,
            total_recommended_reorder_units=total_reorder_units,
            estimated_total_reorder_cost=round(total_reorder_cost, 2),
            items=items,
        )

    def get_reorder_recommendations(
        self, category: Optional[str] = None
    ) -> ReorderRecommendationsResponse:
        """
        Filter analysis for products requiring replenishment.
        """
        summary = self.analyze_inventory(category=category)
        reorder_items = [
            item for item in summary.items if item.recommended_reorder_quantity > 0
        ]
        total_units = sum(i.recommended_reorder_quantity for i in reorder_items)
        total_cost = sum(i.estimated_reorder_cost or 0.0 for i in reorder_items)

        return ReorderRecommendationsResponse(
            total_items_to_reorder=len(reorder_items),
            total_recommended_units=total_units,
            estimated_total_cost=round(total_cost, 2),
            items=reorder_items,
        )


def get_inventory_analysis_service(
    inventory_service: InventoryServiceInterface = Depends(get_inventory_service),
) -> InventoryAnalysisService:
    """Dependency provider for InventoryAnalysisService."""
    return InventoryAnalysisService(inventory_service=inventory_service)
