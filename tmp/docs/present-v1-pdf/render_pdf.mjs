import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { marked } from "marked";
import { chromium } from "playwright";

const ROOT = path.resolve("C:/Users/PK/Desktop/projects/telco_digital");
const SOURCE = path.join(ROOT, "docs/presentation/present_v1.md");
const DOC_DIR = path.dirname(SOURCE);
const SCRATCH = path.join(ROOT, "tmp/docs/present-v1-pdf");
const HTML_PATH = path.join(SCRATCH, "present_v1_reference.html");
const OUTPUT_DIR = path.join(ROOT, "docs/presentation/output");
const PDF_PATH = path.join(OUTPUT_DIR, "present_v1_reference.pdf");
const MERMAID_PATH = path.join(SCRATCH, "mermaid.min.js");
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";

await fs.mkdir(OUTPUT_DIR, { recursive: true });

const markdown = await fs.readFile(SOURCE, "utf8");
const mermaidBlocks = [];
const withoutMermaid = markdown.replace(/```mermaid\s*\n([\s\S]*?)```/g, (_match, source) => {
  const token = `MERMAID_BLOCK_${String(mermaidBlocks.length).padStart(3, "0")}`;
  mermaidBlocks.push(source.trim());
  return `\n\n<div class="mermaid-placeholder">${token}</div>\n\n`;
});

marked.setOptions({ gfm: true, breaks: false });
let body = await marked.parse(withoutMermaid);
for (let index = 0; index < mermaidBlocks.length; index += 1) {
  const token = `MERMAID_BLOCK_${String(index).padStart(3, "0")}`;
  const normalizedSource = mermaidBlocks[index]
    .split(/\r?\n/)
    .map((line) => {
      if (!line.trim()) return "";
      const safeIdentifiers = line
        .replace(/classDef\s+graph\b/, "classDef graphStyle")
        .replace(/^(\s*class\s+[^\s]+)\s+graph\s*$/, "$1 graphStyle");
      return `${safeIdentifiers.replace(/;\s*$/, "")};`;
    })
    .join("\n");
  const safeSource = normalizedSource
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
  body = body.replace(
    `<div class="mermaid-placeholder">${token}</div>`,
    `<div class="diagram-frame"><pre class="mermaid">${safeSource}</pre></div>`,
  );
}

const contents = markdown
  .split(/\r?\n/)
  .filter((line) => /^# (Slide |Cross-capability|Honest POC|Questions to prepare|Recommended closing)/.test(line))
  .map((line) => line.replace(/^# /, ""));

const toc = `
  <section class="contents-page">
    <p class="eyebrow">REFERENCE EDITION</p>
    <h1>Contents</h1>
    <ol>
      ${contents.map((item) => `<li>${item}</li>`).join("\n")}
    </ol>
  </section>
`;

const mermaidScript = await fs.readFile(MERMAID_PATH, "utf8");
const baseHref = pathToFileURL(`${DOC_DIR}${path.sep}`).href;
const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <base href="${baseHref}" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Telco Digital — Technical Presentation Notes v1</title>
  <style>
    :root {
      --navy: #071426;
      --navy-2: #10243a;
      --cyan: #0891b2;
      --violet: #7c3aed;
      --amber: #d97706;
      --green: #059669;
      --coral: #dc5a5a;
      --ink: #172033;
      --muted: #5d687a;
      --line: #d9e1eb;
      --paper: #ffffff;
      --soft: #f4f7fb;
    }

    @page {
      size: A4;
      margin: 17mm 14mm 18mm;
    }

    * { box-sizing: border-box; }

    html { font-family: "Aptos", "Segoe UI", Arial, sans-serif; color: var(--ink); }
    body { margin: 0; font-size: 10.4pt; line-height: 1.48; background: var(--paper); }

    h1, h2, h3, h4 { color: var(--navy); line-height: 1.16; page-break-after: avoid; }
    h1 { font-size: 24pt; margin: 0 0 8mm; border-bottom: 2.5pt solid var(--cyan); padding-bottom: 3.2mm; }
    h2 { font-size: 16pt; margin: 8mm 0 3mm; }
    h3 { font-size: 12.5pt; margin: 6mm 0 2mm; color: #244566; }
    h4 { font-size: 11pt; margin: 5mm 0 2mm; color: #334b67; }

    body > h1:not(:first-of-type) { break-before: page; }
    body > h1:first-of-type { margin-top: 20mm; font-size: 30pt; }
    body > h1:first-of-type + p { font-size: 13pt; color: var(--muted); }

    p { margin: 0 0 3.2mm; orphans: 3; widows: 3; }
    ul, ol { margin: 2mm 0 4mm 6mm; padding-left: 5mm; }
    li { margin: 1.2mm 0; }
    strong { color: #0d3153; }

    blockquote {
      margin: 5mm 0;
      padding: 4mm 5mm;
      border-left: 4pt solid var(--amber);
      background: #fff8e8;
      color: #3e4654;
      font-size: 11pt;
      break-inside: avoid;
    }
    blockquote p { margin: 0; }

    code {
      font-family: "Cascadia Mono", Consolas, monospace;
      font-size: 0.92em;
      background: #edf2f7;
      color: #243b53;
      padding: 0.25mm 0.9mm;
      border-radius: 1mm;
    }

    pre {
      margin: 4mm 0;
      padding: 4mm;
      border-radius: 2mm;
      background: var(--navy);
      color: #e7f4ff;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      break-inside: avoid;
    }
    pre code { background: transparent; color: inherit; padding: 0; }

    table {
      width: 100%;
      border-collapse: collapse;
      margin: 4mm 0 6mm;
      font-size: 9.2pt;
      break-inside: avoid;
    }
    thead { display: table-header-group; }
    th {
      background: var(--navy-2);
      color: #ffffff;
      text-align: left;
      padding: 2.5mm 2.8mm;
      border: 0.5pt solid #29415d;
    }
    td { padding: 2.2mm 2.8mm; border: 0.5pt solid var(--line); vertical-align: top; }
    tr:nth-child(even) td { background: var(--soft); }

    img {
      display: block;
      max-width: 100%;
      max-height: 205mm;
      width: auto;
      height: auto;
      margin: 4mm auto 6mm;
      border: 0.6pt solid #cdd7e4;
      border-radius: 2mm;
      box-shadow: 0 1.5mm 4mm rgba(7, 20, 38, 0.12);
      object-fit: contain;
    }
    p:has(> img) { break-inside: avoid; margin: 0; }
    h3 + p:has(> img), h2 + p:has(> img) { break-before: avoid; }

    a { color: #075d78; text-decoration: none; overflow-wrap: anywhere; }

    .diagram-frame {
      margin: 4mm 0 6mm;
      padding: 4mm;
      border: 0.7pt solid #c9d6e5;
      border-radius: 2.5mm;
      background: #f7fbff;
      break-inside: avoid;
    }
    .diagram-frame pre.mermaid {
      display: flex;
      justify-content: center;
      align-items: center;
      width: 100%;
      margin: 0;
      padding: 0;
      background: transparent;
      color: inherit;
      white-space: pre;
      overflow: visible;
    }
    .mermaid svg { max-width: 100% !important; max-height: 145mm !important; height: auto !important; }

    .contents-page {
      break-before: page;
      break-after: page;
      min-height: 245mm;
      padding-top: 10mm;
    }
    .contents-page .eyebrow {
      font-size: 9pt;
      letter-spacing: 0.12em;
      color: var(--cyan);
      font-weight: 700;
      margin-bottom: 2mm;
    }
    .contents-page h1 { font-size: 27pt; }
    .contents-page ol { columns: 2; column-gap: 14mm; padding-left: 7mm; }
    .contents-page li { break-inside: avoid; margin: 0 0 3mm; font-size: 10pt; }

    .synthetic-note {
      background: #fff4db;
      border: 0.7pt solid #edc66a;
      padding: 3mm 4mm;
      border-radius: 2mm;
      break-inside: avoid;
    }

    hr { border: 0; border-top: 0.7pt solid var(--line); margin: 8mm 0; }
  </style>
</head>
<body>
${toc}
${body}
<script>${mermaidScript}</script>
<script>
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "loose",
    theme: "base",
    flowchart: { htmlLabels: true, curve: "basis", useMaxWidth: true },
    themeVariables: {
      fontFamily: "Aptos, Segoe UI, Arial, sans-serif",
      fontSize: "14px",
      primaryColor: "#12365a",
      primaryTextColor: "#ffffff",
      primaryBorderColor: "#22d3ee",
      lineColor: "#65819f",
      tertiaryColor: "#f4f7fb",
      background: "#f7fbff"
    }
  });
  mermaid.run({ querySelector: ".mermaid" }).then(() => {
    document.documentElement.dataset.mermaidReady = "true";
  }).catch((error) => {
    document.documentElement.dataset.mermaidError =
      error && error.message
        ? String(error.message)
        : error && error.str
          ? String(error.str)
          : JSON.stringify(error);
  });
</script>
</body>
</html>`;

await fs.writeFile(HTML_PATH, html, "utf8");

const browser = await chromium.launch({
  headless: true,
  executablePath: CHROME,
  args: ["--allow-file-access-from-files", "--disable-web-security", "--font-render-hinting=none"],
});

try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.goto(pathToFileURL(HTML_PATH).href, { waitUntil: "load", timeout: 120000 });
  await page.waitForFunction(
    () =>
      document.documentElement.dataset.mermaidReady === "true" ||
      Boolean(document.documentElement.dataset.mermaidError),
    null,
    { timeout: 60000 },
  );
  const mermaidStatus = await page.evaluate(() => ({
    ready: document.documentElement.dataset.mermaidReady,
    error: document.documentElement.dataset.mermaidError,
  }));
  if (mermaidStatus.error) {
    throw new Error(`Mermaid rendering failed: ${mermaidStatus.error}`);
  }
  await page.waitForFunction(() => Array.from(document.images).every((img) => img.complete && img.naturalWidth > 0), null, {
    timeout: 120000,
  });
  await page.emulateMedia({ media: "print" });

  const stats = await page.evaluate(() => ({
    diagrams: document.querySelectorAll(".mermaid svg").length,
    images: document.images.length,
    brokenImages: Array.from(document.images)
      .filter((img) => !img.complete || img.naturalWidth === 0)
      .map((img) => img.getAttribute("src")),
    tables: document.querySelectorAll("table").length,
    headings: document.querySelectorAll("h1,h2,h3,h4").length,
  }));

  if (stats.diagrams !== mermaidBlocks.length) {
    throw new Error(`Expected ${mermaidBlocks.length} rendered diagrams, found ${stats.diagrams}`);
  }
  if (stats.brokenImages.length) {
    throw new Error(`Broken images: ${stats.brokenImages.join(", ")}`);
  }
  if (consoleErrors.length) {
    await fs.writeFile(path.join(SCRATCH, "browser-errors.txt"), consoleErrors.join("\n"), "utf8");
  }

  await page.pdf({
    path: PDF_PATH,
    format: "A4",
    printBackground: true,
    preferCSSPageSize: true,
    displayHeaderFooter: true,
    headerTemplate: `<div style="font-family:Segoe UI,Arial,sans-serif;font-size:8px;color:#607089;width:100%;padding:0 14mm;text-align:right;">Telco Digital · Technical Presentation Notes</div>`,
    footerTemplate: `<div style="font-family:Segoe UI,Arial,sans-serif;font-size:8px;color:#607089;width:100%;padding:0 14mm;display:flex;justify-content:space-between;"><span>Reference PDF</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`,
    margin: { top: "17mm", right: "14mm", bottom: "18mm", left: "14mm" },
  });

  await fs.writeFile(path.join(SCRATCH, "render-stats.json"), JSON.stringify(stats, null, 2), "utf8");
  console.log(JSON.stringify({ pdf: PDF_PATH, html: HTML_PATH, ...stats }, null, 2));
} finally {
  await browser.close();
}
