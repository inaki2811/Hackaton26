# Vendí: recomendación tecnológica (Python vs Java)

Resumen del análisis del prototipo "Súper-app Vendí para PyMEs"

## 1. Resumen ejecutivo

Se recomienda **Python** como lenguaje del backend de Vendí, preferentemente con **FastAPI** (ligero y rápido) o **Django** (si se quiere panel de administración, usuarios y permisos ya resueltos). El frontend generado en Figma Make (normalmente React/TypeScript) se conserva; la decisión Python vs Java aplica solo a la lógica del servidor, la base de datos y las integraciones.

## 2. Qué incluye el prototipo

- **Inicio:** panel con lectura inteligente del menú (producto más vendido, más lento y "joya oculta"), ventas por día y alertas de inventario.
- **Ventas:** registro rápido de ventas, escaneo de tickets de gasto (OCR), resumen semanal de utilidad y exportación a Excel.
- **Mercado:** proveedores cercanos con comparador, seguimiento de pedidos y "Aparador de clientes".
- **Asistente IA:** chat con entrada de voz que responde con datos del propio negocio.

## 3. Por qué Python

- **Asistente IA y lectura inteligente:** es el corazón del producto, y los SDK y librerías de IA tienen soporte de primera clase en Python.
- **Escaneo de tickets (OCR):** se resuelve con modelos de visión o Tesseract con muy poco código.
- **Análisis de ventas:** detectar productos estrella, lentos y picos por día es trabajo natural de pandas.
- **Exportar a Excel:** con openpyxl o pandas son pocas líneas.
- **Voz:** la transcripción del micrófono del asistente tiene buen soporte.
- **Velocidad de desarrollo:** son muchas funciones para un MVP, y Python permite iterar más rápido.

## 4. Cuándo elegir Java

Java (Spring Boot) sería preferible solo si:

- El equipo ya domina Java.
- Se esperan volúmenes muy altos de transacciones desde el inicio.
- Hay requisitos empresariales estrictos (banca, auditoría pesada).

No parece ser el caso de una app para PyMEs en etapa de MVP.

## 5. Stack sugerido

| Capa | Tecnología |
| --- | --- |
| Frontend | React/TypeScript (el generado por Figma Make) |
| Backend | Python con FastAPI o Django |
| Base de datos | PostgreSQL |
| Tareas en segundo plano | Celery con Redis (alertas de reorden, resúmenes semanales, procesamiento de tickets) |
| IA | API de modelo de lenguaje consultando las tablas de ventas e inventario |

## 6. Pedidos e integración con Uber, DiDi y Rappi

En el prototipo, "Tus pedidos" son pedidos a proveedores (por ejemplo, 38 panes dulces de Panadería Don Chuy). Los servicios de mensajería se usarían para entregarlos.

- **Fase 1 (MVP):** botones con enlaces que abren Uber, DiDi o Rappi con la dirección precargada. Es rápido de construir, pero el seguimiento del envío no regresa a Vendí.
- **Fase 2:** integración real por API (por ejemplo, Uber Direct o las APIs para comercios de Rappi y DiDi). Normalmente requieren acuerdo comercial, por lo que conviene solicitar acceso desde ahora.
- **Diseño recomendado:** crear en el backend un módulo de "proveedores de entrega" con un conector por servicio, para pasar de enlaces a API sin modificar el resto de la app.

## 7. Próximos pasos

1. Definir el esquema de base de datos para ventas, inventario, gastos, proveedores y pedidos.
2. Construir la API base (FastAPI o Django) y conectarla al frontend.
3. Implementar registro de ventas, inventario y reportes.
4. Agregar OCR de tickets y el asistente IA.
5. Integrar enlaces de entrega (Fase 1) y gestionar acceso a las APIs de Uber, DiDi y Rappi (Fase 2).

Para crear el esquema se necesita 