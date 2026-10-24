(() => {
  "use strict";

  // Image dialog: choose/paste/drop -> upload for processing -> alt + caption -> markup returned by the server.
  // Exposes window.NicoImages.open(file?, onInsert) and NicoImages.imageFrom(dataTransfer).
  const dialog = document.querySelector("[data-image-dialog]");
  if (!dialog || typeof dialog.showModal !== "function") return;

  const $ = (selector) => dialog.querySelector(selector);
  const form = $("[data-image-form]");
  const input = $("[data-image-input]");
  const pick = $("[data-image-pick]");
  const step = $("[data-image-step]");
  const preview = $("[data-image-preview]");
  const progress = $("[data-image-progress]");
  const meta = $("[data-image-meta]");
  const altField = $("[data-image-alt]");
  const captionField = $("[data-image-caption]");
  const decorative = $("[data-image-decorative]");
  const errorBox = $("[data-image-error]");
  const insertButton = $("[data-image-insert]");
  const retryButton = $("[data-image-retry]");
  const reuseBox = $("[data-image-reuse]");
  const reuseList = $("[data-image-reuse-list]");
  const csrf = () => (document.querySelector('input[name="_csrf_token"]') || {}).value || "";

  const ALLOWED = ["image/jpeg", "image/png", "image/webp"];
  const MAX_BYTES = 15 * 1024 * 1024;

  let onInsert = null;
  let onCancel = null;
  let inserted = false;
  let request = null;
  let file = null;
  let localUrl = "";
  let staged = null; // {id} from the server, or {existing: name}
  let busy = false;

  const kb = (bytes) => (bytes >= 1048576 ? `${(bytes / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`);

  const showError = (message) => {
    errorBox.textContent = message || "";
    errorBox.hidden = !message;
  };

  const refresh = () => {
    const described = decorative.checked || altField.value.trim() !== "";
    insertButton.disabled = busy || !staged || !described;
    altField.disabled = decorative.checked;
    altField.required = !decorative.checked;
  };

  const reset = () => {
    if (request) request.abort();
    request = null;
    if (localUrl) URL.revokeObjectURL(localUrl);
    localUrl = "";
    file = null;
    staged = null;
    busy = false;
    form.reset();
    input.value = "";
    preview.removeAttribute("src");
    progress.hidden = true;
    progress.value = 0;
    meta.textContent = "";
    meta.classList.remove("is-error");
    retryButton.hidden = true;
    step.hidden = true;
    pick.hidden = false;
    showError("");
    refresh();
  };

  const fail = (message) => {
    busy = false;
    progress.hidden = true;
    meta.textContent = "";
    showError(message);
    retryButton.hidden = !file;
    refresh();
  };

  const describe = (data) => {
    const lines = [];
    const source = data.source;
    lines.push(`${data.width}×${data.height} px · ${kb(data.bytes)} · ${String(data.format).toUpperCase()}`);
    if (source) lines.push(`Original: ${source.width}×${source.height} px · ${kb(source.bytes)} · ${source.format}`);
    if (data.notes && data.notes.length) lines.push(data.notes.join(" · "));
    meta.textContent = lines.join("\n");
    meta.style.whiteSpace = "pre-line";
  };

  const upload = () => {
    showError("");
    retryButton.hidden = true;
    busy = true;
    progress.hidden = false;
    progress.value = 0;
    meta.textContent = "Subiendo…";
    refresh();

    const body = new FormData();
    body.append("_csrf_token", csrf());
    body.append("file", file, file.name || "pegada.png");
    const xhr = new XMLHttpRequest();
    request = xhr;
    xhr.open("POST", "/media/stage");
    xhr.responseType = "json";
    xhr.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) return;
      progress.value = (event.loaded / event.total) * 100;
      if (event.loaded === event.total) meta.textContent = "Optimizando imagen en el servidor…";
    });
    xhr.addEventListener("load", () => {
      request = null;
      const data = xhr.response;
      if (xhr.status === 200 && data && data.id) {
        staged = { id: data.id };
        busy = false;
        progress.hidden = true;
        describe(data);
        refresh();
        altField.focus();
      } else {
        fail((data && data.error) || "No se pudo subir la imagen. Probá de nuevo o recargá la página.");
      }
    });
    xhr.addEventListener("error", () => { request = null; fail("Se cortó la conexión mientras se subía la imagen."); });
    xhr.addEventListener("timeout", () => { request = null; fail("La subida tardó demasiado."); });
    xhr.timeout = 120000;
    xhr.send(body);
  };

  const begin = (chosen) => {
    reset();
    if (!ALLOWED.includes(chosen.type)) {
      showError("Formato no admitido. Usá JPEG, PNG o WebP.");
      return;
    }
    if (chosen.size > MAX_BYTES) {
      showError("La imagen supera el máximo de 15 MB.");
      return;
    }
    file = chosen;
    localUrl = URL.createObjectURL(chosen);
    preview.src = localUrl;
    pick.hidden = true;
    step.hidden = false;
    upload();
  };

  const useExisting = (src) => {
    reset();
    staged = { existing: src.split("/").pop() };
    preview.src = src;
    meta.textContent = "Imagen ya publicada: se reutiliza el mismo archivo, sin duplicarlo.";
    pick.hidden = true;
    step.hidden = false;
    refresh();
    altField.focus();
  };

  const close = () => {
    if (dialog.open) dialog.close();
  };

  dialog.addEventListener("close", () => {
    const cancel = inserted ? null : onCancel;
    onInsert = onCancel = null;
    reset();
    if (cancel) cancel();
  });
  dialog.querySelectorAll("[data-image-cancel]").forEach((button) => button.addEventListener("click", close));
  $("[data-image-choose]").addEventListener("click", () => input.click());
  input.addEventListener("change", () => {
    if (input.files && input.files[0]) begin(input.files[0]);
  });
  retryButton.addEventListener("click", () => { if (file) upload(); });
  altField.addEventListener("input", refresh);
  decorative.addEventListener("change", refresh);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (insertButton.disabled) return;
    busy = true;
    refresh();
    showError("");
    const body = new URLSearchParams({
      _csrf_token: csrf(),
      alt: altField.value,
      caption: captionField.value,
      decorative: decorative.checked ? "1" : "0",
    });
    if (staged.existing) body.set("existing", staged.existing);
    else body.set("id", staged.id);
    try {
      const response = await fetch("/media/commit", { method: "POST", body, credentials: "same-origin" });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.html) throw new Error(data.error || "No se pudo guardar la imagen.");
      const insert = onInsert;
      inserted = true;
      close();
      if (insert) insert(data.html);
    } catch (error) {
      busy = false;
      showError(error.message || "No se pudo guardar la imagen.");
      refresh();
    }
  });

  let reusable = [];
  try {
    reusable = JSON.parse(dialog.dataset.reusable || "[]");
  } catch (error) {
    reusable = [];
  }
  reusable.forEach((src) => {
    const button = document.createElement("button");
    button.type = "button";
    const thumb = document.createElement("img");
    thumb.src = src;
    thumb.alt = src.split("/").pop();
    button.append(thumb);
    button.title = src.split("/").pop();
    button.addEventListener("click", () => useExisting(src));
    reuseList.append(button);
  });
  reuseBox.hidden = reusable.length === 0;

  window.NicoImages = {
    open(chosen, insert, cancel) {
      onInsert = insert;
      onCancel = cancel || null;
      inserted = false;
      reset();
      if (!dialog.open) dialog.showModal();
      if (chosen) begin(chosen);
    },
    imageFrom(transfer) {
      if (!transfer || !transfer.files) return null;
      return Array.from(transfer.files).find((item) => item.type.startsWith("image/")) || null;
    },
  };
})();
