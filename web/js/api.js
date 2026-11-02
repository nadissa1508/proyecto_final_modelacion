/**
 * Cliente de la API de PYMESIM. Expone `window.PymesimAPI`.
 */
(function () {
  const POLL_MS = 1500;

  /** Error de la API con la lista de mensajes devuelta por el servidor. */
  class ApiError extends Error {
    constructor(messages, status) {
      super(messages.join(" "));
      this.messages = messages;
      this.status = status;
    }
  }

  /** Convierte el cuerpo de una respuesta con error en una lista de mensajes. */
  function errorMessages(body) {
    const detail = body && body.detail;
    if (detail && Array.isArray(detail.errors)) return detail.errors;
    if (Array.isArray(detail)) return detail.map((d) => `${(d.loc || []).slice(-1)[0]}: ${d.msg}`);
    if (typeof detail === "string") return [detail];
    return ["Error inesperado del servidor."];
  }

  /**
   * Hace una petición JSON y devuelve el cuerpo.
   * @param {string} path Ruta de la API.
   * @param {object} [body] Cuerpo para POST. Sin cuerpo se usa GET.
   * @throws {ApiError} Si la respuesta no es 2xx.
   */
  async function request(path, body) {
    const init = body === undefined ? {} : {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    };
    const res = await fetch(path, init);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new ApiError(errorMessages(data), res.status);
    return data;
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  /**
   * Crea un trabajo y consulta su estado hasta que termina.
   * @param {string} question Pregunta de `GET /questions`.
   * @param {object} business Datos del negocio.
   * @param {object} options Opciones de la pregunta.
   * @param {(job: object) => void} [onUpdate] Recibe cada estado consultado.
   * @returns {Promise<object>} El campo `result` del trabajo.
   */
  async function runJob(question, business, options, onUpdate) {
    const job = await request(`/jobs/${question}`, { business, options });
    if (onUpdate) onUpdate(job);
    for (;;) {
      await sleep(POLL_MS);
      const state = await request(`/jobs/${job.job_id}`);
      if (onUpdate) onUpdate(state);
      if (state.status === "done") return state.result;
      if (state.status === "error") throw new ApiError([state.error || "La simulación falló."], 500);
    }
  }

  window.PymesimAPI = {
    ApiError,
    health: () => request("/health"),
    template: () => request("/template"),
    validate: (business) => request("/validate", business),
    summary: (business) => request("/summary", business),
    runJob,
  };
})();
