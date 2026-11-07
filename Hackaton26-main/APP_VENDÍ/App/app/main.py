from contextlib import asynccontextmanager
import logging
import os
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from openai import APIError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from fastapi.staticfiles import StaticFiles

from app.analytics import build_sales_report
from app.assistant import answer_business_question
from app.database import create_database_engine, create_schema
from app.models import (
    Business,
    Expense,
    InventoryMovement,
    Product,
    Sale,
    SaleItem,
    Supplier,
)
from app.schemas import (
    AssistantQuestion,
    BusinessCreate,
    BusinessRead,
    ExpenseCreate,
    ExpenseRead,
    InventoryAdjustment,
    ProductCreate,
    ProductRead,
    SaleCreate,
    SaleRead,
    SupplierCreate,
    SupplierRead,
)

logger = logging.getLogger(__name__)


def create_app(database_url: str | None = None) -> FastAPI:
    engine = create_database_engine(
        database_url or os.getenv("DATABASE_URL", "sqlite:///./vendi.db")
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        create_schema(engine)
        yield
        engine.dispose()

    app = FastAPI(title="Vendí API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.engine = engine

    def get_session():
        with session_factory() as session:
            yield session

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post(
        "/businesses",
        response_model=BusinessRead,
        status_code=status.HTTP_201_CREATED,
    )
    def create_business(payload: BusinessCreate, session: Session = Depends(get_session)):
        business = Business(name=payload.name)
        session.add(business)
        session.commit()
        session.refresh(business)
        return business

    @app.post(
        "/businesses/{business_id}/products",
        response_model=ProductRead,
        status_code=status.HTTP_201_CREATED,
    )
    def create_product(
        business_id: UUID,
        payload: ProductCreate,
        session: Session = Depends(get_session),
    ):
        if session.get(Business, business_id) is None:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        product = Product(business_id=business_id, **payload.model_dump())
        session.add(product)
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(
                status_code=409, detail="Ya existe un producto con ese SKU"
            ) from error
        session.refresh(product)
        return product

    @app.get("/businesses/{business_id}/products", response_model=list[ProductRead])
    def list_products(business_id: UUID, session: Session = Depends(get_session)):
        if session.get(Business, business_id) is None:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        return session.scalars(
            select(Product)
            .where(Product.business_id == business_id, Product.is_active.is_(True))
            .order_by(Product.name)
        ).all()

    @app.post(
        "/businesses/{business_id}/sales",
        response_model=SaleRead,
        status_code=status.HTTP_201_CREATED,
    )
    def create_sale(
        business_id: UUID,
        payload: SaleCreate,
        session: Session = Depends(get_session),
    ):
        if session.get(Business, business_id) is None:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        product_ids = [item.product_id for item in payload.items]
        if len(set(product_ids)) != len(product_ids):
            raise HTTPException(
                status_code=422, detail="No repitas productos en una misma venta"
            )
        products = {
            product.id: product
            for product in session.scalars(
                select(Product).where(
                    Product.business_id == business_id,
                    Product.id.in_(product_ids),
                    Product.is_active.is_(True),
                )
            )
        }
        if len(products) != len(product_ids):
            raise HTTPException(
                status_code=404,
                detail="Uno o más productos no pertenecen a este negocio",
            )
        for item in payload.items:
            product = products[item.product_id]
            if product.stock_quantity < item.quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"Inventario insuficiente para {product.name}",
                )

        sale = Sale(
            business_id=business_id,
            payment_method=payload.payment_method,
            notes=payload.notes,
        )
        for item in payload.items:
            product = products[item.product_id]
            sale.items.append(
                SaleItem(
                    product_id=product.id,
                    quantity=item.quantity,
                    unit_price=(
                        item.unit_price
                        if item.unit_price is not None
                        else product.unit_price
                    ),
                )
            )
            product.stock_quantity -= item.quantity
            session.add(
                InventoryMovement(
                    business_id=business_id,
                    product_id=product.id,
                    quantity_delta=-item.quantity,
                    reason="sale",
                    notes=f"Venta {sale.id}",
                )
            )
        session.add(sale)
        session.commit()
        session.refresh(sale)
        return sale

    @app.post(
        "/businesses/{business_id}/products/{product_id}/inventory",
        response_model=ProductRead,
    )
    def adjust_inventory(
        business_id: UUID,
        product_id: UUID,
        payload: InventoryAdjustment,
        session: Session = Depends(get_session),
    ):
        product = session.scalar(
            select(Product).where(
                Product.id == product_id, Product.business_id == business_id
            )
        )
        if product is None:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        if product.stock_quantity + payload.quantity_delta < Decimal("0"):
            raise HTTPException(
                status_code=409, detail="El inventario no puede quedar negativo"
            )
        product.stock_quantity += payload.quantity_delta
        session.add(
            InventoryMovement(
                business_id=business_id,
                product_id=product_id,
                quantity_delta=payload.quantity_delta,
                reason=payload.reason,
                notes=payload.notes,
            )
        )
        session.commit()
        session.refresh(product)
        return product

    @app.post(
        "/businesses/{business_id}/expenses",
        response_model=ExpenseRead,
        status_code=status.HTTP_201_CREATED,
    )
    def create_expense(
        business_id: UUID,
        payload: ExpenseCreate,
        session: Session = Depends(get_session),
    ):
        if session.get(Business, business_id) is None:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        expense = Expense(business_id=business_id, **payload.model_dump(exclude_none=True))
        session.add(expense)
        session.commit()
        session.refresh(expense)
        return expense

    @app.post(
        "/businesses/{business_id}/suppliers",
        response_model=SupplierRead,
        status_code=status.HTTP_201_CREATED,
    )
    def create_supplier(
        business_id: UUID,
        payload: SupplierCreate,
        session: Session = Depends(get_session),
    ):
        if session.get(Business, business_id) is None:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        supplier = Supplier(business_id=business_id, **payload.model_dump())
        session.add(supplier)
        session.commit()
        session.refresh(supplier)
        return supplier

    @app.get("/businesses/{business_id}/analytics")
    def get_analytics(
        business_id: UUID,
        days: int = Query(default=7, ge=1, le=365),
        session: Session = Depends(get_session),
    ):
        if session.get(Business, business_id) is None:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        return build_sales_report(session, business_id, days)

    @app.post("/businesses/{business_id}/assistant")
    def ask_assistant(
        business_id: UUID,
        payload: AssistantQuestion,
        session: Session = Depends(get_session),
    ):
        if session.get(Business, business_id) is None:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        report = build_sales_report(session, business_id, 7)
        try:
            answer, model = answer_business_question(payload.question, report)
        except APIError as error:
            logger.exception("Error al consultar el proveedor de IA")
            raise HTTPException(
                status_code=502,
                detail="El proveedor de IA no está disponible; inténtalo más tarde",
            ) from error
        except RuntimeError as error:
            logger.exception("Respuesta inválida del proveedor de IA")
            raise HTTPException(status_code=502, detail=str(error)) from error
        return {"answer": answer, "model": model, "data_period_days": 7}

    web_directory = Path(__file__).resolve().parent.parent / "web"
    app.mount("/", StaticFiles(directory=web_directory, html=True), name="web")

    return app


app = create_app()
