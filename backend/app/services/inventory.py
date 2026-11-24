"""
Firestore Inventory Service and Repository Interfaces.
Keeps database access separate from API endpoints.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from app.core import firebase
from app.models.inventory import Product, ProductCreate, ProductUpdate


class InventoryServiceError(Exception):
    """Base exception for inventory service operations."""
    pass


class ProductNotFoundError(InventoryServiceError):
    """Raised when a product with the given ID cannot be found."""
    pass


class DuplicateSKUError(InventoryServiceError):
    """Raised when a product SKU already exists in the catalog."""
    pass


class FirebaseUnavailableError(InventoryServiceError):
    """Raised when Firestore is unconfigured or unreachable."""
    pass


class InventoryServiceInterface(ABC):
    """Abstract interface defining the inventory repository contract."""

    @abstractmethod
    def create_product(self, product_in: ProductCreate) -> Product:
        """Create a new product, enforcing unique SKU."""
        pass

    @abstractmethod
    def get_product(self, product_id: str) -> Product:
        """Retrieve a product by its ID or raise ProductNotFoundError."""
        pass

    @abstractmethod
    def list_products(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        low_stock: Optional[bool] = None,
    ) -> Tuple[List[Product], int]:
        """List products with pagination, search, and low-stock filters."""
        pass

    @abstractmethod
    def update_product(self, product_id: str, product_update: ProductUpdate) -> Product:
        """Update selected fields of an existing product."""
        pass

    @abstractmethod
    def delete_product(self, product_id: str) -> None:
        """Delete an existing product by its ID."""
        pass

    @abstractmethod
    def get_low_stock_products(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Product], int]:
        """Retrieve products whose quantity is less than or equal to reorder point."""
        pass


class FirestoreInventoryService(InventoryServiceInterface):
    """
    Production inventory service utilizing Firebase Firestore.
    Uses lazy initialization and raises FirebaseUnavailableError when unconfigured.
    """

    COLLECTION_NAME = "inventory_products"

    def _get_db(self):
        """Retrieve Firestore client or raise clean service-unavailable exception."""
        if not firebase.is_firebase_configured():
            raise FirebaseUnavailableError(
                "Firestore service is currently unavailable. "
                "Firebase credentials are not configured in backend/.env."
            )
        try:
            return firebase.get_firestore_client()
        except Exception as e:
            raise FirebaseUnavailableError(
                "Failed to connect to Firestore. Verify Firebase configuration and permissions."
            ) from e

    def create_product(self, product_in: ProductCreate) -> Product:
        db = self._get_db()
        sku_normalized = product_in.sku

        # Enforce unique SKU check across the inventory collection
        existing = (
            db.collection(self.COLLECTION_NAME)
            .where("sku", "==", sku_normalized)
            .limit(1)
            .get()
        )
        if any(existing):
            raise DuplicateSKUError(f"Product with SKU '{sku_normalized}' already exists.")

        now = datetime.now(timezone.utc)
        doc_data = product_in.model_dump()
        doc_data["created_at"] = now.isoformat()
        doc_data["updated_at"] = now.isoformat()

        doc_ref = db.collection(self.COLLECTION_NAME).document()
        doc_ref.set(doc_data)

        return Product(id=doc_ref.id, **doc_data)

    def get_product(self, product_id: str) -> Product:
        db = self._get_db()
        doc = db.collection(self.COLLECTION_NAME).document(product_id).get()
        if not doc.exists:
            raise ProductNotFoundError(f"Product with ID '{product_id}' was not found.")
        data = doc.to_dict() or {}
        return Product(id=doc.id, **data)

    def list_products(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        low_stock: Optional[bool] = None,
    ) -> Tuple[List[Product], int]:
        db = self._get_db()
        docs = db.collection(self.COLLECTION_NAME).stream()

        matched: List[Product] = []
        for doc in docs:
            data = doc.to_dict() or {}
            product = Product(id=doc.id, **data)

            if search:
                term = search.strip().lower()
                if term not in product.name.lower() and term not in product.sku.lower():
                    continue

            if low_stock is not None:
                if low_stock and not product.is_low_stock:
                    continue
                if not low_stock and product.is_low_stock:
                    continue

            matched.append(product)

        # Sort newest first
        matched.sort(key=lambda p: p.created_at, reverse=True)
        total = len(matched)
        return matched[offset : offset + limit], total

    def update_product(self, product_id: str, product_update: ProductUpdate) -> Product:
        db = self._get_db()
        doc_ref = db.collection(self.COLLECTION_NAME).document(product_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise ProductNotFoundError(f"Product with ID '{product_id}' was not found.")

        current_data = doc.to_dict() or {}
        update_fields = product_update.model_dump(exclude_unset=True)

        if not update_fields:
            return Product(id=doc.id, **current_data)

        # If SKU is updated, ensure it is not taken by another product
        if "sku" in update_fields and update_fields["sku"] != current_data.get("sku"):
            new_sku = update_fields["sku"]
            existing = (
                db.collection(self.COLLECTION_NAME)
                .where("sku", "==", new_sku)
                .limit(2)
                .get()
            )
            for item in existing:
                if item.id != product_id:
                    raise DuplicateSKUError(f"Product with SKU '{new_sku}' already exists.")

        now = datetime.now(timezone.utc)
        update_fields["updated_at"] = now.isoformat()

        doc_ref.update(update_fields)
        current_data.update(update_fields)
        return Product(id=product_id, **current_data)

    def delete_product(self, product_id: str) -> None:
        db = self._get_db()
        doc_ref = db.collection(self.COLLECTION_NAME).document(product_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise ProductNotFoundError(f"Product with ID '{product_id}' was not found.")
        doc_ref.delete()

    def get_low_stock_products(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Product], int]:
        return self.list_products(limit=limit, offset=offset, low_stock=True)


def get_inventory_service() -> InventoryServiceInterface:
    """Dependency injection provider for the inventory service."""
    from app.core.supabase import is_supabase_configured
    if is_supabase_configured():
        from app.services.supabase_inventory import SupabaseInventoryService
        return SupabaseInventoryService()
    return FirestoreInventoryService()
