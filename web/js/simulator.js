/**
 * Simulador de PYMESIM. Construye el formulario, mantiene el resumen al día y
 * ejecuta cada pregunta como un trabajo de la API. Requiere Chart.js y api.js.
 */
(function () {
  const API = window.PymesimAPI;

  /** Escenarios por pregunta según la precisión elegida. */
  const PRECISION = { fast: { n: 200, n_grid: 100 }, precise: { n: 500, n_grid: 300 } };

  /** Datos de la tienda de barrio del notebook 07. Se combinan con la plantilla. */
  const TIENDA = {
    name: "Tienda de barrio", initial_cash: 25000, avg_ticket: 60, unit_cost: 42,
    rent: 3500, employees: 2, salary: 3800, utilities: 800, other_fixed: 300,
    initial_inventory: 15000, spoilage_rate: 0.01, loan_amount: 20000, annual_rate: 0.2, loan_term: 24,
    sales_start: 500, sales_mature: 900, ramp_months: 4, seasonality: 0.1,
    visits_per_customer: 6, monthly_retention: 0.95, servers: 1, opening_hour: 6, closing_hour: 21,
    hourly_profile: null, service_minutes: 2, patience_minutes: 4, max_queue: 5,
    credit_share: 0.3, payment_delay: 1, monthly_default: 0.04, default_churn: 0.5,
    strategies: { ad_cost: 800, rent_cut: 0.1, utilities_cut: 0.1 },
  };

  const MONTHS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
    "Septiembre", "Octubre", "Noviembre", "Diciembre"];

  const GROUPS = [
    { id: "money", title: "Dinero y deuda", open: true },
    { id: "sales", title: "Ventas y clientes", open: true },
    { id: "costs", title: "Precios y costos", open: false },
    { id: "service", title: "Atención al público", open: false },
    { id: "credit", title: "Ventas a crédito", open: false },
    { id: "strategies", title: "Estrategias a comparar", open: false },
  ];

  /**
   * Campos del formulario. `type` define cómo se muestra el valor.
   * money (Q), pct (fracción mostrada en %), int, num, text, month.
   */
  const FIELDS = [
    { key: "name", label: "Nombre del negocio", group: "money", type: "text", wide: true },
    { key: "initial_cash", label: "Caja inicial", group: "money", type: "money", step: 1000 },
    { key: "loan_amount", label: "Deuda", group: "money", type: "money", step: 1000 },
    { key: "annual_rate", label: "Interés anual", group: "money", type: "pct", step: 0.5 },
    { key: "loan_term", label: "Plazo de la deuda", group: "money", type: "int", suffix: "meses" },
    { key: "horizon", label: "Meses a simular", group: "money", type: "int", suffix: "meses", wide: true },

    { key: "sales_start", label: "Visitas el primer mes", group: "sales", type: "int", step: 50 },
    { key: "sales_mature", label: "Visitas al crecer", group: "sales", type: "int", step: 50 },
    { key: "ramp_months", label: "Meses para crecer a la mitad", group: "sales", type: "num", step: 1 },
    { key: "visits_per_customer", label: "Visitas por cliente al mes", group: "sales", type: "num", step: 0.5 },
    { key: "monthly_retention", label: "Clientes que regresan cada mes", group: "sales", type: "pct", step: 1 },
    { key: "seasonality", label: "Aumento en temporada alta", group: "sales", type: "pct", step: 1 },
    { key: "start_month", label: "Mes de apertura", group: "sales", type: "month", wide: true },

    { key: "avg_ticket", label: "Venta promedio por visita", group: "costs", type: "money", step: 1 },
    { key: "unit_cost", label: "Costo de insumos por visita", group: "costs", type: "money", step: 1 },
    { key: "rent", label: "Alquiler mensual", group: "costs", type: "money", step: 500 },
    { key: "utilities", label: "Servicios mensuales", group: "costs", type: "money", step: 100 },
    { key: "employees", label: "Empleados", group: "costs", type: "int" },
    { key: "salary", label: "Salario por empleado", group: "costs", type: "money", step: 100 },
    { key: "other_fixed", label: "Otros costos fijos", group: "costs", type: "money", step: 100 },
    { key: "initial_inventory", label: "Inventario inicial", group: "costs", type: "money", step: 500 },
    { key: "spoilage_rate", label: "Merma mensual del inventario", group: "costs", type: "pct", step: 1, wide: true },

    { key: "servers", label: "Personas que atienden", group: "service", type: "int" },
    { key: "days_open", label: "Días abiertos al mes", group: "service", type: "int" },
    { key: "opening_hour", label: "Abre a las", group: "service", type: "int", suffix: "h" },
    { key: "closing_hour", label: "Cierra a las", group: "service", type: "int", suffix: "h" },
    { key: "service_minutes", label: "Minutos por cliente", group: "service", type: "num", step: 0.5, suffix: "min" },
    { key: "patience_minutes", label: "Minutos que esperan", group: "service", type: "num", step: 0.5, suffix: "min" },
    { key: "max_queue", label: "Fila que los hace irse", group: "service", type: "int", suffix: "pers.", wide: true },

    { key: "credit_share", label: "Clientes a crédito", group: "credit", type: "pct", step: 5 },
    { key: "payment_delay", label: "Meses para cobrar", group: "credit", type: "int", suffix: "meses" },
    { key: "monthly_default", label: "Clientes que no pagan al mes", group: "credit", type: "pct", step: 1 },
    { key: "default_churn", label: "Morosos que se van", group: "credit", type: "pct", step: 5 },

    { key: "strategies.ad_cost", label: "Gasto en publicidad al mes", group: "strategies", type: "money", step: 100 },
    { key: "strategies.ad_factor", label: "Clientes nuevos por publicidad", group: "strategies", type: "num", step: 0.5, suffix: "veces" },
    { key: "strategies.loyalty_churn_cut", label: "Menos abandono con lealtad", group: "strategies", type: "pct", step: 5 },
    { key: "strategies.loyalty_discount", label: "Descuento de la lealtad", group: "strategies", type: "pct", step: 1 },
    { key: "strategies.hires", label: "Personas a contratar", group: "strategies", type: "int" },
    { key: "strategies.rent_cut", label: "Recorte del alquiler", group: "strategies", type: "pct", step: 5 },
    { key: "strategies.utilities_cut", label: "Recorte de servicios", group: "strategies", type: "pct", step: 5, wide: true },
  ];

  const HINTS = {
    credit_share: "0% si solo vendes al contado.",
    ramp_months: "Mes en que tus ventas recorren la mitad del camino.",
    "strategies.ad_factor": "Cuántas veces más gente nueva llega por la publicidad.",
  };

  /** Frase de acción de cada estrategia para las respuestas. */
  const ACTIONS = {
    "Publicidad": "invertir en publicidad",
    "Lealtad": "crear un programa de lealtad",
    "Contratar": "contratar a otra persona",
    "Recortar fijos": "recortar costos fijos",
  };

  /** Nombre de cada dato de la sensibilidad en el lenguaje del formulario. */
  const SENS_LABELS = {
    initial_cash: "Caja inicial", avg_ticket: "Venta promedio por visita", unit_cost: "Costo de insumos",
    rent: "Alquiler", salary: "Salarios", imitation: "Recomendaciones entre clientes",
    mean_churn: "Clientes que se van", mean_visits: "Visitas por cliente",
  };

  /** Describe las estrategias con las magnitudes del formulario. */
  function strategyDescriptions(st) {
    const pct = (v) => `${Math.round(v * 100)}%`;
    return {
      "Publicidad": `${fmtQ(st.ad_cost)} al mes en publicidad, que atrae ${st.ad_factor} veces más clientes nuevos.`,
      "Lealtad": `Un programa que reduce en ${pct(st.loyalty_churn_cut)} los clientes que se van, a cambio de ${pct(st.loyalty_discount)} de descuento.`,
      "Contratar": `${st.hires} ${st.hires === 1 ? "persona más" : "personas más"} atendiendo al público.`,
      "Recortar fijos": `Alquiler ${pct(st.rent_cut)} menor y servicios ${pct(st.utilities_cut)} menores.`,
    };
  }

  const state = {
    template: null, business: null, precision: "fast", valid: false, version: 0,
    running: false, results: {}, charts: {}, timer: null,
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const el = (tag, attrs = {}, html = "") => {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
    node.innerHTML = html;
    return node;
  };
  const clone = (obj) => JSON.parse(JSON.stringify(obj));

  /* Formato */
  const nf0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
  const fmtQ = (v) => (v < 0 ? "-Q" : "Q") + nf0.format(Math.abs(v));
  const fmtInt = (v) => nf0.format(v);
  const fmtPct = (v, d = 1) => `${(v * 100).toFixed(d).replace(/\.0$/, "")}%`;
  const months = (v) => `${Math.round(v)} ${Math.round(v) === 1 ? "mes" : "meses"}`;

  /* Lectura y escritura de campos anidados */
  function getValue(obj, key) {
    return key.split(".").reduce((o, k) => (o == null ? undefined : o[k]), obj);
  }
  function setValue(obj, key, value) {
    const parts = key.split(".");
    const last = parts.pop();
    parts.reduce((o, k) => o[k], obj)[last] = value;
  }

  /* Formulario */
  function inputFor(f) {
    const id = `f-${f.key.replace(".", "-")}`;
    const value = getValue(state.business, f.key);
    if (f.type === "month") {
      const opts = MONTHS.map((m, i) => `<option value="${i + 1}"${i + 1 === value ? " selected" : ""}>${m}</option>`).join("");
      return `<select class="input" id="${id}" data-key="${f.key}">${opts}</select>`;
    }
    if (f.type === "text") return `<input class="input" id="${id}" data-key="${f.key}" type="text" value="${value ?? ""}">`;
    const shown = f.type === "pct" ? +(value * 100).toFixed(2) : value;
    const prefix = f.type === "money" ? '<span class="input-prefix">Q</span>' : "";
    const suffixText = f.type === "pct" ? "%" : f.suffix || "";
    const suffix = suffixText ? `<span class="input-suffix">${suffixText}</span>` : "";
    const cls = ["input", prefix ? "has-prefix" : "", suffix ? "has-suffix" : ""].join(" ");
    const step = f.step ?? 1;
    return `<div class="input-wrap">${prefix}<input class="${cls}" id="${id}" data-key="${f.key}" type="number" inputmode="decimal" step="${step}" value="${shown}">${suffix}</div>`;
  }

  function buildForm() {
    const form = $("#business-form");
    form.innerHTML = "";
    GROUPS.forEach((g) => {
      const details = el("details", { class: "group", "data-group": g.id });
      if (g.open) details.open = true;
      details.appendChild(el("summary", {}, `<span>${g.title}</span><span class="badge badge-error group-count" hidden></span>`));
      const body = el("div", { class: "group-body" });
      FIELDS.filter((f) => f.group === g.id).forEach((f) => {
        const field = el("div", { class: `field${f.wide ? " wide" : ""}`, "data-field": f.key });
        const id = `f-${f.key.replace(".", "-")}`;
        field.innerHTML = `<label for="${id}">${f.label}</label>${inputFor(f)}`
          + (HINTS[f.key] ? `<span class="hint">${HINTS[f.key]}</span>` : "")
          + '<span class="field-error" hidden></span>';
        body.appendChild(field);
      });
      if (g.id === "service") {
        const checked = state.business.hourly_profile ? " checked" : "";
        body.appendChild(el("label", { class: "check" },
          `<input type="checkbox" id="peak-profile"${checked}> Más clientes en la mañana y al almuerzo, como una cafetería de 7:00 a 19:00`));
      }
      details.appendChild(body);
      form.appendChild(details);
    });
    syncPeakProfile();
  }

  function readInput(input) {
    const f = FIELDS.find((x) => x.key === input.dataset.key);
    if (f.type === "text") return input.value;
    if (f.type === "month") return Number(input.value);
    if (input.value === "") return NaN;
    const raw = Number(input.value);
    if (f.type === "pct") return raw / 100;
    if (f.type === "int") return Math.round(raw);
    return raw;
  }

  /** Activa el perfil horario de cafetería solo si el horario dura lo mismo que el perfil. */
  function syncPeakProfile() {
    const box = $("#peak-profile");
    const hours = state.business.closing_hour - state.business.opening_hour;
    const fits = hours === state.template.hourly_profile.length;
    box.disabled = !fits;
    if (!fits) box.checked = false;
    state.business.hourly_profile = box.checked ? clone(state.template.hourly_profile) : null;
  }

  function onInput(ev) {
    const target = ev.target;
    if (target.id === "peak-profile") {
      syncPeakProfile();
    } else if (target.dataset.key) {
      const value = readInput(target);
      setValue(state.business, target.dataset.key, value);
      if (target.dataset.key === "opening_hour" || target.dataset.key === "closing_hour") syncPeakProfile();
    } else {
      return;
    }
    markStale();
    scheduleRefresh();
  }

  /* Validación y resumen */
  let refreshTimer = null;
  function scheduleRefresh() {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(refresh, 500);
  }

  function labelize(message) {
    let out = message;
    [...FIELDS].sort((a, b) => b.key.length - a.key.length).forEach((f) => {
      const key = f.key.split(".").pop();
      out = out.replaceAll(key, `«${f.label}»`);
    });
    return out;
  }

  function showErrors(messages) {
    document.querySelectorAll("#business-form .field").forEach((f) => {
      f.classList.remove("invalid");
      const e = $(".field-error", f);
      e.hidden = true;
      e.textContent = "";
    });
    const counts = {};
    const general = [];
    messages.forEach((msg) => {
      const hits = FIELDS.filter((f) => new RegExp(`\\b${f.key.split(".").pop()}\\b`).test(msg));
      const text = labelize(msg);
      if (!hits.length) general.push(text);
      hits.forEach((f) => {
        const field = document.querySelector(`[data-field="${f.key}"]`);
        field.classList.add("invalid");
        const e = $(".field-error", field);
        e.hidden = false;
        e.textContent = text;
        counts[f.group] = (counts[f.group] || 0) + 1;
      });
    });
    document.querySelectorAll(".group").forEach((g) => {
      const badge = $(".group-count", g);
      const n = counts[g.dataset.group] || 0;
      badge.hidden = n === 0;
      badge.textContent = n === 1 ? "1 dato por revisar" : `${n} datos por revisar`;
      if (n) g.open = true;
    });
    return general;
  }

  function hasNaN() {
    return FIELDS.some((f) => Number.isNaN(getValue(state.business, f.key)));
  }

  async function refresh() {
    const version = ++state.version;
    const status = $("#summary-status");
    if (hasNaN()) {
      state.valid = false;
      status.className = "badge badge-error";
      status.textContent = "Completa los datos";
      updateRunButtons();
      return;
    }
    status.className = "badge badge-running badge-dot";
    status.textContent = "Calculando";
    try {
      const v = await API.validate(state.business);
      if (version !== state.version) return;
      const general = showErrors(v.errors);
      state.valid = v.valid;
      if (!v.valid) {
        status.className = "badge badge-error";
        status.textContent = "Revisa los datos";
        $("#summary-note").textContent = general.join(" ");
        return;
      }
      const s = await API.summary(state.business);
      if (version !== state.version) return;
      renderSummary(s);
      status.className = "badge badge-success";
      status.textContent = "Actualizado";
    } catch (err) {
      if (version !== state.version) return;
      status.className = "badge badge-error";
      status.textContent = "Error";
      $("#summary-note").textContent = labelize(err.message);
    } finally {
      updateRunButtons();
    }
  }

  function kpi(label, value, sub = "", accent = false) {
    return `<div class="kpi"><p class="kpi-label">${label}</p><p class="kpi-value${accent ? " accent" : ""}">${value}</p>${sub ? `<p class="kpi-sub">${sub}</p>` : ""}</div>`;
  }

  function renderSummary(s) {
    $("#summary-title").textContent = s.name || "Tu negocio";
    $("#summary-kpis").innerHTML = [
      kpi("Visitas para cubrir costos", fmtInt(s.breakeven_visits), "al mes"),
      kpi("Costos fijos", fmtQ(s.fixed_costs), "al mes"),
      kpi("Cuota de la deuda", fmtQ(s.loan_payment), "al mes"),
      kpi("Ganancia por visita", fmtQ(s.margin_per_visit), "antes de costos fijos"),
    ].join("");
    const h = state.business.horizon;
    let note = s.deterministic_months_survived >= h
      ? `Si todo sale como esperas, tu caja aguanta los ${h} meses. Las preguntas de abajo muestran qué pasa cuando las cosas cambian.`
      : `Aun si todo sale como esperas, tu caja se acaba después de ${months(s.deterministic_months_survived)}.`;
    if (s.calibration.mean_abs_pct_error > 0.05) {
      note += ` <span class="warn">La simulación de tus clientes se aleja ${fmtPct(s.calibration.mean_abs_pct_error)} de tus ventas esperadas, toma los resultados como aproximados.</span>`;
    }
    $("#summary-note").innerHTML = note;
    const labels = s.expected_visits.map((_, i) => `Mes ${i + 1}`);
    drawChart("chart-summary", {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "Visitas que esperas", data: s.expected_visits, borderColor: "#202020", borderDash: [6, 4], pointRadius: 0, borderWidth: 2 },
          { label: "Visitas simuladas", data: s.calibration.abm_visits, borderColor: "#d93a31", pointRadius: 0, borderWidth: 2.5 },
          { label: "Para cubrir costos", data: labels.map(() => s.breakeven_visits), borderColor: "#8d8d8d", pointRadius: 0, borderWidth: 1.5 },
        ],
      },
      options: { scales: { y: { ticks: { callback: (v) => fmtInt(v) } } } },
    });
  }

  /* Gráficas */
  function drawChart(id, config) {
    if (state.charts[id]) state.charts[id].destroy();
    const canvas = document.getElementById(id);
    if (!canvas) return;
    config.options = Object.assign({ responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom", labels: { boxWidth: 12, boxHeight: 12 } } } }, config.options);
    state.charts[id] = new Chart(canvas, config);
  }

  /* Preguntas */
  const QUESTIONS = [
    {
      id: "drop", tab: "¿Cuánto aguanto?", job: "sales_drop",
      title: "¿Cuántos meses aguanto si vendo menos?",
      text: "Compara tus ventas esperadas con una caída. Verás el peor, el probable y el mejor escenario.",
      controls: [{ id: "drop", label: "Caída de ventas", values: [10, 20, 30, 40, 50], value: 30, suffix: "%" }],
      options: (c, p) => ({ drop: c.drop / 100, n: p.n }),
      render: renderDrop,
    },
    {
      id: "retention", tab: "Clientes", job: "retention",
      title: "¿Cuántos clientes debo conservar cada mes?",
      text: "Prueba distintos niveles de clientes que regresan y encuentra el mínimo para tu nivel de riesgo.",
      controls: [{ id: "risk", label: "Riesgo que aceptas", values: [5, 10, 20, 30], value: 10, suffix: "%" }],
      options: (c, p) => ({ target_risk: c.risk / 100, n: p.n_grid }),
      render: renderRetention,
    },
    {
      id: "strategies", tab: "Estrategias", job: "strategies",
      title: "¿Qué me conviene más?",
      text: "Compara publicidad, lealtad, contratar y recortar costos fijos en los mismos futuros posibles, con tus ventas esperadas y con 30% menos.",
      controls: [],
      options: (c, p) => ({ n: p.n_grid, sales_changes: [0, -0.3] }),
      render: renderStrategies,
    },
    {
      id: "sensitivity", tab: "¿Qué pesa más?", job: "sensitivity",
      title: "¿Qué datos pesan más en el resultado?",
      text: "Cada dato se mueve 20% hacia arriba y hacia abajo, uno a la vez, para ver cuánto cambia tu probabilidad de aguantar.",
      controls: [],
      options: (c, p) => ({ n: p.n_grid }),
      render: renderSensitivity,
    },
    {
      id: "credit", tab: "Crédito", job: "credit",
      title: "¿Me conviene vender a crédito?",
      text: "Mide cuánto te afecta cobrar después y que algunos clientes no paguen. Si hoy no vendes a crédito, se evalúa el caso hipotético.",
      controls: [{ id: "share", label: "Si vendieras a crédito a", values: [10, 20, 30, 50], value: 20, suffix: "% de clientes" }],
      options: (c, p) => ({ share: c.share / 100, n: p.n_grid }),
      render: renderCredit,
    },
  ];

  function buildQuestions() {
    const tabs = $("#question-tabs");
    const panels = $("#question-panels");
    QUESTIONS.forEach((q, i) => {
      const tab = el("button", { class: "pill", type: "button", role: "tab", id: `tab-${q.id}`,
        "aria-controls": `panel-${q.id}`, "aria-selected": String(i === 0) }, q.tab);
      tab.addEventListener("click", () => selectQuestion(q.id));
      tabs.appendChild(tab);

      const controls = q.controls.map((c) => {
        const opts = c.values.map((v) => `<option value="${v}"${v === c.value ? " selected" : ""}>${v}${c.suffix}</option>`).join("");
        return `<div class="field"><label for="c-${q.id}-${c.id}">${c.label}</label><select class="input" id="c-${q.id}-${c.id}" data-control="${c.id}">${opts}</select></div>`;
      }).join("");
      const panel = el("div", { class: "question-panel", role: "tabpanel", id: `panel-${q.id}`, "aria-labelledby": `tab-${q.id}` },
        `<div class="q-intro"><div class="q-intro-text"><h3 class="heading-md">${q.title}</h3><p class="body-sm">${q.text}</p></div>`
        + `<div class="q-controls">${controls}<button class="btn btn-primary run" type="button" data-q="${q.id}">Simular</button></div></div>`
        + '<div class="q-status"></div>'
        + '<div class="q-result"><div class="q-empty">Presiona Simular para responder esta pregunta.</div></div>');
      panel.hidden = i !== 0;
      $(".run", panel).addEventListener("click", () => runQuestion(q));
      panels.appendChild(panel);
    });
  }

  function selectQuestion(id) {
    QUESTIONS.forEach((q) => {
      $(`#tab-${q.id}`).setAttribute("aria-selected", String(q.id === id));
      $(`#panel-${q.id}`).hidden = q.id !== id;
    });
    const r = state.results[id];
    if (r && !r.drawn) {
      const q = QUESTIONS.find((x) => x.id === id);
      q.render(r.data, r.controls, $(`#panel-${id} .q-result`));
      r.drawn = true;
    }
  }

  function controlValues(q) {
    const out = {};
    document.querySelectorAll(`#panel-${q.id} [data-control]`).forEach((s) => { out[s.dataset.control] = Number(s.value); });
    return out;
  }

  function updateRunButtons() {
    document.querySelectorAll(".run").forEach((b) => { b.disabled = state.running || !state.valid; });
  }

  function markStale() {
    Object.entries(state.results).forEach(([id, r]) => {
      if (r.stale) return;
      r.stale = true;
      const box = $(`#panel-${id} .q-result`);
      box.classList.add("stale");
      $(`#panel-${id} .q-status`).innerHTML = '<span class="stale-note">Cambiaste tus datos. Vuelve a simular para actualizar esta respuesta.</span>';
    });
  }

  async function runQuestion(q) {
    if (state.running || !state.valid) return;
    state.running = true;
    updateRunButtons();
    const panel = $(`#panel-${q.id}`);
    const status = $(".q-status", panel);
    const box = $(".q-result", panel);
    const controls = controlValues(q);
    const started = Date.now();
    let label = "En cola";
    const tick = () => {
      const secs = Math.round((Date.now() - started) / 1000);
      status.innerHTML = `<span class="badge badge-running badge-dot">${label}</span><span class="caption">${secs} s</span>`;
    };
    tick();
    clearInterval(state.timer);
    state.timer = setInterval(tick, 1000);
    try {
      const result = await API.runJob(q.job, state.business, q.options(controls, PRECISION[state.precision]), (job) => {
        label = job.status === "running" ? "Simulando futuros posibles" : "En cola";
      });
      clearInterval(state.timer);
      const secs = Math.round((Date.now() - started) / 1000);
      status.innerHTML = `<span class="badge badge-success">Listo</span><span class="caption">${secs} s · ${state.precision === "fast" ? "precisión rápida" : "precisión alta"}</span>`;
      box.classList.remove("stale");
      state.results[q.id] = { data: result, controls, stale: false, drawn: true };
      q.render(result, controls, box);
    } catch (err) {
      clearInterval(state.timer);
      status.innerHTML = `<span class="badge badge-error">No se pudo simular</span><span class="caption">${labelize(err.message)}</span>`;
    } finally {
      state.running = false;
      updateRunButtons();
    }
  }

  /* Respuestas */
  function renderDrop(r, c, box) {
    const h = state.business.horizon;
    const exp = r.expected;
    const red = r.reduced;
    const likely = red.range.likely.months_survived;
    const answer = likely >= h
      ? `Con ${c.drop}% menos ventas, en el escenario probable <em>llegas a los ${h} meses</em>.`
      : `Con ${c.drop}% menos ventas, en el escenario probable aguantas <em>${months(likely)}</em>.`;
    const rr = red.range;
    box.innerHTML = `<p class="q-answer">${answer}</p><div class="kpis">`
      + kpi("Riesgo con tus ventas esperadas", fmtPct(exp.probability_out_of_cash), `de quedarte sin caja en ${h} meses`)
      + kpi(`Riesgo con ${c.drop}% menos`, fmtPct(red.probability_out_of_cash), `de quedarte sin caja en ${h} meses`, true)
      + kpi("Meses que aguantas", `${Math.round(rr.worst.months_survived)} · ${Math.round(rr.likely.months_survived)} · ${Math.round(rr.best.months_survived)}`, "peor · probable · mejor")
      + kpi("Caja final probable", fmtQ(rr.likely.final_cash), `con ${c.drop}% menos ventas`)
      + '</div><div class="chart-box tall"><canvas id="chart-drop"></canvas></div>';
    const f1 = exp.cash_fan;
    const f2 = red.cash_fan;
    const labels = f1.month.map((m) => `Mes ${m}`);
    drawChart("chart-drop", {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "Esperadas, peor", data: f1.p10, borderColor: "rgba(32,32,32,0.25)", pointRadius: 0, borderWidth: 1 },
          { label: "Esperadas, rango", data: f1.p90, borderColor: "rgba(32,32,32,0.25)", backgroundColor: "rgba(32,32,32,0.08)", fill: "-1", pointRadius: 0, borderWidth: 1 },
          { label: "Esperadas, probable", data: f1.p50, borderColor: "#202020", pointRadius: 0, borderWidth: 2.5 },
          { label: `${c.drop}% menos, peor`, data: f2.p10, borderColor: "rgba(217,58,49,0.35)", pointRadius: 0, borderWidth: 1 },
          { label: `${c.drop}% menos, rango`, data: f2.p90, borderColor: "rgba(217,58,49,0.35)", backgroundColor: "rgba(255,105,97,0.18)", fill: "-1", pointRadius: 0, borderWidth: 1 },
          { label: `${c.drop}% menos, probable`, data: f2.p50, borderColor: "#d93a31", pointRadius: 0, borderWidth: 2.5 },
        ],
      },
      options: {
        plugins: { legend: { labels: { filter: (item) => item.text.includes("probable") || item.text.includes("rango") } },
          tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${fmtQ(ctx.parsed.y)}` } } },
        scales: { y: { ticks: { callback: (v) => fmtQ(v) }, grid: { color: (ctx) => (ctx.tick.value === 0 ? "#202020" : "rgba(32,32,32,0.08)") } } },
      },
    });
  }

  function renderRetention(r, c, box) {
    const h = state.business.horizon;
    const best = r.min_retention == null ? null : r.rows.find((x) => x.retention === r.min_retention);
    const current = r.rows.find((x) => Math.abs(x.retention - r.expected_retention) < 1e-9);
    const answer = best
      ? `Necesitas que regresen al menos <em>${fmtPct(best.retention, 0)}</em> de tus clientes cada mes para que tu riesgo sea menor a ${c.risk}%.`
      : `Ninguna retención entre ${fmtPct(r.rows[0].retention, 0)} y ${fmtPct(r.rows[r.rows.length - 1].retention, 0)} baja tu riesgo a menos de ${c.risk}%. Conservar clientes no basta, revisa tus costos y precios.`;
    box.innerHTML = `<p class="q-answer">${answer}</p><div class="kpis">`
      + kpi("Retención mínima", best ? fmtPct(best.retention, 0) : "No alcanza", `para un riesgo menor a ${c.risk}%`, true)
      + kpi("Clientes a conservar", best ? fmtInt(best.retained_customers_per_month) : "Sin dato", `por mes, al final de ${h} meses`)
      + kpi("Tu retención actual", fmtPct(r.expected_retention, 0), "según tus datos")
      + kpi("Probabilidad con tu retención", current ? fmtPct(current.probability_survive) : "Sin dato", `de llegar al mes ${h}`)
      + '</div><div class="chart-box"><canvas id="chart-retention"></canvas></div>';
    drawChart("chart-retention", {
      type: "line",
      data: {
        labels: r.rows.map((x) => fmtPct(x.retention, 0)),
        datasets: [
          { label: `Probabilidad de llegar al mes ${h}`, data: r.rows.map((x) => x.probability_survive * 100), borderColor: "#d93a31", backgroundColor: "#d93a31", borderWidth: 2.5, pointRadius: 4 },
          { label: "Objetivo", data: r.rows.map(() => (1 - r.target_risk) * 100), borderColor: "#202020", borderDash: [6, 4], pointRadius: 0, borderWidth: 1.5 },
        ],
      },
      options: { scales: { y: { min: 0, max: 100, ticks: { callback: (v) => `${v}%` } }, x: { title: { display: true, text: "Clientes que regresan cada mes" } } } },
    });
  }

  function barsHTML(rows, rec) {
    return '<div class="bars">' + rows.map((x) => {
      const best = x.strategy === rec;
      return `<div class="bar-row${best ? " best" : ""}"><span>${x.strategy}${best ? '<span class="badge badge-success rec">Recomendada</span>' : ""}</span>`
        + `<div class="bar-track"><div class="bar-fill" style="width:${(x.probability_survive * 100).toFixed(1)}%"></div></div>`
        + `<span class="bar-value">${fmtPct(x.probability_survive, 0)}</span></div>`;
    }).join("") + "</div>";
  }

  function renderStrategies(r, c, box) {
    const h = state.business.horizon;
    const base = r.scenarios[0];
    const rec = base.rows.find((x) => x.strategy === base.recommendation);
    const none = base.rows.find((x) => x.strategy === "Sin cambios");
    const answer = base.recommendation === "Sin cambios"
      ? "Ninguna estrategia mejora tu situación actual. <em>Conviene no hacer cambios</em>."
      : `Te conviene <em>${ACTIONS[base.recommendation]}</em>. Tu probabilidad de llegar al mes ${h} pasa de ${fmtPct(none.probability_survive, 0)} a ${fmtPct(rec.probability_survive, 0)}.`;
    const cols = r.scenarios.map((s) => {
      const title = s.sales_change === 0 ? "Con tus ventas esperadas" : `Con ${Math.round(-s.sales_change * 100)}% menos ventas`;
      return `<div><p class="sub-title">${title}</p>${barsHTML(s.rows, s.recommendation)}</div>`;
    }).join("");
    const desc = Object.entries(strategyDescriptions(state.business.strategies))
      .map(([k, v]) => `<li><strong>${k}.</strong> ${v}</li>`).join("");
    box.innerHTML = `<p class="q-answer">${answer}</p><p class="body-sm strategies-note">Probabilidad de llegar al mes ${h} con cada opción.</p><div class="two-up">${cols}</div><ul class="desc-list">${desc}</ul>`;
  }

  function renderSensitivity(r, c, box) {
    const h = state.business.horizon;
    const top = r.rows[0];
    const name = (x) => SENS_LABELS[x.parameter] || x.label;
    const answer = `El dato que más pesa es <em>${name(top).toLowerCase()}</em>. Si baja 20%, tu probabilidad de llegar al mes ${h} pasa de ${fmtPct(r.base_probability, 0)} a ${fmtPct(top.low, 0)}.`;
    box.innerHTML = `<p class="q-answer">${answer}</p><div class="chart-box tall"><canvas id="chart-sensitivity"></canvas></div>`;
    drawChart("chart-sensitivity", {
      type: "bar",
      data: {
        labels: r.rows.map(name),
        datasets: [
          { label: "Si baja 20%", data: r.rows.map((x) => (x.low - r.base_probability) * 100), backgroundColor: "#d93a31", borderRadius: 4 },
          { label: "Si sube 20%", data: r.rows.map((x) => (x.high - r.base_probability) * 100), backgroundColor: "#202020", borderRadius: 4 },
        ],
      },
      options: {
        indexAxis: "y",
        interaction: { mode: "nearest", intersect: true },
        scales: { x: { ticks: { callback: (v) => `${v > 0 ? "+" : ""}${v} pts` } }, y: { stacked: true } },
        plugins: { tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.x > 0 ? "+" : ""}${ctx.parsed.x.toFixed(1)} puntos` } } },
      },
    });
  }

  function renderCredit(r, c, box) {
    const h = state.business.horizon;
    const share = fmtPct(r.credit_share, 0);
    const answer = r.what_if
      ? `Si vendieras a crédito al ${share} de tus clientes, tu probabilidad de llegar al mes ${h} pasaría de ${fmtPct(r.cash_only.probability_survive, 0)} a <em>${fmtPct(r.with_credit.probability_survive, 0)}</em>.`
      : `Vender a crédito al ${share} de tus clientes cambia tu probabilidad de llegar al mes ${h} de ${fmtPct(r.cash_only.probability_survive, 0)} a <em>${fmtPct(r.with_credit.probability_survive, 0)}</em>.`;
    const tolerable = r.max_tolerable_default == null ? "Ninguna" : fmtPct(r.max_tolerable_default, 0);
    box.innerHTML = `<p class="q-answer">${answer}</p><div class="kpis">`
      + kpi("Solo al contado", fmtPct(r.cash_only.probability_survive, 0), `de llegar al mes ${h}`)
      + kpi("Con crédito", fmtPct(r.with_credit.probability_survive, 0), `de llegar al mes ${h}`, true)
      + kpi("Dinero que no cobrarías", fmtQ(r.with_credit.bad_debt_p50), `escenario probable en ${h} meses`)
      + kpi("Morosidad que toleras", tolerable, `sin perder más de ${fmtPct(r.max_drop, 0)} de probabilidad`)
      + '</div><div class="two-up"><div><p class="sub-title">Según cuántos clientes no pagan</p><div class="chart-box"><canvas id="chart-default"></canvas></div></div>'
      + '<div><p class="sub-title">Según cuánto tardas en cobrar</p><div class="chart-box"><canvas id="chart-delay"></canvas></div></div></div>';
    const pctAxis = { min: 0, max: 100, ticks: { callback: (v) => `${v}%` } };
    drawChart("chart-default", {
      type: "line",
      data: {
        labels: r.default_curve.map((x) => fmtPct(x.monthly_default, 0)),
        datasets: [
          { label: "Con crédito", data: r.default_curve.map((x) => x.probability_survive * 100), borderColor: "#d93a31", backgroundColor: "#d93a31", borderWidth: 2.5, pointRadius: 4 },
          { label: "Solo al contado", data: r.default_curve.map(() => r.cash_only.probability_survive * 100), borderColor: "#202020", borderDash: [6, 4], pointRadius: 0, borderWidth: 1.5 },
        ],
      },
      options: { scales: { y: pctAxis, x: { title: { display: true, text: "Clientes a crédito que no pagan al mes" } } } },
    });
    drawChart("chart-delay", {
      type: "bar",
      data: {
        labels: r.delay_curve.map((x) => `${x.payment_delay} ${x.payment_delay === 1 ? "mes" : "meses"}`),
        datasets: [{ label: `Probabilidad de llegar al mes ${h}`, data: r.delay_curve.map((x) => x.probability_survive * 100), backgroundColor: "#d93a31", borderRadius: 6 }],
      },
      options: { scales: { y: pctAxis } },
    });
  }

  /* Ejemplos y precisión */
  function loadPreset(name) {
    const base = clone(state.template);
    if (name === "tienda") {
      const { strategies, ...rest } = TIENDA;
      Object.assign(base, rest);
      Object.assign(base.strategies, strategies);
    }
    state.business = base;
    state.results = {};
    document.querySelectorAll("#preset-pills .pill").forEach((p) => p.setAttribute("aria-pressed", String(p.dataset.preset === name)));
    document.querySelectorAll(".question-panel").forEach((panel) => {
      $(".q-status", panel).innerHTML = "";
      const box = $(".q-result", panel);
      box.classList.remove("stale");
      box.innerHTML = '<div class="q-empty">Presiona Simular para responder esta pregunta.</div>';
    });
    buildForm();
    refresh();
  }

  function setPrecision(name) {
    state.precision = name;
    document.querySelectorAll("#precision-pills .pill").forEach((p) => p.setAttribute("aria-pressed", String(p.dataset.precision === name)));
  }

  async function init() {
    if (window.Chart) {
      Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
      Chart.defaults.font.size = 12;
      Chart.defaults.color = "#575757";
      Chart.defaults.borderColor = "rgba(32,32,32,0.08)";
    }
    const status = $("#api-status");
    try {
      await API.health();
      status.className = "badge badge-success badge-dot";
      status.textContent = "Servidor activo";
      const t = await API.template();
      state.template = t.business;
    } catch (err) {
      status.className = "badge badge-error badge-dot";
      status.textContent = "Sin conexión";
      $("#summary-note").textContent = "No se pudo conectar con el servidor de PYMESIM. Inícialo con uvicorn business_sim.api:app y recarga la página.";
      return;
    }
    buildQuestions();
    const form = $("#business-form");
    form.addEventListener("input", onInput);
    form.addEventListener("change", onInput);
    document.querySelectorAll("#preset-pills .pill").forEach((p) => p.addEventListener("click", () => loadPreset(p.dataset.preset)));
    document.querySelectorAll("#precision-pills .pill").forEach((p) => p.addEventListener("click", () => setPrecision(p.dataset.precision)));
    loadPreset("cafe");
  }

  init();
})();
