import { api, ApiError } from "./api.js";
import { badge, el, formatDate, formatNumber, provenanceLine, statusBox, text } from "./dom.js";

const LENSES = {
  selfcare: ["usage", "recharges", "travels", "service_interactions"],
  loyalty: ["loyalty", "campaigns"],
  campaigns: ["campaigns", "loyalty"],
  money: ["wallet", "devices"],
  retail: [],
};

function factList(title, rows, emptyText) {
  const items = rows || [];
  const body = items.length
    ? el(
        "ul",
        { className: "timeline" },
        items.map((row) =>
          el("li", {}, [
            el("time", { text: formatDate(row.occurred_at) }),
            el("div", {}, [
              el("div", { text: row.summary }),
              el("small", { text: provenanceLine(row) }),
            ]),
            badge("Recorded fact", "fact"),
          ]),
        ),
      )
    : statusBox("empty", emptyText);
  return el("section", { className: "card fact-card" }, [
    el("header", {}, [el("h3", { text: title }), badge("Recorded fact", "fact")]),
    body,
  ]);
}

function plannedRail() {
  const items = [
    ["Event memory", "No episode matching in this showcase."],
    ["Churn prediction", "No prediction generated."],
    ["Recommendation", "No recommended action generated."],
    ["Digital twin", "No derived twin in this showcase."],
  ];
  return el("aside", { className: "planned-rail", "aria-label": "Planned intelligence" }, [
    el("h2", { text: "Intelligence readiness" }),
    ...items.map(([title, detail]) =>
      el("div", { className: "card" }, [
        el("header", { className: "page-header" }, [
          el("h3", { text: title }),
          badge("POC planned", "planned"),
        ]),
        el("p", { text: detail }),
      ]),
    ),
  ]);
}

export async function renderCustomer360(root, { lens = "all", walkthroughId } = {}) {
  root.append(statusBox("loading", "Loading recorded facts…"));
  let personas;
  try {
    personas = await api.personas();
  } catch (error) {
    root.replaceChildren(errorBox(error, "Could not load personas."));
    return;
  }

  const params = new URLSearchParams(window.location.hash.split("?")[1] || "");
  const selected = params.get("ref") || "U001";
  const asOf = params.get("as_of") || "";
  const currentLens = params.get("lens") || lens;

  const toolbar = el("form", { className: "toolbar" }, [
    el("label", { text: "Golden persona" }, [
      el(
        "select",
        { name: "ref", "aria-label": "Persona selector" },
        (personas.personas || []).map((item) =>
          el("option", {
            value: item.customer_ref,
            selected: item.customer_ref === selected,
            text: item.present ? item.label : `${item.label} (not in database)`,
          }),
        ),
      ),
    ]),
    el("label", { text: "As of (optional ISO-8601)" }, [
      el("input", {
        name: "as_of",
        type: "text",
        value: asOf,
        placeholder: "2026-08-31T23:59:00+00:00",
        "aria-label": "As of timestamp",
      }),
    ]),
    el("label", { text: "Application lens" }, [
      el("select", { name: "lens", "aria-label": "Application lens" }, [
        el("option", { value: "all", selected: currentLens === "all", text: "All recorded facts" }),
        el("option", { value: "selfcare", selected: currentLens === "selfcare", text: "Mobile Selfcare" }),
        el("option", { value: "loyalty", selected: currentLens === "loyalty", text: "Loyalty Management" }),
        el("option", { value: "campaigns", selected: currentLens === "campaigns", text: "adReach and Viber" }),
        el("option", { value: "money", selected: currentLens === "money", text: "Mobile Money" }),
        el("option", { value: "retail", selected: currentLens === "retail", text: "Mobile SFA" }),
        el("option", { value: "lottery", selected: currentLens === "lottery", text: "Mobile Lottery (secondary)" }),
      ]),
    ]),
    el("button", { type: "submit", text: "Load facts" }),
  ]);
  toolbar.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(toolbar);
    const next = new URLSearchParams({
      ref: String(data.get("ref") || "U001"),
      lens: String(data.get("lens") || "all"),
    });
    const nextAsOf = String(data.get("as_of") || "").trim();
    if (nextAsOf) next.set("as_of", nextAsOf);
    window.location.hash = `#/customer-360?${next.toString()}`;
  });

  root.replaceChildren(
    el("div", { className: "page-header" }, [
      el("div", {}, [
        el("h1", { text: "Customer 360" }),
        el("p", {
          text: "Recorded facts only. Derived traits, predictions and recommendations stay POC planned.",
        }),
      ]),
    ]),
    toolbar,
  );

  if (currentLens === "lottery") {
    root.append(
      statusBox(
        "empty",
        "Mobile Lottery is a secondary lens.",
        "Later graph and anomaly capabilities may support abuse investigation. No lottery facts are shown as live intelligence.",
      ),
    );
    root.append(plannedRail());
    return;
  }

  if (currentLens === "retail") {
    await renderRetail(root, asOf);
    return;
  }

  try {
    const [data, features] = await Promise.all([
      api.customer360(selected, asOf || undefined),
      api.customerFeatures(selected, asOf || undefined),
    ]);
    root.append(renderFacts(data, currentLens, features));
  } catch (error) {
    root.append(errorBox(error, `Could not load ${selected}.`));
  }
}

function featurePanel(features) {
  const groups = Object.entries(features.temporal || {});
  return el("section", { className: "card" }, [
    el("header", {}, [el("h2", { text: "Derived features" }), badge("Derived", "derived")]),
    el("p", { className: "meta", text: `${features.feature_set_version} • as_of ${formatDate(features.as_of)}` }),
    ...groups.map(([name, group]) =>
      el("div", {}, [
        el("h3", { text: `${name}${group.window_days ? ` (${group.window_days}d)` : ""}` }),
        el("dl", { className: "feature-list" }, Object.entries(group.values || {}).map(([key, value]) =>
          el("div", {}, [el("dt", { text: key.replaceAll("_", " ") }), el("dd", { text: value ?? "Unknown" })]),
        )),
      ]),
    ),
    el("h3", { text: "Graph context" }),
    features.graph.available
      ? el("dl", { className: "feature-list" }, Object.entries(features.graph.values || {}).map(([key, value]) =>
          el("div", {}, [el("dt", { text: key.replaceAll("_", " ") }), el("dd", { text: value ?? "Unknown" })]),
        ))
      : statusBox("empty", "Graph features unavailable", (features.graph.unknowns || []).join(" ")),
  ]);
}

function renderFacts(data, lens, features) {
  const sections = {
    usage: factList("Usage", data.usage, "No usage events at this as_of."),
    recharges: factList("Recharge history", data.recharges, "No recharges at this as_of."),
    travels: factList("Travel history", data.travels, "No travel records at this as_of."),
    service_interactions: factList(
      "Service interactions",
      data.service_interactions,
      "No service interactions at this as_of.",
    ),
    loyalty: factList("Loyalty ledger", data.loyalty, "No loyalty entries at this as_of."),
    campaigns: factList("Campaign response", data.campaigns, "No campaign interactions at this as_of."),
    wallet: factList("Wallet activity", data.wallet, "No wallet transactions at this as_of."),
    devices: factList("Known devices", data.devices, "No devices valid at this as_of."),
  };
  const visible = lens === "all" ? Object.values(sections) : (LENSES[lens] || []).map((key) => sections[key]);
  const unknowns = (data.unknowns || []).map((item) =>
    el("p", {}, [badge("Unknown", "unknown"), " ", text(item)]),
  );
  return el("div", { className: "two-col" }, [
    el("div", {}, [
      el("section", { className: "card fact-card" }, [
        el("header", {}, [el("h2", { text: data.customer_ref }), badge("Golden persona", "fact")]),
        el("p", { text: `${data.persona || "Unknown persona"} • ${data.account_type} • ${data.home_country}` }),
        el("p", {
          text: `Plan: ${data.current_plan_name || data.current_plan_code || "Unknown"} • Balance: ${data.balance_amount ?? "Unknown"} ${data.currency || ""}`,
        }),
        el("p", { className: "meta", text: provenanceLine(data) }),
        ...unknowns,
      ]),
      el("div", { className: "grid grid-2" }, visible),
      factList("Customer timeline", data.timeline, "No activity events at this as_of."),
    ]),
    el("aside", {}, [featurePanel(features), plannedRail()]),
  ]);
}

async function renderRetail(root, asOf) {
  try {
    const data = await api.retailer("RET-001", asOf || undefined);
    root.append(
      el("div", {}, [
        el("section", { className: "card fact-card" }, [
          el("header", {}, [el("h2", { text: data.name }), badge("Recorded fact", "fact")]),
          el("p", { text: `${data.retailer_ref} • ${data.region} • ${data.status}` }),
          el("p", { className: "meta", text: provenanceLine(data) }),
        ]),
        factList("Sales", data.sales, "No sales at this as_of."),
        factList("Inventory events", data.inventory, "No inventory events at this as_of."),
        el("div", { className: "card" }, [
          el("header", {}, [el("h3", { text: "Forecast and retailer twin" }), badge("POC planned", "planned")]),
          el("p", { text: "Demand forecasts and stockout warnings are not implemented." }),
        ]),
      ]),
    );
  } catch (error) {
    root.append(errorBox(error, "Could not load retailer RET-001."));
  }
}

export function errorBox(error, fallback) {
  if (error instanceof ApiError && error.status === 422) {
    return statusBox("error", "Invalid as_of", "Use a timezone-aware ISO-8601 timestamp.");
  }
  if (error instanceof ApiError && error.status === 404) {
    return statusBox("error", "Not found", error.message);
  }
  if (error instanceof ApiError && (error.status === 503 || error.source === "unavailable")) {
    return statusBox(
      "error",
      "PostgreSQL unavailable",
      "Live evidence is not shown. Notebook artifacts are not substituted.",
    );
  }
  return statusBox("error", fallback, error instanceof Error ? error.message : "Request failed");
}
