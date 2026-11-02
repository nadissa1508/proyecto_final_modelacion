/**
 * Pestañas del pozo de código de la landing.
 * Cada contenedor con [data-tabs] alterna sus paneles según el botón seleccionado.
 */
document.querySelectorAll("[data-tabs]").forEach((box) => {
  const tabs = box.querySelectorAll('[role="tab"]');
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => {
        const selected = t === tab;
        t.setAttribute("aria-selected", String(selected));
        box.querySelector(`#${t.getAttribute("aria-controls")}`).hidden = !selected;
      });
    });
  });
});
