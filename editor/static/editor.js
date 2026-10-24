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
  const imageToolbar = document.querySelector("[data-image-toolbar]");
  const imageButton = document.querySelector("[data-image-open]");
  let markdownEditor = null;
  let editorReady = false;

  const updateCount = (value) => {
    if (bodyCount) bodyCount.textContent = `${value.length.toLocaleString("es-AR")} caracteres`;
  };

  const normalizedMarkdown = (value) => value.replace(/\r\n?/g, "\n").trim();

  // --- Image insertion -------------------------------------------------------------------------
  // Images become <figure class="note-photo"> HTML in the Markdown source. Toast UI would rewrite that
  // block in visual mode, so inserting switches the editor to Markdown mode and keeps it there.
  const withBlankLines = (before, after, block) => {
    const gap = (text, fromEnd) => "\n".repeat(Math.max(0, 2 - (fromEnd ? /\n*$/ : /^\n*/).exec(text)[0].length));
    return `${before === "" ? "" : gap(before, true)}${block}${after === "" ? "\n" : gap(after, false)}`;
  };

  const lockToMarkdownMode = () => {
    const toggle = editorMount && editorMount.querySelector(".toastui-editor-mode-switch");
    if (toggle) toggle.style.display = "none";
    if (modeNote) {
      modeNote.hidden = false;
      modeNote.textContent = "Esta nota incluye HTML de imágenes, así que sigue en modo Markdown para no alterar el contenido.";
    }
  };

  // Toast UI's WYSIWYG->Markdown serializer writes every empty paragraph after the first as a literal
  // "<br>" line. Pressing Enter a few times to "make room" for an image therefore leaves stray <br>s, so
  // drop blank/<br>-only lines directly around the insertion point (intentional <br>s elsewhere stay).
  const isEmptyLine = (line) => /^\s*(<br\s*\/?>)?\s*$/.test(line);
  const trimAround = (before, after) => {
    const head = before.split("\n");
    while (head.length && isEmptyLine(head[head.length - 1])) head.pop();
    const tail = after.split("\n");
    while (tail.length && isEmptyLine(tail[0])) tail.shift();
    return [head.join("\n"), tail.join("\n")];
  };

  // Replaces the current selection in the (Markdown-mode) Toast editor or the textarea.
  // `compose(before, after)` gets the text around the selection and returns [before, inserted, after], where
  // `before`/`after` may be trimmed copies. Only the changed range is replaced, through each editor's own
  // editing API, so the edit is one native undo step and earlier history is kept.
  const spliceMarkdown = (compose, textareaRange, options = {}) => {
    if (markdownEditor) {
      if (markdownEditor.isWysiwygMode()) markdownEditor.changeMode("markdown");
      const text = markdownEditor.getMarkdown();
      const lines = text.split("\n");
      const [[startLine, startCh], [endLine, endCh]] = options.selection || markdownEditor.getSelection();
      const offset = (line, ch) => lines.slice(0, line - 1).reduce((sum, item) => sum + item.length + 1, 0) + ch - 1;
      let start = offset(startLine, startCh);
      let end = offset(endLine, endCh);
      // Toast maps a visual-mode caret to the line after its block; honour a caret that was at the block's start.
      if (options.toLineStart) {
        const blockLine = startCh === 1 && startLine > 1 ? startLine - 1 : startLine;
        start = end = offset(blockLine, 1);
      }
      const [before, inserted, after] = compose(text.slice(0, start), text.slice(end));
      const posAt = (at) => {
        const upTo = text.slice(0, at).split("\n");
        return [upTo.length, upTo[upTo.length - 1].length + 1];
      };
      markdownEditor.replaceSelection(inserted, posAt(before.length), posAt(text.length - after.length));
      const upToCursor = (before + inserted).split("\n");
      const cursor = [upToCursor.length, upToCursor[upToCursor.length - 1].length + 1];
      markdownEditor.setSelection(cursor, cursor);
      markdownEditor.focus();
    } else if (body) {
      const { start, end } = textareaRange || { start: body.selectionStart, end: body.selectionEnd };
      const value = body.value;
      const [before, inserted, after] = compose(value.slice(0, start), value.slice(end));
      body.focus();
      body.setSelectionRange(before.length, value.length - after.length);
      // execCommand keeps the textarea's native undo stack; assigning .value would wipe it.
      let done = false;
      try {
        done = document.execCommand("insertText", false, inserted);
      } catch (error) {
        done = false;
      }
      if (!done) {
        body.setRangeText(inserted, before.length, value.length - after.length, "end");
        body.dispatchEvent(new Event("input", { bubbles: true }));
      }
    }
  };

  const currentBlock = (selection) => {
    const node = selection.rangeCount && selection.anchorNode;
    if (!node || !editorMount.contains(node)) return null;
    return (node.nodeType === 1 ? node : node.parentElement).closest("p, h1, h2, h3, h4, h5, h6");
  };

  const caretAtBlockStart = () => {
    if (!markdownEditor || !markdownEditor.isWysiwygMode()) return false;
    const selection = window.getSelection();
    const block = currentBlock(selection);
    if (!block || !selection.isCollapsed || block.closest("li, blockquote, table, pre") || !block.textContent) return false;
    const head = document.createRange();
    head.selectNodeContents(block);
    head.setEnd(selection.anchorNode, selection.anchorOffset);
    return head.toString().replace(/\u200b/g, "") === "";
  };

  const insertImageMarkup = (markup, textareaRange, atBlockStart, selection) => {
    const wasToast = Boolean(markdownEditor);
    spliceMarkdown((before, after) => {
      const [head, tail] = trimAround(before, after);
      return [head, withBlankLines(head, tail, markup), tail];
    }, textareaRange, { toLineStart: atBlockStart, selection });
    if (wasToast) lockToMarkdownMode();
  };

  // --- Pasting text ---------------------------------------------------------------------------
  // Toast UI drops the blank line between pasted paragraphs (Markdown mode) or merges adjacent <p>s into
  // one Markdown paragraph (WYSIWYG mode: "A\nB"). Rebuild the clipboard payload so paragraph
  // boundaries survive, and keep single line breaks as single newlines.
  const BLOCK_TAGS = /<(p|div|h[1-6]|ul|ol|li|blockquote|pre|br|figure)\b/i;

  const htmlToMarkdown = (html) => {
    const doc = new DOMParser().parseFromString(html, "text/html");
    const wrap = (inner, mark) => inner.replace(/^(\s*)([\s\S]*?)(\s*)$/, `$1${mark}$2${mark}$3`);
    const inline = (node) => Array.from(node.childNodes).map((child) => {
      if (child.nodeType === 3) return child.nodeValue.replace(/\s+/g, " ");
      if (child.nodeType !== 1) return "";
      const tag = child.tagName.toLowerCase();
      const inner = inline(child);
      if (tag === "br") return "\n";
      if (tag === "a" && child.getAttribute("href") && inner.trim()) return `[${inner.trim()}](${child.getAttribute("href")})`;
      if (tag === "code" && inner.trim()) return `\`${inner}\``;
      const bold = (tag === "strong" || tag === "b") && child.style.fontWeight !== "normal";
      const italic = (tag === "em" || tag === "i" || child.style.fontStyle === "italic") && inner.trim();
      if (bold && inner.trim()) return wrap(inner, "**");
      return italic ? wrap(inner, "*") : inner;
    }).join("");
    const clean = (value) => value.replace(/[ \t]*\n[ \t]*/g, "\n").trim();
    const esc = (value) => value.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    // A rendered .note-photo figure goes back to the exact markup the editor inserts.
    const figureMarkup = (node) => {
      const img = node.querySelector("img");
      if (!img || !img.getAttribute("src")) return "";
      const url = new URL(img.getAttribute("src"), "https://example.invalid/");
      const src = url.pathname.startsWith("/assets/img/notes/") ? url.pathname : img.getAttribute("src");
      const size = ["width", "height"].filter((name) => img.getAttribute(name)).map((name) => ` ${name}="${esc(img.getAttribute(name))}"`).join("");
      const caption = node.querySelector("figcaption");
      return [
        '<figure class="note-photo">',
        `  <img src="${esc(src)}" alt="${esc(img.getAttribute("alt") || "")}"${size} loading="lazy" />`,
        ...(caption && clean(caption.textContent) ? [`  <figcaption>${esc(clean(caption.textContent))}</figcaption>`] : []),
        "</figure>",
      ].join("\n");
    };
    const hasBlocks = (node) => node.querySelector("p, div, h1, h2, h3, h4, h5, h6, ul, ol, blockquote, pre, table");
    const blocks = [];
    const walk = (parent) => parent.childNodes.forEach((node) => {
      if (node.nodeType === 3) { if (node.nodeValue.trim()) blocks.push(clean(node.nodeValue)); return; }
      if (node.nodeType !== 1) return;
      const tag = node.tagName.toLowerCase();
      if (tag === "figure") blocks.push(figureMarkup(node));
      else if (/^h[1-6]$/.test(tag)) blocks.push(`${"#".repeat(Number(tag[1]))} ${clean(inline(node))}`);
      else if (tag === "ul" || tag === "ol") {
        blocks.push(Array.from(node.children).filter((item) => item.tagName === "LI")
          .map((item, index) => `${tag === "ol" ? `${index + 1}.` : "-"} ${clean(inline(item)).replace(/\n/g, " ")}`).join("\n"));
      } else if (tag === "blockquote") blocks.push(clean(inline(node)).split("\n").map((line) => `> ${line}`).join("\n"));
      else if (tag === "pre") blocks.push(`\`\`\`\n${node.textContent.replace(/\n$/, "")}\n\`\`\``);
      else if (tag === "table" || tag === "script" || tag === "style" || tag === "meta") return;
      else if (hasBlocks(node)) walk(node);
      else if (clean(inline(node))) blocks.push(clean(inline(node)));
    });
    walk(doc.body);
    return blocks.filter(Boolean).join("\n\n");
  };

  const markdownPasteText = (data) => {
    const html = data.getData("text/html");
    const text = (data.getData("text/plain") || "").replace(/\r\n?/g, "\n");
    // Copies made inside the editor carry ProseMirror's marker; plain text already is the Markdown.
    if (!html || html.includes("data-pm-slice") || !BLOCK_TAGS.test(html)) return text;
    return htmlToMarkdown(html) || text;
  };

  const pasteFigureMarkdown = (pasted) => {
    const atBlockStart = caretAtBlockStart();
    markdownEditor.changeMode("markdown");
    const selection = markdownEditor.getSelection(); // read now: it can drift while we wait below
    // Same reason as the image dialog: keep the insertion out of the mode switch's undo group.
    setTimeout(() => {
      spliceMarkdown((before, after) => {
        const [head, tail] = trimAround(before, after);
        return [head, withBlankLines(head, tail, pasted), tail];
      }, null, { toLineStart: atBlockStart, selection });
      lockToMarkdownMode();
    }, 600);
  };

  const watchTextPastes = (element) => {
    if (!element) return;
    element.addEventListener("paste", (event) => {
      const data = event.clipboardData;
      if (event.defaultPrevented || !data || (window.NicoImages && window.NicoImages.imageFrom(data))) return;
      const html = data.getData("text/html");
      const text = data.getData("text/plain");
      if (!html && !text) return;
      const inToast = Boolean(markdownEditor) && element === editorMount;
      if (inToast && markdownEditor.isWysiwygMode()) {
        // Toast's WYSIWYG paste turns <p>A</p><p>B</p> into adjacent paragraphs, which serialize to "A\nB"
        // (one Markdown paragraph), and any blank separator into two empty paragraphs (a "<br>" line).
        // Multi-paragraph pastes are therefore spliced in as Markdown, then the editor returns to visual mode.
        const pasted = markdownPasteText(data);
        if (/<figure\b/i.test(pasted)) {
          // Visual mode would rewrite the figure (and escape it as text), so paste it as Markdown, like an image.
          event.preventDefault();
          event.stopPropagation();
          pasteFigureMarkdown(pasted.trim());
          return;
        }
        const selection = window.getSelection();
        const block = currentBlock(selection);
        if (!pasted.includes("\n\n") || html.includes("data-pm-slice") || !block
          || block.closest("li, blockquote, table, pre") || !selection.isCollapsed) return;
        const tail = document.createRange();
        tail.selectNodeContents(block);
        tail.setStart(selection.anchorNode, selection.anchorOffset);
        if (tail.toString().replace(/\u200b/g, "") !== "") return; // mid-paragraph: leave to Toast
        event.preventDefault();
        event.stopPropagation();
        spliceMarkdown((before, after) => {
          const [head, rest] = trimAround(before, after);
          return [head, withBlankLines(head, rest, pasted), rest];
        });
        markdownEditor.changeMode("wysiwyg");
        return;
      }
      if (inToast && event.target.closest && event.target.closest(".toastui-editor-md-preview")) return;
      const pasted = markdownPasteText(data);
      if (!pasted) return;
      event.preventDefault();
      event.stopPropagation();
      spliceMarkdown((before, after) => [before, pasted, after]);
    }, true);
  };

  function openImageDialog(file) {
    if (!window.NicoImages) return;
    const range = body ? { start: body.selectionStart, end: body.selectionEnd } : { start: 0, end: 0 };
    const atBlockStart = caretAtBlockStart();
    // Figures cannot live in visual mode, so switch now rather than at insert time: the load into the Markdown
    // editor then gets its own history entry (seconds earlier), and Ctrl+Z after inserting only removes the image.
    const switched = Boolean(markdownEditor) && markdownEditor.isWysiwygMode();
    if (switched) markdownEditor.changeMode("markdown");
    const switchedAt = Date.now();
    const selection = markdownEditor ? markdownEditor.getSelection() : null; // caret as mapped right after the switch
    window.NicoImages.open(
      file || null,
      (markup) => {
        // Keep the insertion out of the load's undo group (ProseMirror merges edits closer than ~500 ms).
        const wait = switched ? Math.max(0, 600 - (Date.now() - switchedAt)) : 0;
        setTimeout(() => insertImageMarkup(markup, range, atBlockStart, selection), wait);
      },
      () => { if (switched && markdownEditor && !markdownEditor.isWysiwygMode()) markdownEditor.changeMode("wysiwyg"); },
    );
  }

  const watchImageDrops = (element) => {
    if (!element || !window.NicoImages) return;
    element.addEventListener("paste", (event) => {
      const data = event.clipboardData;
      const image = window.NicoImages.imageFrom(data);
      if (!image || (data.getData("text/plain") || "").trim()) return;
      event.preventDefault();
      event.stopPropagation();
      openImageDialog(image);
    }, true);
    element.addEventListener("dragover", (event) => {
      if (!event.dataTransfer || !Array.from(event.dataTransfer.types).includes("Files")) return;
      event.preventDefault();
      element.classList.add("editor-dragging");
    }, true);
    ["dragleave", "dragend"].forEach((name) => element.addEventListener(name, () => element.classList.remove("editor-dragging"), true));
    element.addEventListener("drop", (event) => {
      element.classList.remove("editor-dragging");
      const image = window.NicoImages.imageFrom(event.dataTransfer);
      if (!image) return;
      event.preventDefault();
      event.stopPropagation();
      openImageDialog(image);
    }, true);
  };
  watchImageDrops(editorMount);
  watchImageDrops(body);
  watchTextPastes(editorMount);
  watchTextPastes(body);
  if (editorMount) {
    // Toast UI binds redo to Ctrl/Cmd+Shift+Z only; Windows/Linux users also expect Ctrl+Y.
    editorMount.addEventListener("keydown", (event) => {
      if (!markdownEditor || !(event.ctrlKey || event.metaKey) || event.shiftKey || event.altKey || event.key.toLowerCase() !== "y") return;
      event.preventDefault();
      markdownEditor.exec("redo");
    }, true);
  }
  if (imageButton) imageButton.addEventListener("click", () => openImageDialog());
  const showTextareaToolbar = () => {
    if (imageToolbar && window.NicoImages) imageToolbar.hidden = false;
  };

  if (body && editorMount && window.toastui && window.toastui.Editor) {
    const originalMarkdown = body.value;
    const imageToolbarButton = document.createElement("button");
    imageToolbarButton.type = "button";
    imageToolbarButton.className = "toastui-editor-toolbar-icons nico-image-button";
    imageToolbarButton.setAttribute("aria-label", "Insertar imagen");
    imageToolbarButton.style.cssText = "background-image:none;";
    imageToolbarButton.innerHTML = '<svg class="image-icon" style="display:block;margin:2px;width:18px;height:18px" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="m21 16-5-5-9 9"/></svg>';
    imageToolbarButton.addEventListener("click", () => openImageDialog());
    const toolbarItems = [
      ["heading", "bold", "italic", "strike"],
      ["hr", "quote"],
      ["ul", "ol", "task", "indent", "outdent"],
      ["table", "link", { name: "nicoImage", tooltip: "Imagen", el: imageToolbarButton }],
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
        addImageBlobHook: (blob) => {
          openImageDialog(blob);
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
        showTextareaToolbar();
      } else {
        body.hidden = true;
        editorReady = true;
        applyEditorTheme(root.getAttribute("data-theme") || "editorial");
      }
    } catch (error) {
      editorMount.hidden = true;
      body.hidden = false;
      showTextareaToolbar();
      if (compatibilityWarning) {
        compatibilityWarning.textContent = "No se pudo cargar el editor visual. Podés seguir editando el Markdown sin perder contenido.";
        compatibilityWarning.hidden = false;
      }
    }
  }
  if (body && !window.toastui) showTextareaToolbar();
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
