from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Expense, Product, Sale, SaleItem


def build_sales_report(session: Session, business_id: UUID, days: int) -> dict:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    products = session.scalars(
        select(Product)
        .where(Product.business_id == business_id, Product.is_active.is_(True))
        .order_by(Product.name)
    ).all()
    sales_rows = session.execute(
        select(
            SaleItem.product_id,
            SaleItem.quantity,
            SaleItem.unit_price,
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(Sale.business_id == business_id, Sale.sold_at >= start)
    ).all()
    product_sales: dict[UUID, dict[str, Decimal]] = {}
    for product_id, quantity, unit_price in sales_rows:
        totals = product_sales.setdefault(
            product_id,
            {"quantity_sold": Decimal("0"), "gross_revenue": Decimal("0")},
        )
        totals["quantity_sold"] += quantity
        totals["gross_revenue"] += quantity * unit_price

    rankings = []
    for product in products:
        result = product_sales.get(product.id, {})
        rankings.append(
            {
                "product_id": str(product.id),
                "product_name": product.name,
                "quantity_sold": result.get("quantity_sold", Decimal("0")),
                "gross_revenue": result.get("gross_revenue", Decimal("0")),
                "stock_quantity": product.stock_quantity,
                "reorder_point": product.reorder_point,
            }
        )

    best_seller = max(
        (item for item in rankings if item["quantity_sold"] > 0),
        key=lambda item: (item["quantity_sold"], item["gross_revenue"]),
        default=None,
    )
    slowest = min(
        rankings,
        key=lambda item: (item["quantity_sold"], item["gross_revenue"]),
        default=None,
    )
    revenue = sum(
        (item["gross_revenue"] for item in rankings), start=Decimal("0")
    )
    expense_amounts = session.scalars(
        select(Expense.amount).where(
            Expense.business_id == business_id, Expense.occurred_at >= start
        )
    ).all()
    expenses = sum(expense_amounts, start=Decimal("0"))
    inventory_alerts = [
        item for item in rankings if item["stock_quantity"] <= item["reorder_point"]
    ]
    opportunity = max(
        (item for item in rankings if item["gross_revenue"] > 0),
        key=lambda item: item["gross_revenue"],
        default=None,
    )

    return {
        "period_days": days,
        "currency": "MXN",
        "gross_revenue": revenue,
        "recorded_expenses": expenses,
        "best_seller": best_seller,
        "slowest_product": slowest,
        "revenue_opportunity": opportunity,
        "opportunity_note": (
            "La oportunidad se basa en ingresos, no en margen: el producto no "
            "tiene costo de compra registrado."
        ),
        "inventory_alerts": inventory_alerts,
        "products": rankings,
    }
