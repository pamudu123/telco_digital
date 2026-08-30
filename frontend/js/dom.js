export function text(value) {
  return value == null ? "" : String(value);
}

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, val] of Object.entries(attrs)) {
    if (val == null || val === false) continue;
    if (key === "className") node.className = val;
    else if (key === "dataset") Object.assign(node.dataset, val);
    else if (key.startsWith("on") && typeof val === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), val);
    } else if (key === "text") node.textContent = text(val);
    else node.setAttribute(key, val === true ? "" : String(val));
  }
  for (const child of [].concat(children)) {
    if (child == null || child === false) continue;
    node.append(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

export function badge(label, kind) {
  return el("span", { className: `badge badge-${kind}`, text: label });
}

export function statusBox(kind, title, detail) {
  return el("div", { className: `status ${kind}`, role: kind === "error" ? "alert" : "status" }, [
    el("strong", { text: title }),
    detail ? el("p", { text: detail }) : null,
  ]);
}

export function formatNumber(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "Unavailable";
  return num.toLocaleString("en-GB");
}

export function formatDate(value) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  return date.toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
}

export function provenanceLine(item) {
  const source = item?.source || item?.provenance?.source || "unknown";
  const asOf = item?.as_of || item?.provenance?.as_of;
  const table = item?.provenance?.table;
  const parts = [`Source: ${source}`];
  if (asOf) parts.push(`as_of ${formatDate(asOf)}`);
  if (table) parts.push(table);
  return parts.join(" • ");
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}
