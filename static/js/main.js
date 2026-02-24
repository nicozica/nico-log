(function () {
  "use strict";

  const root = document.documentElement;
  const toggleButton = document.getElementById("theme-toggle");

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);

    if (!toggleButton) {
      return;
    }

    const terminalEnabled = theme === "terminal";
    toggleButton.setAttribute("aria-pressed", String(terminalEnabled));
    toggleButton.textContent = terminalEnabled ? "Editorial" : "Terminal";
  }

  function readTheme() {
    try {
      return localStorage.getItem("portal-theme") || "editorial";
    } catch (error) {
      return "editorial";
    }
  }

  function saveTheme(theme) {
    try {
      localStorage.setItem("portal-theme", theme);
    } catch (error) {
      // Ignore storage failures and keep behavior stateless.
    }
  }

  function copyWithFallback(value) {
    if (!value) {
      return;
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(value).catch(function () {
        window.prompt("Copy this URL:", value);
      });
      return;
    }

    window.prompt("Copy this URL:", value);
  }

  applyTheme(readTheme());

  if (toggleButton) {
    toggleButton.addEventListener("click", function () {
      const nextTheme = root.getAttribute("data-theme") === "terminal" ? "editorial" : "terminal";
      applyTheme(nextTheme);
      saveTheme(nextTheme);
    });
  }

  document.querySelectorAll(".copy-btn").forEach(function (button) {
    button.addEventListener("click", function () {
      const value = button.getAttribute("data-copy-value") || "";
      copyWithFallback(value);
    });
  });
})();
