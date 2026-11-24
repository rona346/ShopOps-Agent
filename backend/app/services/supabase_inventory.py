"""
Supabase PostgreSQL Inventory Service and Repository Implementation.
Fulfills InventoryServiceInterface using Supabase PostgREST database operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.supabase import (
    SupabaseDatabaseClient,
    SupabaseQueryError,
    get_supabase_client,
)
from app.models.inventory import (
    Product,
    ProductCreate,
    ProductUpdate,
)
from app.services.inventory import (
    DuplicateSKUError,
    InventoryServiceError,
    InventoryServiceInterface,
    ProductNotFoundError,
)


class SupabaseInventoryService(InventoryServiceInterface):
    """
    Production inventory service utilizing Supabase PostgreSQL table 'inventory_products'.
    Mediates access using privileged backend client.
    """

    TABLE_NAME = "inventory_products"

    def __init__(self, client: Optional[SupabaseDatabaseClient] = None):
        self._client = client

    def _get_client(self) -> SupabaseDatabaseClient:
        if self._client is not None:
            return self._client
        return get_supabase_client()

    def create_product(self, product_in: ProductCreate) -> Product:
        client = self._get_client()
        sku_normalized = product_in.sku

        # Pre-check for duplicate SKU
        existing, _ = client.select(
            self.TABLE_NAME,
            params={"sku": f"eq.{sku_normalized}"},
            limit=1,
        )
        if existing:
            raise DuplicateSKUError(f"Product with SKU '{sku_normalized}' already exists.")

        now = datetime.now(timezone.utc)
        doc_data = product_in.model_dump()
        doc_data["created_at"] = now.isoformat()
        doc_data["updated_at"] = now.isoformat()

        try:
            row = client.insert(self.TABLE_NAME, doc_data)
            return Product(**row)
        except SupabaseQueryError as exc:
            msg = str(exc).lower()
            if "23505" in msg or "uq_inventory_sku" in msg or "duplicate" in msg:
                raise DuplicateSKUError(f"Product with SKU '{sku_normalized}' already exists.") from exc
            raise InventoryServiceError(f"Failed to create product in database: {str(exc)}") from exc

    def get_product(self, product_id: str) -> Product:
        client = self._get_client()
        row = client.get_by_id(self.TABLE_NAME, product_id)
        if not row:
            raise ProductNotFoundError(f"Product with ID '{product_id}' was not found.")
        return Product(**row)

    def list_products(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        low_stock: Optional[bool] = None,
    ) -> Tuple[List[Product], int]:
        client = self._get_client()
        params: Dict[str, str] = {}

        if search:
            s = search.strip()
            params["or"] = f"(name.ilike.*{s}*,sku.ilike.*{s}*)"

        rows, total = client.select(
            self.TABLE_NAME,
            params=params if params else None,
            limit=limit,
            offset=offset,
            order="created_at.desc",
        )

        products = [Product(**r) for r in rows]

        if low_stock is not None:
            filtered = [p for p in products if p.is_low_stock == low_stock]
            return filtered, len(filtered)

        return products, total

    def update_product(self, product_id: str, product_update: ProductUpdate) -> Product:
        client = self._get_client()
        current = self.get_product(product_id)
        current_data = current.model_dump()

        update_fields = {
            k: v for k, v in product_update.model_dump().items() if v is not None
        }
        if not update_fields:
            return current

        # If SKU is updated, ensure it is not taken by another product
        if "sku" in update_fields and update_fields["sku"] != current_data.get("sku"):
            new_sku = update_fields["sku"]
            existing, _ = client.select(
                self.TABLE_NAME,
                params={"sku": f"eq.{new_sku}"},
                limit=2,
            )
            for item in existing:
                if str(item.get("id")) != product_id:
                    raise DuplicateSKUError(f"Product with SKU '{new_sku}' already exists.")

        now = datetime.now(timezone.utc)
        update_fields["updated_at"] = now.isoformat()

        try:
            row = client.update(self.TABLE_NAME, product_id, update_fields)
            return Product(**row)
        except SupabaseQueryError as exc:
            msg = str(exc).lower()
            if "23505" in msg or "uq_inventory_sku" in msg:
                raise DuplicateSKUError(f"Product with SKU '{update_fields.get('sku')}' already exists.") from exc
            raise InventoryServiceError(f"Failed to update product '{product_id}': {str(exc)}") from exc

    def delete_product(self, product_id: str) -> None:
        client = self._get_client()
        # Verify existence
        self.get_product(product_id)
        try:
            client.delete(self.TABLE_NAME, product_id)
        except SupabaseQueryError as exc:
            msg = str(exc).lower()
            if "23503" in msg or "fk_" in msg or "foreign key" in msg:
                raise InventoryServiceError(
                    f"Cannot delete product '{product_id}' because active approval requests or reorder tasks reference it."
                ) from exc
            raise InventoryServiceError(f"Failed to delete product '{product_id}': {str(exc)}") from exc

    def get_low_stock_products(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Product], int]:
        return self.list_products(limit=limit, offset=offset, low_stock=True)
