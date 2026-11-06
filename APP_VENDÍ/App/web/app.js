const API_URL = "";
const BUSINESS_KEY = "vendi.business.id";
const BUSINESS_NAME_KEY = "vendi.business.name";
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const state = { businessId: null, businessName: "", products: [], report: null, toastTimer: null };

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

async function api(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `No se pudo completar la solicitud (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}

function notify(message, type = "success") {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", type === "error");
  toast.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("show"), 3200);
}

function setBusy(button, busy, label) {
  if (busy) {
    button.dataset.originalText = button.innerHTML;
    button.disabled = true;
    button.textContent = label;
  } else {
    button.disabled = false;
    if (button.dataset.originalText) button.innerHTML = button.dataset.originalText;
  }
}

function showWorkspace() {
  $("#loading").classList.add("hidden");
  $("#onboarding").classList.add("hidden");
  $("#workspace").classList.remove("hidden");
  $("#sidebar-business").textContent = state.businessName;
  $("#greeting-name").textContent = state.businessName;
}

function showOnboarding() {
  $("#loading").classList.add("hidden");
  $("#workspace").classList.add("hidden");
  $("#onboarding").classList.remove("hidden");
}

async function initialize() {
  state.businessId = localStorage.getItem(BUSINESS_KEY);
  state.businessName = localStorage.getItem(BUSINESS_NAME_KEY) || "";
  if (!state.businessId || !state.businessName) {
    showOnboarding();
    return;
  }
  try {
    await refreshData();
    showWorkspace();
  } catch (error) {
    if (error.message.includes("Negocio no encontrado")) {
      localStorage.removeItem(BUSINESS_KEY);
      localStorage.removeItem(BUSINESS_NAME_KEY);
      showOnboarding();
      return;
    }
    $("#loading").innerHTML = `<span>No se pudo cargar Vendí. ${escapeHtml(error.message)}</span>`;
  }
}

async function refreshData() {
  const [products, report] = await Promise.all([
    api(`/businesses/${state.businessId}/products`),
    api(`/businesses/${state.businessId}/analytics?days=7`),
  ]);
  state.products = products;
  state.report = report;
  renderAll();
}

function currency(value) {
  return new Intl.NumberFormat("es-MX", {
    style: "currency", currency: "MXN", maximumFractionDigits: 2,
  }).format(Number(value || 0));
}

function quantity(value) {
  return new Intl.NumberFormat("es-MX", { maximumFractionDigits: 3 }).format(Number(value || 0));
}

function renderAll() {
  renderDashboard();
  renderInventory();
  renderSaleOptions();
}

function renderDashboard() {
  const report = state.report;
  $("#date-label").textContent = new Intl.DateTimeFormat("es-MX", {
    weekday: "long", day: "numeric", month: "long",
  }).format(new Date()).toLocaleUpperCase("es-MX");
  $("#metric-revenue").innerHTML = `${currency(report.gross_revenue)}<span> MXN</span>`;
  $("#metric-expenses").innerHTML = `${currency(report.recorded_expenses)}<span> MXN</span>`;
  $("#expense-caption").textContent = Number(report.recorded_expenses) > 0
    ? "Gastos del periodo"
    : "Aún sin gastos";
  $("#metric-products").textContent = state.products.length;
  $("#stock-caption").textContent = state.products.length
    ? `${state.products.reduce((sum, product) => sum + Number(product.stock_quantity), 0)} unidades disponibles`
    : "Listos para vender";

  const soldProducts = [...report.products]
    .sort((a, b) => Number(b.quantity_sold) - Number(a.quantity_sold))
    .slice(0, 4);
  const maxSold = Math.max(1, ...soldProducts.map((product) => Number(product.quantity_sold)));
  $("#demand-list").innerHTML = soldProducts.length
    ? soldProducts.map((product) => `
      <div class="demand-row">
        <span class="demand-name">${escapeHtml(product.product_name)}</span>
        <span class="demand-bar"><span style="width:${Math.max(3, Number(product.quantity_sold) / maxSold * 100)}%"></span></span>
        <span class="demand-qty">${quantity(product.quantity_sold)} uds.</span>
      </div>`).join("")
    : '<div class="empty-inline">Todavía no hay productos. Agrega tu catálogo o carga los datos de ejemplo para ver cómo se mueve tu negocio.</div>';

  const alerts = report.inventory_alerts || [];
  $("#alert-count").textContent = alerts.length;
  $("#alerts-list").innerHTML = alerts.length
    ? alerts.map((product) => `
      <div class="alert-row">
        <i class="alert-indicator"></i>
        <span class="alert-name">${escapeHtml(product.product_name)}</span>
        <span class="alert-stock">${quantity(product.stock_quantity)} / ${quantity(product.reorder_point)} uds.</span>
      </div>`).join("")
    : '<div class="alert-empty"><span>✓</span> Todo en orden. Sin alertas de inventario.</div>';

  if (report.best_seller) {
    $("#insight-title").textContent = `${report.best_seller.product_name} va a la cabeza.`;
    $("#insight-copy").textContent = `Se vendieron ${quantity(report.best_seller.quantity_sold)} unidades en los últimos 7 días. ¿Será tu próximo favorito?`;
  } else if (report.slowest_product && Number(report.slowest_product.quantity_sold) === 0) {
    $("#insight-title").textContent = "Es hora de empezar.";
    $("#insight-copy").textContent = "Registra una venta para descubrir qué productos prefieren tus clientes.";
  } else {
    $("#insight-title").textContent = "Cada dato cuenta.";
    $("#insight-copy").textContent = "Registra tus productos y ventas. Vendí te ayudará a encontrar lo que está funcionando.";
  }

  const seedButton = $("#seed-demo");
  seedButton.classList.toggle("hidden", state.products.length > 0);
}

const productIcons = ["☕", "🥐", "🍰", "🥛", "🧁", "🍞"];
const productColors = ["", "orange", "pink", "blue"];

function renderInventory() {
  const products = state.products;
  const lowStock = state.report.inventory_alerts || [];
  $("#inventory-summary").innerHTML = `
    <div class="summary-chip"><strong>${products.length}</strong> productos</div>
    <div class="summary-chip"><strong>${lowStock.length}</strong> por reabastecer</div>
    <div class="summary-chip"><strong>${quantity(products.reduce((sum, product) => sum + Number(product.stock_quantity), 0))}</strong> unidades en total</div>`;
  $("#inventory-list").innerHTML = products.length
    ? products.map((product, index) => {
      const isLow = Number(product.stock_quantity) <= Number(product.reorder_point);
      return `<div class="inventory-row">
        <div class="product-cell">
          <span class="product-thumb ${productColors[index % productColors.length]}">${productIcons[index % productIcons.length]}</span>
          <span class="product-copy"><strong>${escapeHtml(product.name)}</strong><span>${product.sku ? `SKU ${escapeHtml(product.sku)}` : "Producto"}</span></span>
        </div>
        <span class="table-price">${currency(product.unit_price)}</span>
        <span class="table-stock">${quantity(product.stock_quantity)} uds.</span>
        <span class="stock-status ${isLow ? "low" : ""}">${isLow ? "Stock bajo" : "Disponible"}</span>
      </div>`;
    }).join("")
    : '<div class="empty-table">Aún no tienes productos. Agrega el primero para empezar.</div>';
}

function renderSaleOptions() {
  const select = $("#sale-product");
  const selectedId = select.value;
  select.innerHTML = '<option value="">Elige un producto</option>' + state.products
    .map((product) => `<option value="${escapeHtml(product.id)}">${escapeHtml(product.name)} · ${currency(product.unit_price)}</option>`)
    .join("");
  if (state.products.some((product) => product.id === selectedId)) select.value = selectedId;
  updateSaleSummary();
}

function updateSaleSummary() {
  const product = state.products.find((item) => item.id === $("#sale-product").value);
  const amount = Math.max(0, Number($("#sale-quantity").value) || 0);
  $("#sale-total").textContent = currency(product ? Number(product.unit_price) * amount : 0);
  $("#sale-product-note").textContent = product
    ? `${quantity(product.stock_quantity)} unidades disponibles · ${currency(product.unit_price)} por unidad`
    : "Selecciona un producto para ver sus existencias.";
  $("#sale-quantity").max = product ? product.stock_quantity : "";
}

function navigate(viewName) {
  const title = { home: "Resumen", inventory: "Inventario", sales: "Registrar venta", assistant: "Asistente" }[viewName];
  if (!title) return;
  $$(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${viewName}`));
  $$("[data-view]").forEach((button) => button.classList.toggle("active", button.dataset.view === viewName));
  $("#page-label").textContent = title;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function seedDemo(button) {
  setBusy(button, true, "Preparando demo...");
  const demoProducts = [
    { name: "Café americano", unit_price: "45.00", stock_quantity: "24", reorder_point: "6" },
    { name: "Croissant de mantequilla", unit_price: "38.00", stock_quantity: "4", reorder_point: "8" },
    { name: "Panqué de limón", unit_price: "42.00", stock_quantity: "12", reorder_point: "3" },
    { name: "Latte de vainilla", unit_price: "58.00", stock_quantity: "18", reorder_point: "5" },
  ];
  try {
    const created = [];
    for (const product of demoProducts) {
      created.push(await api(`/businesses/${state.businessId}/products`, {
        method: "POST", body: JSON.stringify(product),
      }));
    }
    const sampleSales = [
      { product_id: created[0].id, quantity: "8" },
      { product_id: created[1].id, quantity: "4" },
      { product_id: created[2].id, quantity: "2" },
      { product_id: created[3].id, quantity: "5" },
    ];
    for (const item of sampleSales) {
      await api(`/businesses/${state.businessId}/sales`, {
        method: "POST", body: JSON.stringify({ items: [item], payment_method: "Efectivo" }),
      });
    }
    await api(`/businesses/${state.businessId}/expenses`, {
      method: "POST",
      body: JSON.stringify({ description: "Compra de insumos", category: "Insumos", amount: "320.00" }),
    });
    await refreshData();
    notify("¡Demo lista! Explora tus ventas e inventario.");
  } catch (error) {
    notify(error.message, "error");
    await refreshData();
  } finally {
    setBusy(button, false);
  }
}

$("#business-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector('button[type="submit"]');
  const name = new FormData(event.currentTarget).get("name").trim();
  setBusy(button, true, "Creando...");
  try {
    const business = await api("/businesses", { method: "POST", body: JSON.stringify({ name }) });
    state.businessId = business.id;
    state.businessName = business.name;
    localStorage.setItem(BUSINESS_KEY, business.id);
    localStorage.setItem(BUSINESS_NAME_KEY, business.name);
    await refreshData();
    showWorkspace();
    notify(`¡Listo, ${business.name}! Tu espacio ya está creado.`);
  } catch (error) {
    notify(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

$$("[data-view]").forEach((button) => button.addEventListener("click", () => navigate(button.dataset.view)));
$("#seed-demo").addEventListener("click", (event) => seedDemo(event.currentTarget));
$("#open-product-form").addEventListener("click", () => {
  $("#product-form-wrap").classList.remove("hidden");
  $("#product-form").elements.name.focus();
});
$("#close-product-form").addEventListener("click", () => $("#product-form-wrap").classList.add("hidden"));
$("#product-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  const data = Object.fromEntries(new FormData(form));
  for (const field of ["unit_price", "stock_quantity", "reorder_point"]) data[field] = String(data[field]);
  setBusy(button, true, "Guardando...");
  try {
    await api(`/businesses/${state.businessId}/products`, { method: "POST", body: JSON.stringify(data) });
    form.reset();
    form.elements.stock_quantity.value = "0";
    form.elements.reorder_point.value = "0";
    $("#product-form-wrap").classList.add("hidden");
    await refreshData();
    notify("Producto agregado a tu inventario.");
  } catch (error) {
    notify(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

$("#sale-product").addEventListener("change", updateSaleSummary);
$("#sale-quantity").addEventListener("input", updateSaleSummary);
$("#quantity-minus").addEventListener("click", () => {
  $("#sale-quantity").value = Math.max(0.001, Number($("#sale-quantity").value || 1) - 1);
  updateSaleSummary();
});
$("#quantity-plus").addEventListener("click", () => {
  $("#sale-quantity").value = Number($("#sale-quantity").value || 0) + 1;
  updateSaleSummary();
});
$("#sale-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  const productId = form.elements.product_id.value;
  const amount = Number(form.elements.quantity.value);
  if (!state.products.length) {
    notify("Agrega un producto antes de registrar una venta.", "error");
    navigate("inventory");
    return;
  }
  if (!productId || !Number.isFinite(amount) || amount <= 0) {
    notify("Selecciona un producto y una cantidad válida.", "error");
    return;
  }
  setBusy(button, true, "Guardando venta...");
  try {
    const paymentMethod = form.elements.payment_method.value;
    await api(`/businesses/${state.businessId}/sales`, {
      method: "POST",
      body: JSON.stringify({
        items: [{ product_id: productId, quantity: String(amount) }],
        ...(paymentMethod ? { payment_method: paymentMethod } : {}),
      }),
    });
    form.reset();
    $("#sale-quantity").value = "1";
    await refreshData();
    notify("Venta registrada. Tu inventario ya está actualizado.");
    navigate("home");
  } catch (error) {
    notify(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

async function ask(question) {
  const container = $("#chat-messages");
  const suggestions = container.querySelectorAll(".suggestion");
  suggestions.forEach((button) => button.remove());
  container.insertAdjacentHTML("beforeend", `<div class="chat-message user">${escapeHtml(question)}</div>`);
  const pending = document.createElement("div");
  pending.className = "chat-message assistant";
  pending.textContent = "Estoy revisando tus datos...";
  container.append(pending);
  container.scrollTop = container.scrollHeight;
  $("#assistant-mode").textContent = "Consultando tus datos...";
  try {
    const result = await api(`/businesses/${state.businessId}/assistant`, {
      method: "POST", body: JSON.stringify({ question }),
    });
    pending.textContent = result.answer;
    $("#assistant-mode").textContent = result.model === "local_analytics"
      ? "Análisis de tus datos"
      : `Con IA · ${result.model}`;
  } catch (error) {
    pending.classList.add("error");
    pending.textContent = error.message;
    $("#assistant-mode").textContent = "No se pudo completar la consulta";
  } finally {
    container.scrollTop = container.scrollHeight;
  }
}

$("#assistant-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("#assistant-question");
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  await ask(question);
});
$$(".suggestion").forEach((button) => button.addEventListener("click", () => ask(button.dataset.question)));

initialize();
