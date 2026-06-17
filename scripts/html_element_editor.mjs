#!/usr/bin/env node

import { copyFile, mkdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const VOID_TAGS = new Set([
  "area",
  "base",
  "br",
  "col",
  "embed",
  "hr",
  "img",
  "input",
  "link",
  "meta",
  "param",
  "source",
  "track",
  "wbr"
]);

const SKIP_TAGS = new Set([
  "html",
  "head",
  "body",
  "script",
  "style",
  "meta",
  "link",
  "title",
  "template",
  "svg",
  "path",
  "noscript"
]);

const ATTR_EDIT_TAGS = new Set([
  "img",
  "input",
  "textarea",
  "select",
  "option",
  "a",
  "button"
]);

const SIGNAL_ATTRS = [
  "alt",
  "aria-label",
  "title",
  "placeholder",
  "value",
  "href",
  "src"
];

const HELP = `
Codex HTML Element Editor

Usage:
  node tools/codex-html-editor.mjs scan <html-file> [--name page-name] [--out .codex-html-editor] [--all]
  node tools/codex-html-editor.mjs list <map-json>
  node tools/codex-html-editor.mjs text <map-json> <id> <new text> [--html] [--no-rescan]
  node tools/codex-html-editor.mjs style <map-json> <id> "color: #111; font-size: 20px" [--replace] [--no-rescan]
  node tools/codex-html-editor.mjs attr <map-json> <id> <attr-name> <value> [--no-rescan]

Examples:
  npm run html:scan -- ./index.html --name homepage
  npm run html:list -- .codex-html-editor/homepage.map.json
  npm run html:text -- .codex-html-editor/homepage.map.json 12 "Start now"
  npm run html:style -- .codex-html-editor/homepage.map.json 12 "background: #111; color: white"
`;

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});

async function main() {
  const [command, ...rest] = process.argv.slice(2);

  if (!command || command === "-h" || command === "--help") {
    process.stdout.write(HELP.trimStart());
    return;
  }

  const { positional, flags } = parseArgs(rest);

  if (command === "scan") {
    await runScan(positional, flags);
    return;
  }

  if (command === "list") {
    await runList(positional);
    return;
  }

  if (command === "text" || command === "set-text") {
    await runText(positional, flags);
    return;
  }

  if (command === "style" || command === "set-style") {
    await runStyle(positional, flags);
    return;
  }

  if (command === "attr" || command === "set-attr") {
    await runAttr(positional, flags);
    return;
  }

  throw new Error(`Unknown command: ${command}\n\n${HELP}`);
}

async function runScan(positional, flags) {
  const sourcePath = requiredPath(positional[0], "Missing <html-file>.");
  const result = await scanHtmlFile(sourcePath, {
    name: flags.name,
    outDir: flags.out,
    all: Boolean(flags.all)
  });

  printScanResult(result);
}

async function runList(positional) {
  const mapPath = requiredPath(positional[0], "Missing <map-json>.");
  const map = await readMap(mapPath);
  printElementTable(map.elements);
}

async function runText(positional, flags) {
  const mapPath = requiredPath(positional[0], "Missing <map-json>.");
  const id = required(positional[1], "Missing <id>.");
  const newText = required(positional[2], "Missing <new text>.");
  const map = await readMap(mapPath);
  const result = await updateElement(map, id, (html, element) => {
    if (!Number.isFinite(element.endTagStartIndex)) {
      throw new Error(
        `#${id} is a <${element.tag}> element without inner text. Use the attr command instead.`
      );
    }

    const replacement = flags.html ? newText : escapeHtmlText(newText);
    return (
      html.slice(0, element.startTagEndIndex) +
      replacement +
      html.slice(element.endTagStartIndex)
    );
  });

  await afterWrite(mapPath, map, flags);
  console.log(`Updated #${id} text in ${result.sourcePath}`);
  console.log(`Backup: ${result.backupPath}`);
}

async function runStyle(positional, flags) {
  const mapPath = requiredPath(positional[0], "Missing <map-json>.");
  const id = required(positional[1], "Missing <id>.");
  const styleText = required(positional[2], "Missing <style text>.");
  const map = await readMap(mapPath);
  const result = await updateElement(map, id, (html, element) => {
    const startTag = html.slice(element.startIndex, element.startTagEndIndex);
    const currentStyle = getAttributeValue(startTag, "style") || "";
    const nextStyle = flags.replace
      ? normalizeStyleText(styleText)
      : mergeStyleText(currentStyle, styleText);
    const nextStartTag = setAttribute(startTag, "style", nextStyle);

    return (
      html.slice(0, element.startIndex) +
      nextStartTag +
      html.slice(element.startTagEndIndex)
    );
  });

  await afterWrite(mapPath, map, flags);
  console.log(`Updated #${id} style in ${result.sourcePath}`);
  console.log(`Backup: ${result.backupPath}`);
}

async function runAttr(positional, flags) {
  const mapPath = requiredPath(positional[0], "Missing <map-json>.");
  const id = required(positional[1], "Missing <id>.");
  const attrName = required(positional[2], "Missing <attr-name>.");
  const attrValue = required(positional[3], "Missing <value>.");
  const map = await readMap(mapPath);
  const result = await updateElement(map, id, (html, element) => {
    const startTag = html.slice(element.startIndex, element.startTagEndIndex);
    const nextStartTag = setAttribute(startTag, attrName, attrValue);

    return (
      html.slice(0, element.startIndex) +
      nextStartTag +
      html.slice(element.startTagEndIndex)
    );
  });

  await afterWrite(mapPath, map, flags);
  console.log(`Updated #${id} ${attrName} attribute in ${result.sourcePath}`);
  console.log(`Backup: ${result.backupPath}`);
}

async function scanHtmlFile(sourcePathInput, options = {}) {
  const sourcePath = path.resolve(sourcePathInput);
  const html = await readFile(sourcePath, "utf8");
  const sourceStat = await stat(sourcePath);
  const parsed = parseHtml(html);
  const candidates = pickCandidates(parsed.elements, html, {
    includeAll: Boolean(options.all)
  });

  candidates.forEach((element, index) => {
    element.inspectId = String(index + 1);
  });

  const name = sanitizeName(
    options.name || path.basename(sourcePath, path.extname(sourcePath))
  );
  const outDir = path.resolve(options.outDir || ".codex-html-editor");
  await mkdir(outDir, { recursive: true });

  const mapPath = path.join(outDir, `${name}.map.json`);
  const previewPath = path.join(outDir, `${name}.numbered.html`);
  const map = {
    version: 1,
    name,
    source: sourcePath,
    sourceMtimeMs: sourceStat.mtimeMs,
    createdAt: new Date().toISOString(),
    preview: previewPath,
    elements: candidates.map((element) => toMapElement(element, html, parsed))
  };

  await writeFile(mapPath, `${JSON.stringify(map, null, 2)}\n`, "utf8");
  await writeFile(previewPath, buildPreviewHtml(html, candidates), "utf8");

  return {
    map,
    mapPath,
    previewPath,
    count: candidates.length
  };
}

async function updateElement(map, id, mutate) {
  const sourcePath = path.resolve(map.source);
  const html = await readFile(sourcePath, "utf8");
  const parsed = parseHtml(html);
  const mapElement = map.elements.find((element) => String(element.id) === String(id));

  if (!mapElement) {
    throw new Error(`#${id} does not exist in ${map.name}.`);
  }

  const element = findCurrentElement(parsed.elements, mapElement);
  if (!element) {
    throw new Error(
      `Could not locate #${id} in the current HTML. Re-run scan and try again.`
    );
  }

  const nextHtml = mutate(html, element);
  const backupPath = `${sourcePath}.bak.${timestampForFile()}`;
  await copyFile(sourcePath, backupPath);
  await writeFile(sourcePath, nextHtml, "utf8");

  return {
    sourcePath,
    backupPath
  };
}

async function afterWrite(mapPath, map, flags) {
  if (flags["no-rescan"]) {
    return;
  }

  const refreshed = await scanHtmlFile(map.source, {
    name: map.name,
    outDir: path.dirname(path.resolve(mapPath))
  });
  console.log(`Refreshed map: ${refreshed.mapPath}`);
  console.log(`Refreshed preview: ${refreshed.previewPath}`);
}

async function readMap(mapPathInput) {
  const mapPath = path.resolve(mapPathInput);
  const raw = await readFile(mapPath, "utf8");
  const map = JSON.parse(raw);

  if (!map || map.version !== 1 || !Array.isArray(map.elements) || !map.source) {
    throw new Error(`${mapPath} is not a Codex HTML editor map.`);
  }

  return map;
}

function parseHtml(html) {
  const elements = [];
  const stack = [];
  const tagRe =
    /<!--[\s\S]*?-->|<![^>]*>|<\s*\/?\s*[A-Za-z][\w:-]*(?:\s[^<>]*?)?>/g;
  let match;

  while ((match = tagRe.exec(html))) {
    const token = match[0];

    if (token.startsWith("<!--") || token.startsWith("<!")) {
      continue;
    }

    const closeMatch = /^<\s*\/\s*([A-Za-z][\w:-]*)/i.exec(token);
    if (closeMatch) {
      const tag = closeMatch[1].toLowerCase();
      closeStackToTag(stack, tag, match.index, match.index + token.length);
      continue;
    }

    const openMatch = /^<\s*([A-Za-z][\w:-]*)\b([\s\S]*?)>$/i.exec(token);
    if (!openMatch) {
      continue;
    }

    const tag = openMatch[1].toLowerCase();
    const selfClosing = /\/\s*>$/.test(token);
    const isVoid = VOID_TAGS.has(tag);
    const element = {
      order: elements.length,
      tag,
      startIndex: match.index,
      startTagEndIndex: match.index + token.length,
      attrInsertIndex: match.index + token.length - (selfClosing ? 2 : 1),
      endTagStartIndex: null,
      closeEndIndex: selfClosing || isVoid ? match.index + token.length : null,
      attrs: parseAttributes(token),
      parent: stack.length ? stack[stack.length - 1] : null,
      children: [],
      path: ""
    };

    if (element.parent) {
      element.parent.children.push(element);
    }

    elements.push(element);

    if (tag === "script" || tag === "style") {
      const closeRe = new RegExp(`</\\s*${escapeRegExp(tag)}\\s*>`, "ig");
      closeRe.lastIndex = tagRe.lastIndex;
      const close = closeRe.exec(html);
      if (close) {
        element.endTagStartIndex = close.index;
        element.closeEndIndex = close.index + close[0].length;
        tagRe.lastIndex = element.closeEndIndex;
      }
      continue;
    }

    if (!selfClosing && !isVoid) {
      stack.push(element);
    }
  }

  while (stack.length) {
    const element = stack.pop();
    element.endTagStartIndex = html.length;
    element.closeEndIndex = html.length;
  }

  assignTreePaths(elements);

  return { elements };
}

function closeStackToTag(stack, tag, closeStart, closeEnd) {
  for (let index = stack.length - 1; index >= 0; index -= 1) {
    if (stack[index].tag !== tag) {
      continue;
    }

    while (stack.length > index) {
      const element = stack.pop();
      if (element.tag === tag) {
        element.endTagStartIndex = closeStart;
        element.closeEndIndex = closeEnd;
        return;
      }

      element.endTagStartIndex = closeStart;
      element.closeEndIndex = closeStart;
    }
  }
}

function assignTreePaths(elements) {
  const roots = elements.filter((element) => !element.parent);
  assignChildrenPaths({ path: "document", children: roots });
}

function assignChildrenPaths(parent) {
  const counts = new Map();

  for (const child of parent.children) {
    const nextCount = (counts.get(child.tag) || 0) + 1;
    counts.set(child.tag, nextCount);
    child.path = `${parent.path}>${child.tag}[${nextCount}]`;
    assignChildrenPaths(child);
  }
}

function pickCandidates(elements, html, options = {}) {
  const candidates = [];

  for (const element of elements) {
    if (SKIP_TAGS.has(element.tag)) {
      continue;
    }

    const directText = getDirectText(element, html);
    const fullText = getFullText(element, html);
    const attrSignal = getAttributeSignal(element.attrs);
    const hasUsefulText = directText.length > 0;
    const hasUsefulAttr =
      ATTR_EDIT_TAGS.has(element.tag) && attrSignal && attrSignal.value.length > 0;

    if (options.includeAll) {
      candidates.push(element);
      continue;
    }

    if (hasUsefulText || hasUsefulAttr) {
      element.directText = directText;
      element.fullText = fullText;
      element.attrSignal = attrSignal;
      candidates.push(element);
    }
  }

  return candidates;
}

function toMapElement(element, html, parsed) {
  const location = indexToLineColumn(html, element.startIndex);
  const endLocation = indexToLineColumn(
    html,
    Number.isFinite(element.endTagStartIndex)
      ? element.endTagStartIndex
      : element.startTagEndIndex
  );

  return {
    id: element.inspectId,
    tag: element.tag,
    line: location.line,
    column: location.column,
    endLine: endLocation.line,
    path: element.path,
    selectorHint: selectorHint(element),
    text: truncate(element.fullText || getFullText(element, html), 180),
    directText: truncate(element.directText || getDirectText(element, html), 180),
    attrs: pickDisplayAttributes(element.attrs),
    startIndex: element.startIndex,
    startTagEndIndex: element.startTagEndIndex,
    endTagStartIndex: element.endTagStartIndex,
    closeEndIndex: element.closeEndIndex,
    sourceOrder: element.order,
    childCount: element.children.length,
    siblingSummary: siblingSummary(element, parsed.elements)
  };
}

function findCurrentElement(elements, mapElement) {
  const byPath = elements.find(
    (element) => element.path === mapElement.path && element.tag === mapElement.tag
  );

  if (byPath) {
    return byPath;
  }

  const byIndex = elements.find(
    (element) =>
      element.startIndex === mapElement.startIndex && element.tag === mapElement.tag
  );

  return byIndex || null;
}

function buildPreviewHtml(html, candidates) {
  const inserts = candidates
    .map((element) => ({
      index: element.attrInsertIndex,
      text: ` data-codex-inspect-id="${escapeAttribute(element.inspectId)}"`
    }))
    .sort((a, b) => b.index - a.index);

  let markedHtml = html;
  for (const insert of inserts) {
    markedHtml =
      markedHtml.slice(0, insert.index) + insert.text + markedHtml.slice(insert.index);
  }

  const overlay = previewOverlay();
  const bodyClose = /<\/body\s*>/i.exec(markedHtml);

  if (bodyClose) {
    const index = bodyClose.index;
    return markedHtml.slice(0, index) + overlay + markedHtml.slice(index);
  }

  return `${markedHtml}\n${overlay}`;
}

function previewOverlay() {
  return `
<style id="codex-html-editor-style">
  [data-codex-inspect-id] {
    outline: 1.5px solid rgba(37, 99, 235, 0.72) !important;
    outline-offset: 2px !important;
  }
  [data-codex-inspect-id].codex-html-editor-selected {
    outline: 3px solid rgba(245, 158, 11, 0.95) !important;
  }
  .codex-html-editor-badge {
    align-items: center !important;
    background: #111827 !important;
    border: 1px solid rgba(255, 255, 255, 0.8) !important;
    border-radius: 999px !important;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.22) !important;
    color: white !important;
    cursor: pointer !important;
    display: inline-flex !important;
    font: 700 12px/1 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    height: 22px !important;
    justify-content: center !important;
    min-width: 22px !important;
    padding: 0 7px !important;
    pointer-events: auto !important;
    position: absolute !important;
    transform: translate(-4px, -10px) !important;
    user-select: none !important;
    z-index: 2147483647 !important;
  }
  .codex-html-editor-toast {
    background: #111827 !important;
    border-radius: 8px !important;
    bottom: 18px !important;
    box-shadow: 0 12px 32px rgba(15, 23, 42, 0.28) !important;
    color: white !important;
    font: 600 13px/1.4 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    left: 50% !important;
    max-width: min(420px, calc(100vw - 32px)) !important;
    padding: 10px 13px !important;
    pointer-events: none !important;
    position: fixed !important;
    transform: translateX(-50%) !important;
    z-index: 2147483647 !important;
  }
</style>
<script id="codex-html-editor-script">
(() => {
  const badgeClass = "codex-html-editor-badge";
  const selectedClass = "codex-html-editor-selected";
  let selected = null;
  let toastTimer = null;
  let frame = null;

  function editableElements() {
    return Array.from(document.querySelectorAll("[data-codex-inspect-id]"));
  }

  function isVisible(rect) {
    return rect.width > 1 && rect.height > 1;
  }

  function scheduleRender() {
    if (frame) return;
    frame = window.requestAnimationFrame(() => {
      frame = null;
      renderBadges();
    });
  }

  function renderBadges() {
    document.querySelectorAll("." + badgeClass).forEach((badge) => badge.remove());

    for (const element of editableElements()) {
      const rect = element.getBoundingClientRect();
      if (!isVisible(rect)) continue;

      const badge = document.createElement("button");
      const id = element.getAttribute("data-codex-inspect-id");
      badge.className = badgeClass;
      badge.type = "button";
      badge.textContent = id;
      badge.title = "Element #" + id;
      badge.style.left = window.scrollX + rect.left + "px";
      badge.style.top = window.scrollY + rect.top + "px";
      badge.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        selectElement(element);
      });
      document.body.appendChild(badge);
    }
  }

  function selectElement(element) {
    if (selected) {
      selected.classList.remove(selectedClass);
    }

    selected = element;
    selected.classList.add(selectedClass);

    const id = selected.getAttribute("data-codex-inspect-id");
    const label = "Selected element #" + id;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(id).catch(() => {});
    }
    showToast(label + " (number copied if browser allows it)");
  }

  function showToast(message) {
    if (toastTimer) {
      window.clearTimeout(toastTimer);
    }

    let toast = document.querySelector(".codex-html-editor-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.className = "codex-html-editor-toast";
      document.body.appendChild(toast);
    }

    toast.textContent = message;
    toastTimer = window.setTimeout(() => toast.remove(), 2200);
  }

  document.addEventListener("click", (event) => {
    const element = event.target.closest && event.target.closest("[data-codex-inspect-id]");
    if (!element || event.target.classList.contains(badgeClass)) return;
    event.preventDefault();
    event.stopPropagation();
    selectElement(element);
  }, true);

  window.addEventListener("resize", scheduleRender);
  window.addEventListener("scroll", scheduleRender, true);
  document.addEventListener("DOMContentLoaded", scheduleRender);
  window.addEventListener("load", scheduleRender);
  scheduleRender();
})();
</script>`;
}

function getDirectText(element, html) {
  if (!Number.isFinite(element.endTagStartIndex)) {
    return "";
  }

  let position = element.startTagEndIndex;
  const end = element.endTagStartIndex;
  let raw = "";

  const children = [...element.children].sort((a, b) => a.startIndex - b.startIndex);
  for (const child of children) {
    if (child.startIndex >= end) {
      continue;
    }

    raw += html.slice(position, child.startIndex);
    position = Math.min(end, child.closeEndIndex || child.startTagEndIndex);
  }

  raw += html.slice(position, end);

  return cleanText(raw);
}

function getFullText(element, html) {
  if (!Number.isFinite(element.endTagStartIndex)) {
    const signal = getAttributeSignal(element.attrs);
    return signal ? signal.value : "";
  }

  return cleanText(html.slice(element.startTagEndIndex, element.endTagStartIndex));
}

function cleanText(value) {
  return decodeEntities(
    value
      .replace(/<!--[\s\S]*?-->/g, " ")
      .replace(/<script\b[\s\S]*?<\/script>/gi, " ")
      .replace(/<style\b[\s\S]*?<\/style>/gi, " ")
      .replace(/<[^>]+>/g, " ")
      .replace(/\s+/g, " ")
      .trim()
  );
}

function parseAttributes(token) {
  const open = /^<\s*[A-Za-z][\w:-]*\b([\s\S]*?)\/?>$/i.exec(token);
  if (!open) {
    return {};
  }

  const raw = open[1].replace(/\/\s*$/, "");
  const attrs = {};
  const attrRe = /([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>/]+)))?/g;
  let match;

  while ((match = attrRe.exec(raw))) {
    const name = match[1];
    attrs[name] = decodeEntities(match[2] ?? match[3] ?? match[4] ?? "");
  }

  return attrs;
}

function setAttribute(startTag, attrName, attrValue) {
  const escapedName = escapeRegExp(attrName);
  const attrRe = new RegExp(
    `(\\s${escapedName})(?:\\s*=\\s*(?:"[^"]*"|'[^']*'|[^\\s>\\/]+))?`,
    "i"
  );
  const nextAttr = ` ${attrName}="${escapeAttribute(attrValue)}"`;

  if (attrRe.test(startTag)) {
    return startTag.replace(attrRe, nextAttr);
  }

  if (/\/\s*>$/.test(startTag)) {
    return startTag.replace(/\s*\/\s*>$/, `${nextAttr} />`);
  }

  return startTag.replace(/\s*>$/, `${nextAttr}>`);
}

function getAttributeValue(startTag, attrName) {
  const attrs = parseAttributes(startTag);
  const exactKey = Object.keys(attrs).find(
    (key) => key.toLowerCase() === attrName.toLowerCase()
  );
  return exactKey ? attrs[exactKey] : "";
}

function mergeStyleText(currentStyle, incomingStyle) {
  const map = new Map();

  for (const declaration of splitStyleDeclarations(currentStyle)) {
    map.set(declaration.property.toLowerCase(), declaration);
  }

  for (const declaration of splitStyleDeclarations(incomingStyle)) {
    map.set(declaration.property.toLowerCase(), declaration);
  }

  return Array.from(map.values())
    .map((declaration) => `${declaration.property}: ${declaration.value}`)
    .join("; ");
}

function normalizeStyleText(styleText) {
  return splitStyleDeclarations(styleText)
    .map((declaration) => `${declaration.property}: ${declaration.value}`)
    .join("; ");
}

function splitStyleDeclarations(styleText) {
  return String(styleText)
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const separator = part.indexOf(":");
      if (separator === -1) {
        throw new Error(`Invalid CSS declaration: ${part}`);
      }

      return {
        property: part.slice(0, separator).trim(),
        value: part.slice(separator + 1).trim()
      };
    })
    .filter((declaration) => declaration.property && declaration.value);
}

function selectorHint(element) {
  if (element.attrs.id) {
    return `#${element.attrs.id}`;
  }

  const dataKey = Object.keys(element.attrs).find((key) =>
    key.toLowerCase().startsWith("data-")
  );
  if (dataKey) {
    return `[${dataKey}="${element.attrs[dataKey]}"]`;
  }

  if (element.attrs.class) {
    const firstClass = element.attrs.class.split(/\s+/).filter(Boolean)[0];
    if (firstClass) {
      return `${element.tag}.${firstClass}`;
    }
  }

  return element.tag;
}

function siblingSummary(element) {
  if (!element.parent) {
    return "root";
  }

  const sameTag = element.parent.children.filter((child) => child.tag === element.tag);
  const index = sameTag.indexOf(element) + 1;
  return `${element.tag} ${index}/${sameTag.length} under <${element.parent.tag}>`;
}

function pickDisplayAttributes(attrs) {
  const result = {};
  const keys = Object.keys(attrs).filter((key) => {
    const lower = key.toLowerCase();
    return (
      lower === "id" ||
      lower === "class" ||
      lower.startsWith("data-") ||
      SIGNAL_ATTRS.includes(lower)
    );
  });

  for (const key of keys) {
    result[key] = truncate(attrs[key], 120);
  }

  return result;
}

function getAttributeSignal(attrs) {
  for (const preferredName of SIGNAL_ATTRS) {
    const key = Object.keys(attrs).find(
      (attrName) => attrName.toLowerCase() === preferredName
    );
    if (key && String(attrs[key]).trim()) {
      return {
        name: key,
        value: String(attrs[key]).trim()
      };
    }
  }

  return null;
}

function parseArgs(args) {
  const positional = [];
  const flags = {};

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];

    if (!arg.startsWith("--")) {
      positional.push(arg);
      continue;
    }

    const trimmed = arg.slice(2);
    const equalIndex = trimmed.indexOf("=");
    if (equalIndex !== -1) {
      flags[trimmed.slice(0, equalIndex)] = trimmed.slice(equalIndex + 1);
      continue;
    }

    const next = args[index + 1];
    if (next && !next.startsWith("--")) {
      flags[trimmed] = next;
      index += 1;
    } else {
      flags[trimmed] = true;
    }
  }

  return { positional, flags };
}

function printScanResult(result) {
  console.log(`Scanned ${result.count} editable elements.`);
  console.log(`Preview: ${pathToFileURL(result.previewPath).href}`);
  console.log(`Map: ${result.mapPath}`);
  console.log("");
  printElementTable(result.map.elements.slice(0, 30));

  if (result.map.elements.length > 30) {
    console.log(`... ${result.map.elements.length - 30} more elements in the map.`);
  }
}

function printElementTable(elements) {
  const rows = elements.map((element) => ({
    id: String(element.id),
    tag: element.tag,
    line: String(element.line),
    selector: element.selectorHint,
    text: element.text || element.directText || JSON.stringify(element.attrs)
  }));

  const widths = {
    id: Math.max(2, ...rows.map((row) => row.id.length)),
    tag: Math.max(3, ...rows.map((row) => row.tag.length)),
    line: Math.max(4, ...rows.map((row) => row.line.length)),
    selector: Math.max(8, ...rows.map((row) => row.selector.length))
  };

  console.log(
    `${pad("ID", widths.id)}  ${pad("Tag", widths.tag)}  ${pad(
      "Line",
      widths.line
    )}  ${pad("Selector", widths.selector)}  Text`
  );
  console.log(
    `${"-".repeat(widths.id)}  ${"-".repeat(widths.tag)}  ${"-".repeat(
      widths.line
    )}  ${"-".repeat(widths.selector)}  ${"-".repeat(40)}`
  );

  for (const row of rows) {
    console.log(
      `${pad(row.id, widths.id)}  ${pad(row.tag, widths.tag)}  ${pad(
        row.line,
        widths.line
      )}  ${pad(row.selector, widths.selector)}  ${truncate(row.text, 90)}`
    );
  }
}

function required(value, message) {
  if (value === undefined || value === null || value === "") {
    throw new Error(message);
  }

  return value;
}

function requiredPath(value, message) {
  return path.resolve(required(value, message));
}

function sanitizeName(value) {
  return String(value)
    .trim()
    .replace(/[^A-Za-z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "page";
}

function indexToLineColumn(html, index) {
  const before = html.slice(0, index);
  const lines = before.split(/\n/);

  return {
    line: lines.length,
    column: lines[lines.length - 1].length + 1
  };
}

function escapeHtmlText(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function escapeAttribute(value) {
  return escapeHtmlText(value).replace(/"/g, "&quot;");
}

function decodeEntities(value) {
  return String(value).replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (entity, body) => {
    const lower = body.toLowerCase();

    if (lower.startsWith("#x")) {
      return String.fromCodePoint(Number.parseInt(lower.slice(2), 16));
    }

    if (lower.startsWith("#")) {
      return String.fromCodePoint(Number.parseInt(lower.slice(1), 10));
    }

    const named = {
      amp: "&",
      apos: "'",
      gt: ">",
      lt: "<",
      nbsp: " ",
      quot: "\""
    };

    return named[lower] || entity;
  });
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function truncate(value, max) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.length > max ? `${text.slice(0, max - 1)}...` : text;
}

function pad(value, width) {
  return String(value).padEnd(width, " ");
}

function timestampForFile() {
  return new Date().toISOString().replace(/[-:]/g, "").replace(/\..+$/, "");
}
