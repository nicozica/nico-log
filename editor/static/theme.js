(function () {
  "use strict";

  var theme = "editorial";
  try {
    var savedTheme = localStorage.getItem("portal-theme");
    if (savedTheme === "editorial" || savedTheme === "terminal") {
      theme = savedTheme;
    } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      theme = "terminal";
    }
  } catch (error) {
    // Keep the light default when browser storage is unavailable.
  }
  document.documentElement.setAttribute("data-theme", theme);
})();
