# Vendí — demo MVP

Vendí ayuda a pequeñas empresas a registrar productos, ventas, gastos e inventario, y convierte esos datos en indicadores entendibles. Este repositorio contiene un backend FastAPI y una interfaz responsive de demostración, servida desde el mismo origen, con SQLite por defecto.

## Requisitos

- Python 3.11 o posterior
- Una clave de API de OpenAI para habilitar respuestas conversacionales con el modelo preentrenado. Sin ella, el asistente responde con un resumen local de los indicadores.

## Ejecutar localmente

Desde esta carpeta (`App/`), en macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abre `http://127.0.0.1:8000` para la interfaz CSR de la demo: el navegador muestra las vistas y consulta los datos a la API REST. La documentación interactiva está en `/docs` y la comprobación de salud en `/health`. No se necesita Node.js ni un servidor frontend aparte para esta modalidad. La base local se crea en `vendi.db`. Para cambiarla, configura `DATABASE_URL`, por ejemplo `sqlite:///./vendi.db` o una URL de PostgreSQL.

### Desplegar el frontend por separado

La carpeta `web/` es estática y puede servirse desde un hosting de frontend. Antes de desplegarla, establece el contenido de `meta[name="vendi-api-url"]` en `web/index.html` a la URL pública de la API (por ejemplo, `https://api.ejemplo.com`), sin una ruta final. En el servidor de la API configura `CORS_ORIGINS` con el origen exacto del frontend; admite varios orígenes separados por comas:

```bash
export CORS_ORIGINS="https://app.ejemplo.com,https://www.ejemplo.com"
```

Si `vendi-api-url` se deja vacío, el frontend usa el mismo origen, como en la ejecución local de arriba.

Al entrar por primera vez, crea un espacio para el negocio. Su identificador se guarda en el navegador para la demo. El botón **Cargar datos de ejemplo** registra productos, ventas y un gasto reales en la API para que puedas explorar el reporte; úsalo una sola vez por espacio.

Para activar la IA preentrenada:

```bash
export OPENAI_API_KEY="tu-clave"
export OPENAI_MODEL="gpt-4o-mini"
uvicorn app.main:app --reload
```

No se necesita clave para iniciar el servidor. Sin la clave, el asistente usa un resumen local de los indicadores. Cuando la IA está habilitada, la pregunta y el reporte resumido del negocio se envían a OpenAI; no subas la clave al repositorio.

## API disponible

- `GET /health`: comprobación básica.
- `POST /businesses`: crear un negocio.
- `POST /businesses/{id}/products` y `GET /businesses/{id}/products`: catálogo e inventario.
- `POST /businesses/{id}/sales`: registrar venta; verifica existencias, descuenta inventario y registra el movimiento de forma conjunta.
- `POST /businesses/{id}/products/{product_id}/inventory`: registrar compra, devolución o ajuste.
- `POST /businesses/{id}/expenses`: registrar gasto.
- `POST /businesses/{id}/suppliers`: registrar proveedor.
- `GET /businesses/{id}/analytics?days=7`: ingresos, productos con mayor/menor demanda y alertas de reabastecimiento.
- `POST /businesses/{id}/assistant`: preguntar sobre los indicadores de los últimos siete días.

Ejemplo mínimo:

```bash
curl -X POST http://127.0.0.1:8000/businesses \
  -H 'Content-Type: application/json' \
  -d '{"name":"Mi negocio"}'
```

Los importes se expresan en MXN en los reportes. El esquema actual no almacena el costo de compra por producto: por eso “oportunidad” se basa en ingresos y no se presenta como margen de ganancia. La IA recibe únicamente el reporte calculado para responder, no ejecuta operaciones sobre la base de datos.

## Verificación

```bash
pytest
```

## Siguientes etapas del producto

Esta interfaz es una demo para un hackathon, no una aplicación lista para operar con clientes reales. Usa datos de ejemplo y guarda el negocio activo en el navegador. Todavía hacen falta autenticación y permisos, migraciones de base de datos, gestión completa de órdenes de compra, catálogo público/marketplace, OCR de tickets y despliegue. El modelo preentrenado evita entrenar una red propia con datos insuficientes; más adelante se pueden evaluar modelos propios para predicciones concretas cuando exista historial suficiente y medible.
