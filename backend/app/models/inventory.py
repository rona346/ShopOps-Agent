from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Product name")
    sku: str = Field(..., min_length=1, max_length=100, description="Stock Keeping Unit")
    category: str = Field(..., min_length=1, max_length=100, description="Product category")
    quantity: int = Field(default=0, ge=0, description="Current stock quantity")
    reorder_point: int = Field(default=10, ge=0, description="Threshold for low stock alert")
    unit: str = Field(default="pcs", min_length=1, max_length=50, description="Unit of measurement")
    unit_cost: Optional[float] = Field(default=None, ge=0.0, description="Cost per unit")
    supplier_name: Optional[str] = Field(default=None, max_length=200, description="Supplier or vendor name")
    description: Optional[str] = Field(default=None, max_length=1000, description="Product description")

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError("Product name cannot be empty or only whitespace")
            return v_stripped
        return v

    @field_validator("sku", mode="before")
    @classmethod
    def normalize_sku(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_normalized = v.strip().upper()
            if not v_normalized:
                raise ValueError("SKU cannot be empty or only whitespace")
            return v_normalized
        return v

    @field_validator("category", "unit", mode="before")
    @classmethod
    def strip_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError("Field cannot be empty or only whitespace")
            return v_stripped
        return v

    @field_validator("supplier_name", "description", mode="before")
    @classmethod
    def strip_optional_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v


class ProductCreate(ProductBase):
    """Schema for creating a new product."""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating an existing product (all fields optional)."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    sku: Optional[str] = Field(default=None, min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    quantity: Optional[int] = Field(default=None, ge=0)
    reorder_point: Optional[int] = Field(default=None, ge=0)
    unit: Optional[str] = Field(default=None, min_length=1, max_length=50)
    unit_cost: Optional[float] = Field(default=None, ge=0.0)
    supplier_name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Any) -> Any:
        if v is not None and isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError("Product name cannot be empty or only whitespace")
            return v_stripped
        return v

    @field_validator("sku", mode="before")
    @classmethod
    def normalize_sku(cls, v: Any) -> Any:
        if v is not None and isinstance(v, str):
            v_normalized = v.strip().upper()
            if not v_normalized:
                raise ValueError("SKU cannot be empty or only whitespace")
            return v_normalized
        return v

    @field_validator("category", "unit", mode="before")
    @classmethod
    def strip_strings(cls, v: Any) -> Any:
        if v is not None and isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError("Field cannot be empty or only whitespace")
            return v_stripped
        return v

    @field_validator("supplier_name", "description", mode="before")
    @classmethod
    def strip_optional_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v


class Product(ProductBase):
    """Domain model representing a product in the database."""
    id: str = Field(..., description="Document identifier")
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> datetime:
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            return v
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v)
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
        return datetime.now(timezone.utc)

    @property
    def is_low_stock(self) -> bool:
        return self.quantity <= self.reorder_point


class ProductResponse(ProductBase):
    """API response schema for a single product."""
    id: str
    created_at: datetime
    updated_at: datetime
    is_low_stock: bool

    @classmethod
    def from_product(cls, product: Product) -> "ProductResponse":
        return cls(
            id=product.id,
            name=product.name,
            sku=product.sku,
            category=product.category,
            quantity=product.quantity,
            reorder_point=product.reorder_point,
            unit=product.unit,
            unit_cost=product.unit_cost,
            supplier_name=product.supplier_name,
            description=product.description,
            created_at=product.created_at,
            updated_at=product.updated_at,
            is_low_stock=product.is_low_stock,
        )


class ProductListResponse(BaseModel):
    """API response schema for paginated product lists."""
    items: List[ProductResponse]
    total: int
    limit: int
    offset: int
