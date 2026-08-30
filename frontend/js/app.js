import { api } from "./api.js";
import { renderBarChart, renderDoughnut } from "./charts.js";
import { renderCustomer360, errorBox } from "./customer-360.js";
import { badge, el, formatDate, formatNumber, provenanceLine, statusBox } from "./dom.js";
import { renderStatus } from "./status.js";
import { renderWalkthroughs } from "./walkthroughs.js";
import { renderGraph } from "./graph.js";

const NAV = [
  ["overview", "Overview", "live"],
  ["customer-360", "Customer 360", "live"],
  ["journey", "Journey and Event Memory", "planned"],
  ["campaigns", "Campaigns and Loyalty", "live"],
  ["money", "Money and Fraud", "live"],
  ["retail", "Retail and SFA", "live"],
  ["graph", "Graph Explorer", "live"],
  ["models", "Models and Decisions", "planned"],
  ["copilot", "Copilot", "planned"],
  ["status", "POC Status", "live"],
];

const PLANNED = {
  journey: {
    title: "Journey and Event Memory",
    body: "Event memory matches similar historical episodes. This capability is not started. No fabricated journey metrics are shown.",
  },
  models: {
    title: "Models and Decisions",
    body: "Churn, recommendations, twins and the decision engine are not started. This page does not display model scores.",
  },
  copilot: {
    title: "Copilot",
    body: "A grounded Copilot is not connected. No LLM answers are generated in this showcase.",
  },
};

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
    el("div", { className: "banner", role: "note" }, [
      el("strong", { text: "Synthetic data" }),
      el("span", {
        text: "All customer records are synthetic POC fixtures. Capabilities 00–02 are a read-only POC showcase — not production, not FastAPI complete, and not the simulator.",
      }),
    ]),
    el("div", { className: "app-shell" }, [
      el("header", { className: "topbar" }, [
        el("div", { className: "brand" }, [
          el("strong", { text: "omobio INTELLIGENCE" }),
          el("span", { text: "NG Application Shell • Omobio Intelligence POC" }),
        ]),
        el("div", { className: "topbar-tools" }, [
          el("span", { text: "A. Demo" }),
          el("span", { className: "avatar", text: "AD", "aria-hidden": "true" }),
        ]),
      ]),
      el("aside", { className: "sidebar" }, [
        el("h2", { text: "Intelligence" }),
        nav,
        el("div", { className: "sidebar-foot" }, [
          el("div", { text: "POC environment: Live evidence = capability 00." }),
          el("div", { text: "Planned capability = not implemented." }),
        ]),
      ]),
      content,
      el("footer", { className: "footer", text: "© 2026 Omobio. Shared-intelligence POC. Synthetic data only." }),
    ]),
  );
  return { nav, content };
}

function setCurrent(nav, id) {
  for (const link of nav.querySelectorAll("a")) {
    if (link.dataset.route === id) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
}

async function renderOverview(root) {
  root.replaceChildren(
    el("div", { className: "page-header" }, [
      el("div", {}, [
        el("h1", { text: "Intelligence overview" }),
        el("p", { text: "Live facts, Neo4j projection evidence and point-in-time features. Later capabilities are labeled as planned." }),
      ]),
      el("a", { href: "#/status", text: "POC status" }),
    ]),
    statusBox("loading", "Loading live database evidence…"),
  );
  try {
    const [overview, evidence, manifest] = await Promise.all([api.overview(), api.evidence(), api.status()]);
    if (overview.source !== "live_database" || evidence.source !== "live_database") {
      root.append(
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
          manifest.capabilities.slice(0, 8).map((capability) => {
            const complete = capability.status === "POC complete";
            return el("div", { className: `step ${complete ? "complete" : "planned"}` }, [
              el("div", { className: "dot", text: capability.number }),
              el("div", { text: capability.name }),
              badge(capability.status, complete ? "live" : "planned"),
            ]);
          }),
          ),
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

function renderPlanned(root, id) {
  const copy = PLANNED[id];
  root.replaceChildren(
    el("div", { className: "page-header" }, [
      el("div", {}, [
        el("h1", { text: copy.title }),
        el("p", { text: copy.body }),
      ]),
      badge("POC planned", "planned"),
    ]),
    el("section", { className: "card" }, [
      el("p", { text: "This page remains visible so the roadmap is honest. It does not display fabricated metrics or simulated model output." }),
      el("a", { href: "#/status", text: "See capability status" }),
    ]),
  );
}

export function start() {
  const { nav, content } = renderShell(document.body);
  async function show() {
    const id = route();
    setCurrent(nav, id);
    content.replaceChildren();
    if (id === "overview") await renderOverview(content);
    else if (id === "customer-360") await renderCustomer360(content);
    else if (id === "campaigns") await renderCustomer360(content, { lens: "campaigns" });
    else if (id === "money") await renderCustomer360(content, { lens: "money" });
    else if (id === "retail") await renderCustomer360(content, { lens: "retail" });
    else if (id === "walkthroughs") await renderWalkthroughs(content);
    else if (id === "graph") await renderGraph(content);
    else if (id === "status") await renderStatus(content);
    else if (PLANNED[id]) renderPlanned(content, id);
    else content.replaceChildren(statusBox("error", "Unknown page", "Use the Intelligence navigation."));
    content.focus();
  }
  window.addEventListener("hashchange", () => {
    show();
  });
  if (!window.location.hash) window.location.hash = "#/overview";
  else show();
}

start();
