(() => {
  "use strict";

  const body = document.querySelector("#body");
  const bodyCount = document.querySelector("[data-body-count]");
  if (body && bodyCount) {
    const updateCount = () => {
      bodyCount.textContent = `${body.value.length.toLocaleString("es-AR")} caracteres`;
    };
    body.addEventListener("input", updateCount);
    updateCount();
  }

  const newNoteForm = document.querySelector("[data-new-note]");
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
