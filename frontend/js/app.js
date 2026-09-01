import { api, isAbortError } from "./api.js";
import { renderBarChart, renderDoughnut } from "./charts.js";
import { renderCopilot } from "./copilot.js";
import { renderCustomer360, errorBox } from "./customer-360.js";
import { badge, el, formatDate, formatNumber, provenanceLine, statusBox } from "./dom.js";
import { renderGraph } from "./graph.js";
import { renderJourney } from "./journey.js";
import { renderModels } from "./models.js";
import { renderStatus } from "./status.js";
import { renderWalkthroughs } from "./walkthroughs.js";

const NAV = [
  ["overview", "Overview", "live"],
  ["customer-360", "Customer 360", "live"],
  ["journey", "Journey and Event Memory", "live"],
  ["campaigns", "Campaigns and Loyalty", "live"],
  ["money", "Money and Fraud", "live"],
  ["retail", "Retail and SFA", "live"],
  ["graph", "Graph Explorer", "live"],
  ["models", "Models and Decisions", "live"],
  ["copilot", "Copilot", "live"],
  ["status", "POC Status", "live"],
];

function route() {
  const hash = window.location.hash.replace(/^#\/?/, "") || "overview";
  const [path] = hash.split("?");
  return path || "overview";
}

function renderShell(root) {
  const nav = el(
    "nav",
    { className: "nav", "aria-label": "Intelligence" },
    NAV.map(([id, label, kind]) =>
      el("a", { href: `#/${id}`, dataset: { route: id } }, [
        label,
        badge(kind === "live" ? "Live evidence" : "POC planned", kind === "live" ? "live" : "planned"),
      ]),
    ),
  );
  const content = el("main", { id: "main", className: "content", tabindex: "-1" });
  root.replaceChildren(
    el("a", { className: "skip-link", href: "#main", text: "Skip to content" }),
    el("div", { className: "app-shell" }, [
      el("header", { className: "topbar" }, [
        el("div", { className: "brand" }, [
          el("strong", { text: "COMPANY INTELLIGENCE" }),
          el("span", { text: "NG Application Shell • Company Intelligence POC" }),
        ]),
        el("div", { className: "topbar-tools" }, [
          el("span", { text: "A. Demo" }),
          el("span", { className: "avatar", text: "AD", "aria-hidden": "true" }),
        ]),
      ]),
      el("aside", { className: "sidebar" }, [
        el("h2", { text: "Intelligence" }),
        nav,
      ]),
      content,
    ]),
    el("footer", { className: "footer", text: "© 2026 Company. Shared-intelligence POC. Synthetic data only." }),
  );
  return { nav, content };
}

function setCurrent(nav, id) {
  for (const link of nav.querySelectorAll("a")) {
    if (link.dataset.route === id) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
}

async function renderOverview(root, { signal } = {}) {
  root.replaceChildren(
    el("div", { className: "page-header" }, [
      el("div", {}, [
        el("h1", { text: "Intelligence overview" }),
        el("p", { text: "Live facts, Neo4j projection, point-in-time features, travel event memory, catalogue recommendations, graph fraud scores, SFA forecasts, computed twins, next-best actions, Copilot and the FastAPI service boundary. The simulator stays planned." }),
      ]),
      el("a", { href: "#/status", text: "POC status" }),
    ]),
    statusBox("loading", "Loading live database evidence…"),
  );
  try {
    const [overview, evidence, manifest] = await Promise.all([
      api.overview(undefined, { signal }),
      api.evidence(undefined, { signal }),
      api.status({ signal }),
    ]);
    if (signal?.aborted) return;
    if (overview.source !== "live_database" || evidence.source !== "live_database") {
      root.replaceChildren(
        statusBox("error", "Unexpected evidence source", "Live pages do not mix notebook artifacts into metric cards."),
      );
      return;
    }
    const cards = [
      ["Customers", overview.total_customers, "Includes U001–U005 seed customers"],
      ["Background customers", overview.background_customers, "Generated BG% customers"],
      ["Golden personas", overview.golden_personas, "U001–U010 present in the database"],
      ["Generated rows", overview.generated_rows, "poc-v1 owned rows, not total table SUM"],
      ["Activity events", overview.activity_events, "poc-v1 activity events"],
      ["Outbox events", overview.outbox_events, `Parity ${overview.event_outbox_parity ? "yes" : "no"}`],
    ];
    const tableCanvas = el("canvas", { "aria-hidden": "true" });
    const personaCanvas = el("canvas", { "aria-hidden": "true" });
    const monthlyCanvas = el("canvas", { "aria-hidden": "true" });
    root.replaceChildren(
      el("div", { className: "page-header" }, [
        el("div", {}, [
          el("h1", { text: "Intelligence overview" }),
          el("p", { text: provenanceLine(overview) }),
        ]),
      ]),
      el(
        "div",
        { className: "grid grid-3" },
        cards.map(([label, value, hint]) =>
          el("article", { className: "card metric" }, [
            el("div", { text: label }),
            el("div", { className: "value", text: formatNumber(value) }),
            el("div", { className: "meta", text: `${hint} • ${formatDate(overview.as_of)} • ${overview.source}` }),
          ]),
        ),
      ),
      el("section", { className: "card" }, [
        el("h2", { text: "Capability stepper" }),
        el(
          "div",
          { className: "stepper" },
          manifest.capabilities.map((capability) => {
            const complete = capability.status === "POC complete";
            return el("div", { className: `step ${complete ? "complete" : "planned"}` }, [
              el("div", { className: "dot", text: capability.number }),
              el("div", { text: capability.name }),
              badge(capability.status, complete ? "live" : "planned"),
            ]);
          }),
        ),
      ]),
      el("section", { className: "card" }, [
        el("h2", { text: "Domain coverage" }),
        el("table", { className: "table" }, [
          el("thead", {}, [
            el("tr", {}, [
              el("th", { text: "Domain" }),
              el("th", { text: "Demonstrated data" }),
              el("th", { text: "Existing application" }),
              el("th", { text: "Status" }),
            ]),
          ]),
          el(
            "tbody",
            {},
            overview.domain_coverage.map((row) =>
              el("tr", {}, [
                el("td", { text: row.domain }),
                el("td", { text: row.demonstrated_data }),
                el("td", { text: row.existing_application }),
                el("td", {}, [badge(row.live ? "Live facts" : "POC planned", row.live ? "live" : "planned")]),
              ]),
            ),
          ),
        ]),
      ]),
      el("div", { className: "grid grid-2" }, [
        chartCard("Generated rows by table", tableCanvas, evidence.generated_rows_by_table),
        chartCard("Persona distribution", personaCanvas, evidence.persona_distribution, true),
      ]),
      chartCard("Twelve-month activity events", monthlyCanvas, evidence.monthly_activity),
      el("p", {}, [
        el("a", { href: "#/walkthroughs", text: "Open golden-scenario walkthroughs" }),
      ]),
    );
    renderBarChart(
      tableCanvas,
      evidence.generated_rows_by_table.map((p) => p.label),
      evidence.generated_rows_by_table.map((p) => p.value),
      "Generated rows",
    );
    renderDoughnut(
      personaCanvas,
      evidence.persona_distribution.map((p) => p.label),
      evidence.persona_distribution.map((p) => p.value),
    );
    renderBarChart(
      monthlyCanvas,
      evidence.monthly_activity.map((p) => p.label),
      evidence.monthly_activity.map((p) => p.value),
      "Activity events",
    );
  } catch (error) {
    if (signal?.aborted || isAbortError(error)) return;
    root.replaceChildren(errorBox(error, "Could not load overview evidence."));
  }
}

function chartCard(title, canvas, points, doughnut = false) {
  const table = el("table", { className: "table" }, [
    el("caption", { className: "sr-only", text: `${title} data table` }),
    el("thead", {}, [el("tr", {}, [el("th", { text: "Label" }), el("th", { text: "Value" })])]),
    el(
      "tbody",
      {},
      (points || []).map((point) =>
        el("tr", {}, [el("td", { text: point.label }), el("td", { text: formatNumber(point.value) })]),
      ),
    ),
  ]);
  return el("section", { className: "card" }, [
    el("h2", { text: title }),
    el("div", { className: "chart-wrap" }, [canvas]),
    table,
  ]);
}

export function start() {
  const { nav, content } = renderShell(document.body);
  let active = new AbortController();
  let currentId = null;
  const views = new Map();

  function viewFor(id) {
    if (!views.has(id)) {
      views.set(id, {
        root: el("div", { className: "page-view", dataset: { route: id } }),
        status: "new",
        run: 0,
      });
    }
    return views.get(id);
  }

  async function renderPage(id, view, signal) {
    const run = ++view.run;
    view.status = "loading";
    try {
      if (id === "overview") await renderOverview(view.root, { signal });
      else if (id === "customer-360") await renderCustomer360(view.root, { signal });
      else if (id === "campaigns") await renderCustomer360(view.root, { lens: "campaigns", signal });
      else if (id === "money") await renderCustomer360(view.root, { lens: "money", signal });
      else if (id === "retail") await renderCustomer360(view.root, { lens: "retail", signal });
      else if (id === "walkthroughs") await renderWalkthroughs(view.root, { signal });
      else if (id === "journey") await renderJourney(view.root, { signal });
      else if (id === "graph") await renderGraph(view.root, { signal });
      else if (id === "models") await renderModels(view.root, { signal });
      else if (id === "copilot") await renderCopilot(view.root, { signal });
      else if (id === "status") await renderStatus(view.root, { signal });
      else view.root.replaceChildren(statusBox("error", "Unknown page", "Use the Intelligence navigation."));
      if (view.run === run) view.status = signal.aborted ? "aborted" : "ready";
    } catch (error) {
      if (view.run !== run) return;
      if (signal.aborted || isAbortError(error)) {
        view.status = "aborted";
        return;
      }
      view.status = "ready";
      view.root.replaceChildren(errorBox(error, "Could not load this page."));
    }
  }

  async function show() {
    active.abort();
    const controller = new AbortController();
    active = controller;
    const { signal } = controller;
    const id = route();
    const isSameScreen = id === currentId;
    const view = viewFor(id);
    currentId = id;
    setCurrent(nav, id);
    content.replaceChildren(view.root);

    // A hash change within the active screen is a new search. Moving between
    // screens restores the cached DOM and its loaded information unchanged.
    if (isSameScreen || view.status === "new" || view.status === "aborted") {
      await renderPage(id, view, signal);
    }
    if (signal.aborted) return;
    content.focus();
  }
  window.addEventListener("hashchange", () => {
    show();
  });
  if (!window.location.hash) window.location.hash = "#/overview";
  else show();
}

start();
