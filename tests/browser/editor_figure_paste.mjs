// Browser regression: pasting a <figure class="note-photo"> between notes must keep the markup intact
// (no escaped "\<figure", no <br>, no rewritten <img>). Not part of `unittest discover`; run with Playwright:
//   PLAYWRIGHT_ENTRY=/path/to/node_modules/playwright/index.mjs node tests/browser/editor_figure_paste.mjs
// It starts the editor against a temporary project root and never touches content/ or static/.
import { spawn } from "node:child_process";
import { cpSync, mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = await import(process.env.PLAYWRIGHT_ENTRY || "playwright");
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const root = mkdtempSync(path.join(tmpdir(), "nico-editor-"));
const port = 5600 + Math.floor(Math.random() * 300);

const FIGURE = [
  '<figure class="note-photo">',
  '  <img src="/assets/img/notes/pipeta-alpine-linux-20260407.webp" alt="Pipeta, una Pi" width="1600" height="984" loading="lazy" />',
  "  <figcaption>Pipeta, lista para seguir.</figcaption>",
  "</figure>",
].join("\n");

mkdirSync(path.join(root, "content", "notes"), { recursive: true });
mkdirSync(path.join(root, "content", "drafts"), { recursive: true });
mkdirSync(path.join(root, "static", "img", "notes"), { recursive: true });
cpSync(path.join(repo, "static/img/notes/pipeta-alpine-linux-20260407.webp"), path.join(root, "static/img/notes/pipeta-alpine-linux-20260407.webp"));
const note = (lang, name, title, body) => writeFileSync(
  path.join(root, "content", "notes", name),
  `---\ntitle: ${title}\ndate: '2026-10-01'\nlang: ${lang}\nnote_id: 2026-10-01-par\nslug: ${name.slice(11, -3)}\n---\n\n${body}\n`,
);
note("es", "2026-10-01-es.md", "ES", `Antes\n\n${FIGURE}\n\nDespués`);
note("en", "2026-10-01-en.md", "EN", "Plain English text.");

const server = spawn(path.join(repo, ".venv/bin/python"), ["-c",
  `import sys; sys.path.insert(0, ${JSON.stringify(repo)}); from editor.app import create_app; create_app(${JSON.stringify(root)}, testing=True).run(port=${port})`,
], { stdio: "ignore" });
const base = `http://127.0.0.1:${port}`;
for (let i = 0; i < 50; i++) { try { await fetch(base); break; } catch { await new Promise((r) => setTimeout(r, 200)); } }

const browser = await chromium.launch();
let failures = 0;
const check = (name, ok, detail = "") => { if (!ok) failures++; console.log(`${ok ? "PASS" : "FAIL"} ${name}${ok ? "" : "  " + detail}`); };
const WW = ".toastui-editor-ww-container .ProseMirror";
const MD = ".toastui-editor-md-container .ProseMirror";
const clean = (md) => !/\\|<br>/.test(md.replace(/\/>/g, ""));
const bodyOf = async (page) => {
  await page.evaluate(() => document.querySelector("form[data-editor-form]").dispatchEvent(new Event("submit", { cancelable: true })));
  return (await page.inputValue("#body")).trim();
};
const paste = (page, selector, data) => page.evaluate(([sel, payload]) => {
  const dt = new DataTransfer();
  for (const [type, value] of Object.entries(payload)) dt.setData(type, value);
  document.querySelector(sel).dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
}, [selector, data]);
const openEn = async (context, mode) => {
  const page = await context.newPage();
  await page.goto(`${base}/notes/2026-10-01-en.md/edit`);
  await page.waitForSelector(".toastui-editor-defaultUI");
  if (mode === "markdown") await page.click(".toastui-editor-mode-switch .tab-item >> nth=0");
  return page;
};
const settle = (page) => page.waitForTimeout(900); // figure paste waits ~600 ms to keep its own undo step

try {
  const context = await browser.newContext({ viewport: { width: 1200, height: 900 } });
  await context.grantPermissions(["clipboard-read", "clipboard-write"], { origin: base });

  // Real clipboard: copy the figure out of the Markdown-only ES textarea, paste into the visual EN note.
  const es = await context.newPage();
  await es.goto(`${base}/notes/2026-10-01-es.md/edit`);
  await es.waitForSelector("[data-image-toolbar]:not([hidden])");
  const bodyText = await es.inputValue("#body");
  await es.evaluate(([from, to]) => { const t = document.querySelector("#body"); t.focus(); t.setSelectionRange(from, to); }, [bodyText.indexOf("<figure"), bodyText.indexOf("</figure>") + 9]);
  await es.keyboard.press("Control+c");
  const en = await openEn(context, "wysiwyg");
  await en.locator(WW).click();
  await en.waitForTimeout(300);
  await en.keyboard.press("Control+End");
  await en.keyboard.press("Control+v");
  await settle(en);
  let md = await bodyOf(en);
  check("real copy ES textarea -> paste EN visual keeps figure exactly", md === `Plain English text.\n\n${FIGURE}`, JSON.stringify(md));
  check("no backslashes or <br>", clean(md), md);
  check("editor stays in Markdown mode afterwards", await en.locator(".toastui-editor-mode-switch").isHidden());
  await en.keyboard.press("Control+z"); await settle(en);
  check("Ctrl+Z removes only the pasted figure", (await bodyOf(en)) === "Plain English text.", JSON.stringify(await bodyOf(en)));
  await en.close(); await es.close();

  const cases = [
    ["plain figure between paragraphs -> visual", "wysiwyg", { "text/plain": `Antes\n\n${FIGURE}\n\nDespués` }, `Antes\n\n${FIGURE}\n\nDespués`],
    ["Markdown-pane copy (ProseMirror html + plain) -> visual", "wysiwyg",
      { "text/html": `<div data-pm-slice="0 0 []"><div>${FIGURE.split("\n").join("</div><div>")}</div></div>`, "text/plain": FIGURE }, FIGURE],
    ["rendered figure html (article preview copy) -> visual", "wysiwyg",
      { "text/html": '<figure class="note-photo"><img src="http://127.0.0.1:1/assets/img/notes/pipeta-alpine-linux-20260407.webp" alt="Pipeta, una Pi" width="1600" height="984" loading="lazy"><figcaption>Pipeta, lista para seguir.</figcaption></figure>', "text/plain": "Pipeta, lista para seguir." }, FIGURE],
    ["plain figure -> Markdown mode", "markdown", { "text/plain": FIGURE }, `Plain English text.${FIGURE}`],
  ];
  for (const [name, mode, data, expectedTail] of cases) {
    const page = await openEn(context, mode);
    const selector = mode === "wysiwyg" ? WW : MD;
    await page.locator(selector).click();
    await page.waitForTimeout(300); // let Toast UI finish focusing before moving the caret
    await page.keyboard.press("Control+End");
    if (mode === "wysiwyg" && !name.startsWith("plain figure between")) { await page.keyboard.press("Enter"); await page.keyboard.press("Enter"); }
    await page.waitForTimeout(300); // let ProseMirror sync the caret before the paste, as a real user would
    await paste(page, selector, data);
    await settle(page);
    md = await bodyOf(page);
    const expected = mode === "markdown" ? expectedTail : name.startsWith("plain figure between") ? `Plain English text.\n\n${expectedTail}` : `Plain English text.\n\n${expectedTail}`;
    check(name, md === expected || (mode === "markdown" && md.endsWith(FIGURE)), JSON.stringify(md));
    check(`${name}: no backslashes/<br>`, clean(md), md);
    await page.close();
  }

  // Markdown-only textarea (custom HTML note): paste figure verbatim at the cursor.
  const page = await context.newPage();
  await page.goto(`${base}/notes/2026-10-01-es.md/edit`);
  await page.waitForSelector("[data-image-toolbar]:not([hidden])");
  const original = await page.inputValue("#body");
  await page.evaluate(() => { const t = document.querySelector("#body"); t.focus(); t.setSelectionRange(t.value.length, t.value.length); });
  await paste(page, "#body", { "text/plain": `\n\n${FIGURE}\n` });
  check("textarea paste inserts the figure verbatim", (await page.inputValue("#body")) === `${original}\n\n${FIGURE}\n`);
  await page.close();
} finally {
  await browser.close();
  server.kill();
}
console.log(failures ? `${failures} FAILED` : "ALL PASS");
process.exit(failures ? 1 : 0);
