import { api, ApiError, isAbortError } from "./api.js";
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

function eventMemoryPanel(data) {
  const top = (data.matches || [])[0];
  return el("div", { className: "card" }, [
    el("header", { className: "page-header" }, [
      el("h3", { text: "Event memory" }),
      badge("Derived", "derived"),
    ]),
    top
      ? el("p", {
          text: `${top.episode.destination_name}: ${top.episode.duration_days} days, ${top.episode.metrics.usage_gb} GB, ${top.episode.actions.plan_selected || "no roam plan"}.`,
        })
      : el("p", { text: "No similar historical episode retrieved at this as_of." }),
    el("p", { className: "meta", text: data.episode_set_version }),
    el("a", { href: `#/journey?ref=${encodeURIComponent(data.customer_ref)}`, text: "Open Journey and Event Memory" }),
  ]);
}

function behaviourPanel(data) {
  const traits = data.traits || [];
  return el("div", { className: "card" }, [
    el("header", { className: "page-header" }, [
      el("h3", { text: "Behaviour traits" }),
      badge("Derived", "derived"),
    ]),
    traits.length
      ? el(
          "ul",
          { className: "timeline" },
          traits.map((item) =>
            el("li", {}, [
              el("div", {}, [
                el("div", { text: `${item.trait.replaceAll("_", " ")} (${item.confidence})` }),
                el("small", { text: Object.entries(item.evidence || {}).map(([key, value]) => `${key}: ${value}`).join(" • ") }),
              ]),
              badge("Derived", "derived"),
            ]),
          ),
        )
      : el("p", { text: "No behaviour trait met the evidence threshold at this as_of." }),
    el("p", { className: "meta", text: data.behaviour_set_version }),
  ]);
}

function plannedRail(eventMemory, eventMemoryError, behaviour, behaviourError) {
  const items = [
    ["Churn prediction", "No prediction generated."],
    ["Recommendation", "No recommended action generated."],
    ["Digital twin", "No derived twin in this showcase."],
  ];
  return el("aside", { className: "planned-rail", "aria-label": "Intelligence readiness" }, [
    el("h2", { text: "Intelligence readiness" }),
    eventMemoryError
      ? el("div", { className: "card" }, [
          el("header", { className: "page-header" }, [
            el("h3", { text: "Event memory" }),
            badge("Unavailable", "unknown"),
          ]),
          el("p", { text: "Episode matching could not be loaded. Recorded facts remain live." }),
        ])
      : eventMemory
        ? eventMemoryPanel(eventMemory)
        : el("div", { className: "card" }, [
            el("header", { className: "page-header" }, [
              el("h3", { text: "Event memory" }),
              badge("Derived", "derived"),
            ]),
            el("p", { text: "Open Journey to recall similar historical travel episodes." }),
            el("a", { href: "#/journey", text: "Open Journey and Event Memory" }),
          ]),
    behaviourError
      ? el("div", { className: "card" }, [
          el("header", { className: "page-header" }, [
            el("h3", { text: "Behaviour traits" }),
            badge("Unavailable", "unknown"),
          ]),
          el("p", { text: "Trait rules could not be loaded. Recorded facts remain live." }),
        ])
      : behaviour
        ? behaviourPanel(behaviour)
        : el("div", { className: "card" }, [
            el("header", { className: "page-header" }, [
              el("h3", { text: "Behaviour traits" }),
              badge("Derived", "derived"),
            ]),
            el("p", { text: "Derived traits appear when feature evidence is available." }),
          ]),
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

function stale(signal) {
  return Boolean(signal?.aborted);
}

export async function renderCustomer360(root, { lens = "all", signal } = {}) {
  root.replaceChildren(statusBox("loading", "Loading recorded facts…"));
  let personas;
  try {
    personas = await api.personas({ signal });
  } catch (error) {
    if (stale(signal) || isAbortError(error)) return;
    root.replaceChildren(errorBox(error, "Could not load personas."));
    return;
  }
  if (stale(signal)) return;

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

  if (stale(signal)) return;

  const results = el("div", { className: "page-results" });
  root.replaceChildren(
    el("div", { className: "page-header" }, [
      el("div", {}, [
        el("h1", { text: "Customer 360" }),
        el("p", {
          text: "Recorded facts plus derived features, episodes and behaviour traits. Predictions and recommendations stay POC planned.",
        }),
      ]),
    ]),
    toolbar,
    results,
  );

  if (currentLens === "lottery") {
    results.replaceChildren(
      statusBox(
        "empty",
        "Mobile Lottery is a secondary lens.",
        "Later graph and anomaly capabilities may support abuse investigation. No lottery facts are shown as live intelligence.",
      ),
      plannedRail(),
    );
    return;
  }

  if (currentLens === "retail") {
    await renderRetail(results, asOf, signal);
    return;
  }

  results.replaceChildren(statusBox("loading", "Loading recorded facts…"));
  const [factsOutcome, featuresOutcome, memoryOutcome, behaviourOutcome] = await Promise.allSettled([
    api.customer360(selected, asOf || undefined, { signal }),
    api.customerFeatures(selected, asOf || undefined, { signal }),
    api.eventMemory(selected, asOf || undefined, undefined, { signal }),
    api.customerBehaviour(selected, asOf || undefined, { signal }),
  ]);
  if (stale(signal)) return;

  if (factsOutcome.status === "rejected") {
    if (isAbortError(factsOutcome.reason)) return;
    results.replaceChildren(errorBox(factsOutcome.reason, `Could not load ${selected}.`));
    return;
  }

  const features = featuresOutcome.status === "fulfilled" ? featuresOutcome.value : null;
  const featuresError =
    featuresOutcome.status === "rejected" && !isAbortError(featuresOutcome.reason)
      ? featuresOutcome.reason
      : null;
  const eventMemory = memoryOutcome.status === "fulfilled" ? memoryOutcome.value : null;
  const eventMemoryError =
    memoryOutcome.status === "rejected" && !isAbortError(memoryOutcome.reason)
      ? memoryOutcome.reason
      : null;
  const behaviour = behaviourOutcome.status === "fulfilled" ? behaviourOutcome.value : null;
  const behaviourError =
    behaviourOutcome.status === "rejected" && !isAbortError(behaviourOutcome.reason)
      ? behaviourOutcome.reason
      : null;
  results.replaceChildren(
    renderFacts(
      factsOutcome.value,
      currentLens,
      features,
      featuresError,
      eventMemory,
      eventMemoryError,
      behaviour,
      behaviourError,
    ),
  );
}

function featureErrorPanel(error) {
  return el("section", { className: "card" }, [
    el("header", {}, [el("h2", { text: "Derived features" }), badge("Unavailable", "unknown")]),
    statusBox(
      "error",
      "Could not load derived features",
      "Recorded facts remain live. Notebook artifacts are not substituted.",
    ),
    el("p", { className: "meta", text: error instanceof Error ? error.message : "Request failed" }),
  ]);
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

function renderFacts(
  data,
  lens,
  features,
  featuresError,
  eventMemory,
  eventMemoryError,
  behaviour,
  behaviourError,
) {
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
    el("aside", {}, [
      featuresError ? featureErrorPanel(featuresError) : features ? featurePanel(features) : null,
      plannedRail(eventMemory, eventMemoryError, behaviour, behaviourError),
    ]),
  ]);
}

async function renderRetail(root, asOf, signal) {
  try {
    const data = await api.retailer("RET-001", asOf || undefined, { signal });
    if (stale(signal)) return;
    root.replaceChildren(
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
    if (stale(signal) || isAbortError(error)) return;
    root.replaceChildren(errorBox(error, "Could not load retailer RET-001."));
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
