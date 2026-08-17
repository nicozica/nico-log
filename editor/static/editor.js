(() => {
  "use strict";

  const root = document.documentElement;
  const themeToggle = document.querySelector("[data-theme-toggle]");
  const themeIcon = document.querySelector("[data-theme-icon]");
  const themeLabel = document.querySelector("[data-theme-label]");

  const applyEditorTheme = (theme) => {
    const dark = theme === "terminal";
    root.setAttribute("data-theme", theme);
    document.querySelectorAll(".toastui-editor-defaultUI").forEach((element) => {
      element.classList.toggle("toastui-editor-dark", dark);
    });
    if (themeToggle) {
      themeToggle.setAttribute("aria-pressed", String(dark));
      themeToggle.setAttribute("aria-label", dark ? "Cambiar a modo claro" : "Cambiar a modo oscuro");
    }
    if (themeIcon) themeIcon.textContent = dark ? "☼" : "☾";
    if (themeLabel) themeLabel.textContent = dark ? "Claro" : "Oscuro";
    const themeColor = document.querySelector('meta[name="theme-color"]');
    if (themeColor) themeColor.setAttribute("content", dark ? "#0b1112" : "#14231d");
  };

  applyEditorTheme(root.getAttribute("data-theme") || "editorial");
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const nextTheme = root.getAttribute("data-theme") === "terminal" ? "editorial" : "terminal";
      applyEditorTheme(nextTheme);
      try {
        localStorage.setItem("portal-theme", nextTheme);
      } catch (error) {
        // Theme still works for this page when storage is unavailable.
      }
    });
  }

  const body = document.querySelector("[data-markdown-source]");
  const bodyCount = document.querySelector("[data-body-count]");
  const editorMount = document.querySelector("[data-wysiwyg-editor]");
  const compatibilityWarning = document.querySelector("[data-editor-compatibility-warning]");
  const modeNote = document.querySelector("[data-editor-mode-note]");
  let markdownEditor = null;
  let editorReady = false;

  const updateCount = (value) => {
    if (bodyCount) bodyCount.textContent = `${value.length.toLocaleString("es-AR")} caracteres`;
  };

  const normalizedMarkdown = (value) => value.replace(/\r\n?/g, "\n").trim();

  if (body && editorMount && window.toastui && window.toastui.Editor) {
    const originalMarkdown = body.value;
    const toolbarItems = [
      ["heading", "bold", "italic", "strike"],
      ["hr", "quote"],
      ["ul", "ol", "task", "indent", "outdent"],
      ["table", "link"],
      ["code", "codeblock"],
    ];
    const createMarkdownEditor = (initialEditType, hideModeSwitch) => new window.toastui.Editor({
      el: editorMount,
      height: "560px",
      initialEditType,
      initialValue: originalMarkdown,
      hideModeSwitch,
      language: "es-ES",
      previewStyle: "vertical",
      theme: root.getAttribute("data-theme") === "terminal" ? "dark" : "",
      toolbarItems,
      usageStatistics: false,
      hooks: {
        addImageBlobHook: () => {
          if (modeNote) modeNote.textContent = "La carga de imágenes todavía no está disponible.";
          return false;
        },
      },
      events: {
        change: () => {
          if (!editorReady || !markdownEditor) return;
          updateCount(markdownEditor.getMarkdown());
        },
      },
    });

    try {
      editorMount.hidden = false;
      markdownEditor = createMarkdownEditor("wysiwyg", false);
      const roundTripSafe = normalizedMarkdown(markdownEditor.getMarkdown()) === normalizedMarkdown(originalMarkdown);
      if (!roundTripSafe) {
        markdownEditor.destroy();
        editorMount.replaceChildren();
        markdownEditor = null;
        editorMount.hidden = true;
        body.hidden = false;
        if (compatibilityWarning) compatibilityWarning.hidden = false;
        if (modeNote) modeNote.hidden = true;
      } else {
        body.hidden = true;
        editorReady = true;
        applyEditorTheme(root.getAttribute("data-theme") || "editorial");
      }
    } catch (error) {
      editorMount.hidden = true;
      body.hidden = false;
      if (compatibilityWarning) {
        compatibilityWarning.textContent = "No se pudo cargar el editor visual. Podés seguir editando el Markdown sin perder contenido.";
        compatibilityWarning.hidden = false;
      }
    }
  }
  if (body) {
    body.addEventListener("input", () => updateCount(body.value));
    updateCount(body.value);
    const form = body.closest("form");
    if (form) {
      form.addEventListener("submit", () => {
        if (markdownEditor) body.value = markdownEditor.getMarkdown();
      });
    }
  }

  const editorForm = document.querySelector("[data-editor-form]");
  if (editorForm) {
    editorForm.addEventListener("submit", (event) => {
      if (!event.submitter || event.submitter.value !== "publish") return;
      const button = event.submitter;
      const originalLabel = button.textContent;
      button.textContent = "Actualizando…";
      button.setAttribute("aria-label", `${originalLabel}. Publicando y actualizando el sitio.`);
    });
  }

  const newNoteForm = document.querySelector("[data-new-note]");
  document.querySelectorAll("[data-publish-form]").forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector("[data-publish-button]");
      const status = document.querySelector("[data-publishing-status]");
      if (button) {
        button.disabled = true;
        button.textContent = "Actualizando…";
      }
      if (status) status.hidden = false;
    });
  });

  if (!newNoteForm) return;

  const title = newNoteForm.querySelector("#title");
  const slug = newNoteForm.querySelector("#slug");
  if (!title || !slug) return;

  let slugEdited = Boolean(slug.value);
  slug.addEventListener("input", () => { slugEdited = Boolean(slug.value); });
  title.addEventListener("input", () => {
    if (slugEdited) return;
    slug.value = title.value
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  });
})();
