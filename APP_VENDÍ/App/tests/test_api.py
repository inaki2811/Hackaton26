import pytest
from fastapi.testclient import TestClient

from app.assistant import answer_business_question
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}")
    with TestClient(app) as test_client:
        yield test_client


def create_business(client: TestClient) -> str:
    response = client.post("/businesses", json={"name": "Tienda de prueba"})
    assert response.status_code == 201
    return response.json()["id"]


def test_health_and_in_memory_database():
    app = create_app("sqlite:///:memory:")
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert create_business(client)


def test_demo_frontend_is_served_from_api(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}")
    with TestClient(app) as client:
        page = client.get("/")
        script = client.get("/app.js")
        stylesheet = client.get("/styles.css")

    assert page.status_code == 200
    assert "Vendí" in page.text
    assert script.status_code == 200
    assert "businesses" in script.text
    assert stylesheet.status_code == 200
    assert "@media" in stylesheet.text


def test_sale_updates_inventory_and_analytics(client):
    business_id = create_business(client)
    product_response = client.post(
        f"/businesses/{business_id}/products",
        json={
            "name": "Café",
            "unit_price": "45.50",
            "stock_quantity": "10",
            "reorder_point": "2",
        },
    )
    assert product_response.status_code == 201
    product_id = product_response.json()["id"]

    sale_response = client.post(
        f"/businesses/{business_id}/sales",
        json={"items": [{"product_id": product_id, "quantity": "3"}]},
    )
    assert sale_response.status_code == 201
    assert sale_response.json()["items"][0]["unit_price"] == "45.50"

    products = client.get(f"/businesses/{business_id}/products").json()
    assert products[0]["stock_quantity"] == "7.000"
    report = client.get(f"/businesses/{business_id}/analytics").json()
    assert report["gross_revenue"] == 136.5
    assert report["best_seller"]["product_name"] == "Café"
    assert report["best_seller"]["quantity_sold"] == 3
    assert report["slowest_product"]["quantity_sold"] == 3


def test_sale_rejects_insufficient_stock_without_partial_changes(client):
    business_id = create_business(client)
    product_id = client.post(
        f"/businesses/{business_id}/products",
        json={"name": "Pan", "unit_price": "10", "stock_quantity": "1"},
    ).json()["id"]

    response = client.post(
        f"/businesses/{business_id}/sales",
        json={"items": [{"product_id": product_id, "quantity": "2"}]},
    )

    assert response.status_code == 409
    product = client.get(f"/businesses/{business_id}/products").json()[0]
    assert product["stock_quantity"] == "1.000"
    assert client.get(f"/businesses/{business_id}/analytics").json()["gross_revenue"] == 0


def test_inventory_adjustment_and_expense_appear_in_report(client):
    business_id = create_business(client)
    product_id = client.post(
        f"/businesses/{business_id}/products",
        json={"name": "Leche", "unit_price": "30", "stock_quantity": "2"},
    ).json()["id"]

    adjustment = client.post(
        f"/businesses/{business_id}/products/{product_id}/inventory",
        json={"quantity_delta": "5", "reason": "purchase"},
    )
    assert adjustment.status_code == 200
    assert adjustment.json()["stock_quantity"] == "7.000"

    expense = client.post(
        f"/businesses/{business_id}/expenses",
        json={"description": "Compra de leche", "amount": "80"},
    )
    assert expense.status_code == 201
    report = client.get(f"/businesses/{business_id}/analytics").json()
    assert report["recorded_expenses"] == 80
    assert report["inventory_alerts"] == []


def test_assistant_uses_local_report_without_api_key(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    business_id = create_business(client)
    response = client.post(
        f"/businesses/{business_id}/assistant",
        json={"question": "¿Qué se vendió más?"},
    )

    assert response.status_code == 200
    assert response.json()["model"] == "local_analytics"
    assert "Aún no hay ventas" in response.json()["answer"]
    assert "$0.00 MXN" in response.json()["answer"]


def test_local_assistant_formats_report_numbers(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    report = {
        "period_days": 7,
        "gross_revenue": 931,
        "recorded_expenses": 320,
        "best_seller": {
            "product_name": "Café",
            "quantity_sold": 9,
        },
        "slowest_product": {"product_name": "Pan"},
        "inventory_alerts": [],
    }

    answer, model = answer_business_question("Resumen", report)

    assert model == "local_analytics"
    assert "$931.00 MXN" in answer
    assert "9 unidades" in answer
