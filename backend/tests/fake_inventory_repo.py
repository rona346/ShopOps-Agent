"""
Isolated In-Memory Inventory Repository for Testing.
Strictly used for unit and API tests. Never used in production.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from app.models.inventory import Product, ProductCreate, ProductUpdate
from app.services.inventory import (
    DuplicateSKUError,
    InventoryServiceInterface,
    ProductNotFoundError,
)


class InMemoryInventoryRepository(InventoryServiceInterface):
    """Test-only repository implementing InventoryServiceInterface in memory."""

    def __init__(self):
        self._products: Dict[str, Product] = {}

    def clear(self):
        self._products.clear()

    def create_product(self, product_in: ProductCreate) -> Product:
        # Check SKU uniqueness
        for existing in self._products.values():
            if existing.sku == product_in.sku:
                raise DuplicateSKUError(f"Product with SKU '{product_in.sku}' already exists.")

        now = datetime.now(timezone.utc)
        product_id = f"test_{uuid.uuid4().hex[:8]}"
        product = Product(
            id=product_id,
            created_at=now,
            updated_at=now,
            **product_in.model_dump(),
        )
        self._products[product_id] = product
        return product

    def get_product(self, product_id: str) -> Product:
        if product_id not in self._products:
            raise ProductNotFoundError(f"Product with ID '{product_id}' was not found.")
        return self._products[product_id]

    def list_products(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        low_stock: Optional[bool] = None,
    ) -> Tuple[List[Product], int]:
        items = list(self._products.values())

        if search:
            s = search.strip().lower()
            items = [
                p for p in items
                if s in p.name.lower() or s in p.sku.lower()
            ]

        if low_stock is not None:
            if low_stock:
                items = [p for p in items if p.is_low_stock]
            else:
                items = [p for p in items if not p.is_low_stock]

        items.sort(key=lambda p: p.created_at, reverse=True)
        total = len(items)
        return items[offset : offset + limit], total

    def update_product(self, product_id: str, product_update: ProductUpdate) -> Product:
        if product_id not in self._products:
            raise ProductNotFoundError(f"Product with ID '{product_id}' was not found.")

        current = self._products[product_id]
        updates = product_update.model_dump(exclude_unset=True)

        if "sku" in updates and updates["sku"] != current.sku:
            for pid, existing in self._products.items():
                if pid != product_id and existing.sku == updates["sku"]:
                    raise DuplicateSKUError(f"Product with SKU '{updates['sku']}' already exists.")

        now = datetime.now(timezone.utc)
        current_dict = current.model_dump()
        current_dict.update(updates)
        current_dict["updated_at"] = now
        updated = Product(**current_dict)
        self._products[product_id] = updated
        return updated

    def delete_product(self, product_id: str) -> None:
        if product_id not in self._products:
            raise ProductNotFoundError(f"Product with ID '{product_id}' was not found.")
        del self._products[product_id]

    def get_low_stock_products(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Product], int]:
        return self.list_products(limit=limit, offset=offset, low_stock=True)
