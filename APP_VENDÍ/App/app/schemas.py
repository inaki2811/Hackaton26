from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class BusinessRead(BusinessCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    sku: str | None = Field(default=None, max_length=80)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    stock_quantity: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=3)
    reorder_point: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=3)


class ProductRead(ProductCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    is_active: bool


class SaleItemCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class SaleCreate(BaseModel):
    payment_method: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=500)
    items: list[SaleItemCreate] = Field(min_length=1, max_length=100)


class SaleItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    quantity: Decimal
    unit_price: Decimal


class SaleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    sold_at: datetime
    payment_method: str | None
    notes: str | None
    items: list[SaleItemRead]


class InventoryAdjustment(BaseModel):
    quantity_delta: Decimal = Field(max_digits=12, decimal_places=3)
    reason: str = Field(pattern="^(purchase|adjustment|return)$")
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("quantity_delta")
    @classmethod
    def quantity_delta_must_not_be_zero(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("quantity_delta no puede ser cero")
        return value


class ExpenseCreate(BaseModel):
    description: str = Field(min_length=1, max_length=240)
    category: str | None = Field(default=None, max_length=80)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    occurred_at: datetime | None = None


class ExpenseRead(ExpenseCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=254)
    address: str | None = Field(default=None, max_length=300)


class SupplierRead(SupplierCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID


class AssistantQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
