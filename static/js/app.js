/* Theme: applied before paint to avoid flash. */
(function () {
  var stored = localStorage.getItem("hesabban-theme");
  var dark = stored ? stored === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme = dark ? "dark" : "light";
})();

document.addEventListener("DOMContentLoaded", function () {
  var toggle = document.getElementById("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var root = document.documentElement;
      var next = root.dataset.theme === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      localStorage.setItem("hesabban-theme", next);
    });
  }

  /* Modal */
  var overlay = document.getElementById("modal-overlay");
  var content = document.getElementById("modal-content");

  function openModal() {
    overlay.hidden = false;
    requestAnimationFrame(function () { overlay.classList.add("open"); });
  }
  function closeModal() {
    overlay.classList.remove("open");
    setTimeout(function () { overlay.hidden = true; content.innerHTML = ""; }, 200);
  }

  document.body.addEventListener("htmx:afterSwap", function (e) {
    if (e.detail.target.id === "modal-content") openModal();
  });
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay || e.target.closest("[data-close-modal]")) closeModal();
  });
  document.body.addEventListener("htmx:beforeSwap", function (e) {
    if (e.detail.target.id === "modal-content" && e.detail.xhr && e.detail.xhr.responseURL && e.detail.requestConfig.verb === "post") {
      /* keep modal open for validation errors; HX-Refresh handles success */
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !overlay.hidden) closeModal();
  });

  /* Toasts raised from HX-Trigger headers */
  document.body.addEventListener("toast", function (e) {
    var message = e.detail && e.detail.value;
    if (!message) return;
    var toasts = document.getElementById("toasts");
    var el = document.createElement("div");
    el.className = "toast glass";
    el.textContent = message;
    toasts.appendChild(el);
    requestAnimationFrame(function () { el.classList.add("show"); });
    setTimeout(function () {
      el.classList.remove("show");
      setTimeout(function () { el.remove(); }, 300);
    }, 3200);
  });
});
