import json
import logging
import os
from decimal import Decimal

from openai import APIError, OpenAI

logger = logging.getLogger(__name__)


def _format_quantity(value: Decimal | int | float | str) -> str:
    normalized = Decimal(value).normalize()
    return format(normalized, "f")


def _format_money(value) -> str:
    return f"{Decimal(value):,.2f}"


def answer_business_question(question: str, report: dict) -> tuple[str, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        best_seller = report["best_seller"]
        slowest = report["slowest_product"]
        answer = (
            f"En los últimos {report['period_days']} días, las ventas brutas fueron "
            f"${_format_money(report['gross_revenue'])} MXN y los gastos registrados "
            f"${_format_money(report['recorded_expenses'])} MXN. "
        )
        answer += (
            f"El producto más vendido fue {best_seller['product_name']} "
            f"({_format_quantity(best_seller['quantity_sold'])} unidades). "
            if best_seller
            else "Aún no hay ventas registradas en este periodo. "
        )
        answer += (
            f"El producto con menos unidades vendidas fue {slowest['product_name']}. "
            if slowest
            else "Aún no hay productos activos para comparar. "
        )
        if report["inventory_alerts"]:
            names = ", ".join(
                item["product_name"] for item in report["inventory_alerts"]
            )
            answer += f"Revisa el inventario de: {names}. "
        answer += (
            "Estoy usando un resumen automático de los datos; configura OPENAI_API_KEY "
            "para habilitar respuestas conversacionales con IA."
        )
        return answer, "local_analytics"

    client = OpenAI(api_key=api_key)
    try:
        completion = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres Vendí, un asistente para pequeñas empresas. Responde "
                        "en español, con claridad y brevedad. Usa exclusivamente "
                        "el contexto de datos proporcionado; no inventes cifras. "
                        "Si faltan costos, advierte que no se puede calcular margen."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Datos del negocio (JSON): {json.dumps(report, default=str)}\n"
                        f"Pregunta: {question}"
                    ),
                },
            ],
        )
    except APIError:
        logger.exception("El proveedor de IA no pudo responder")
        raise

    answer = completion.choices[0].message.content
    if not answer:
        raise RuntimeError("El proveedor de IA devolvió una respuesta vacía")
    return answer, os.getenv("OPENAI_MODEL", "gpt-4o-mini")
