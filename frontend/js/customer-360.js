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

function formatEpisodeSummary(episode) {
  const destination = episode?.destination_name || episode?.destination || "Unknown destination";
  const duration = episode?.duration_known ? `${episode.duration_days} days` : "duration unknown";
  const usageGb = episode?.metrics?.usage_gb;
  const usage = usageGb == null ? "usage unknown" : `${usageGb} GB`;
  const plan = episode?.actions?.plan_selected || "no roam plan";
  return `${destination}: ${duration}, ${usage}, ${plan}.`;
}

function eventMemoryPanel(data) {
  const top = (data.matches || [])[0];
  return el("div", { className: "card" }, [
    el("header", { className: "page-header" }, [
      el("h3", { text: "Event memory" }),
      badge("Derived", "derived"),
    ]),
    top
      ? el("p", { text: formatEpisodeSummary(top.episode) })
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

function churnPanel(data) {
  const drivers = data.drivers || [];
  const percent = Math.round(Number(data.probability) * 100);
  return el("div", { className: "card" }, [
    el("header", { className: "page-header" }, [
      el("h3", { text: "Churn prediction" }),
      badge("Prediction", "prediction"),
    ]),
    el("p", {
      text: `${data.risk_band} risk • ${percent}% probability (${data.model_version})`,
    }),
    drivers.length
      ? el(
          "ul",
          { className: "timeline" },
          drivers.map((item) =>
            el("li", {}, [
              el("div", {}, [
                el("div", { text: item.feature.replaceAll("_", " ") }),
                el("small", {
                  text: `value ${item.value} • ${item.direction.replaceAll("_", " ")} (${item.contribution})`,
                }),
              ]),
              badge("Prediction", "prediction"),
            ]),
          ),
        )
      : el("p", { text: "No drivers were returned for this score." }),
    el("p", { className: "meta", text: `${data.prediction_set_version} • as_of ${formatDate(data.as_of)}` }),
  ]);
}

function fraudPanel(data) {
  const fired = (data.rules || []).filter((item) => item.fired);
  const percent = Math.round(Number(data.combined_risk) * 100);
  const transaction = Math.round(Number(data.transaction_risk) * 100);
  const graph = data.graph_available ? Math.round(Number(data.graph_risk) * 100) : null;
  return el("div", { className: "card" }, [
    el("header", { className: "page-header" }, [
      el("h3", { text: "Graph fraud" }),
      badge("Prediction", "prediction"),
    ]),
    el("p", {
      text: `${data.risk_band} combined • ${percent}% (${data.scorer_version})`,
    }),
    el("p", {
      className: "meta",
      text: graph == null
        ? `Transaction-only ${transaction}% • graph unavailable`
        : `Transaction-only ${transaction}% • graph ${graph}%`,
    }),
    fired.length
      ? el(
          "ul",
          { className: "timeline" },
          fired.map((item) =>
            el("li", {}, [
              el("div", {}, [
                el("div", { text: item.code.replaceAll("_", " ") }),
                el("small", { text: `${item.severity} • boost ${item.boost}` }),
              ]),
              badge("Prediction", "prediction"),
            ]),
          ),
        )
      : el("p", { text: "No fraud rule fired at this as_of." }),
    el("p", { className: "meta", text: `${data.prediction_set_version} • as_of ${formatDate(data.as_of)}` }),
  ]);
}

function recommendationPanel(data, customerRef) {
  const primary = data.primary;
  return el("div", { className: "card" }, [
    el("header", { className: "page-header" }, [
      el("h3", { text: "Recommendation" }),
      badge("Recommend", "recommend"),
    ]),
    el("p", {
      text: primary
        ? `${data.mode.replaceAll("_", " ")} • ${primary.plan_code} for ${primary.scenario_label}`
        : `${(data.mode || "NO_RECOMMENDATION").replaceAll("_", " ")} • no catalogue offer`,
    }),
    el("p", { className: "meta", text: data.recommendation_set_version }),
    el("a", {
      href: `#/journey?ref=${encodeURIComponent(customerRef || data.customer_ref || "U001")}`,
      text: "Open ranked offers on Journey",
    }),
  ]);
}

function plannedRail(
  eventMemory,
  eventMemoryError,
  behaviour,
  behaviourError,
  churn,
  churnError,
  recommendation,
  recommendationError,
  fraud,
  fraudError,
  customerRef,
) {
  const items = [
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
    churnError
      ? el("div", { className: "card" }, [
          el("header", { className: "page-header" }, [
            el("h3", { text: "Churn prediction" }),
            badge("Unavailable", "unknown"),
          ]),
          el("p", { text: "The trained churn model could not be scored. Recorded facts remain live." }),
        ])
      : churn
        ? churnPanel(churn)
        : el("div", { className: "card" }, [
            el("header", { className: "page-header" }, [
              el("h3", { text: "Churn prediction" }),
              badge("Prediction", "prediction"),
            ]),
            el("p", { text: "A trained score appears when feature evidence is available." }),
          ]),
    recommendationError
      ? el("div", { className: "card" }, [
          el("header", { className: "page-header" }, [
            el("h3", { text: "Recommendation" }),
            badge("Unavailable", "unknown"),
          ]),
          el("p", { text: "Catalogue ranking could not be loaded. Recorded facts remain live." }),
        ])
      : recommendation
        ? recommendationPanel(recommendation, customerRef)
        : el("div", { className: "card" }, [
            el("header", { className: "page-header" }, [
              el("h3", { text: "Recommendation" }),
              badge("Recommend", "recommend"),
            ]),
            el("p", { text: "Ranked catalogue offers appear when a travel destination is known." }),
          ]),
    fraudError
      ? el("div", { className: "card" }, [
          el("header", { className: "page-header" }, [
            el("h3", { text: "Graph fraud" }),
            badge("Unavailable", "unknown"),
          ]),
          el("p", { text: "Graph fraud scoring could not be loaded. Recorded facts remain live." }),
        ])
      : fraud
        ? fraudPanel(fraud)
        : el("div", { className: "card" }, [
            el("header", { className: "page-header" }, [
              el("h3", { text: "Graph fraud" }),
              badge("Prediction", "prediction"),
            ]),
            el("p", { text: "Transaction-only and graph risk appear when money or projection evidence is available." }),
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
          text: "Recorded facts plus derived features, episodes, behaviour traits, a trained churn score, catalogue recommendations and graph fraud risk. The decision engine stays POC planned.",
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
  const recDestination = selected === "U001" ? "SG" : undefined;
  const [factsOutcome, featuresOutcome, memoryOutcome, behaviourOutcome, churnOutcome, recsOutcome, fraudOutcome] =
    await Promise.allSettled([
    api.customer360(selected, asOf || undefined, { signal }),
    api.customerFeatures(selected, asOf || undefined, { signal }),
    api.eventMemory(selected, asOf || undefined, recDestination, { signal }),
    api.customerBehaviour(selected, asOf || undefined, { signal }),
    api.customerChurn(selected, asOf || undefined, { signal }),
    api.customerRecommendations(selected, asOf || undefined, recDestination, { signal }),
    api.customerFraud(selected, asOf || undefined, { signal }),
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
  const churn = churnOutcome.status === "fulfilled" ? churnOutcome.value : null;
  const churnError =
    churnOutcome.status === "rejected" && !isAbortError(churnOutcome.reason)
      ? churnOutcome.reason
      : null;
  const recommendation = recsOutcome.status === "fulfilled" ? recsOutcome.value : null;
  const recommendationError =
    recsOutcome.status === "rejected" && !isAbortError(recsOutcome.reason)
      ? recsOutcome.reason
      : null;
  const fraud = fraudOutcome.status === "fulfilled" ? fraudOutcome.value : null;
  const fraudError =
    fraudOutcome.status === "rejected" && !isAbortError(fraudOutcome.reason)
      ? fraudOutcome.reason
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
      churn,
      churnError,
      recommendation,
      recommendationError,
      fraud,
      fraudError,
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
  churn,
  churnError,
  recommendation,
  recommendationError,
  fraud,
  fraudError,
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
      plannedRail(
        eventMemory,
        eventMemoryError,
        behaviour,
        behaviourError,
        churn,
        churnError,
        recommendation,
        recommendationError,
        fraud,
        fraudError,
        data.customer_ref,
      ),
    ]),
  ]);
}

function forecastPanel(data) {
  const hero = (data.products || []).find((item) => item.product_code === data.hero_product) || (data.products || [])[0];
  return el("div", { className: "card" }, [
    el("header", { className: "page-header" }, [
      el("h3", { text: "Demand forecast" }),
      badge("Forecast", "forecast"),
    ]),
    hero
      ? el("div", {}, [
          el("p", {
            text: `${hero.product_name}: ${hero.on_hand} on hand, ${hero.forecast_7d} forecast in ${data.horizon_days} days.`,
          }),
          el("p", {
            text: `${hero.risk_band} cover ${hero.cover_days} days • ${hero.action}${hero.warning ? ` • ${hero.warning}` : ""}`,
          }),
        ])
      : el("p", { text: "No product forecast at this as_of." }),
    el("p", { className: "meta", text: `${data.forecast_set_version} • ${data.model_type}` }),
  ]);
}

async function renderRetail(root, asOf, signal) {
  try {
    const [factsOutcome, forecastOutcome] = await Promise.allSettled([
      api.retailer("RET-001", asOf || undefined, { signal }),
      api.retailerForecast("RET-001", asOf || undefined, { signal }),
    ]);
    if (stale(signal)) return;
    if (factsOutcome.status !== "fulfilled") {
      throw factsOutcome.reason;
    }
    const data = factsOutcome.value;
    const forecast = forecastOutcome.status === "fulfilled" ? forecastOutcome.value : null;
    const forecastError =
      forecastOutcome.status === "rejected" && !isAbortError(forecastOutcome.reason)
        ? forecastOutcome.reason
        : null;
    root.replaceChildren(
      el("div", {}, [
        el("section", { className: "card fact-card" }, [
          el("header", {}, [el("h2", { text: data.name }), badge("Recorded fact", "fact")]),
          el("p", { text: `${data.retailer_ref} • ${data.region} • ${data.status}` }),
          el("p", { className: "meta", text: provenanceLine(data) }),
        ]),
        factList("Sales", data.sales, "No sales at this as_of."),
        factList("Inventory events", data.inventory, "No inventory events at this as_of."),
        forecastError
          ? el("div", { className: "card" }, [
              el("header", {}, [el("h3", { text: "Demand forecast" }), badge("Unavailable", "unknown")]),
              el("p", { text: "The trained forecast model could not be scored. Recorded facts remain live." }),
            ])
          : forecast
            ? forecastPanel(forecast)
            : el("div", { className: "card" }, [
                el("header", {}, [el("h3", { text: "Demand forecast" }), badge("Unavailable", "unknown")]),
                el("p", { text: "No forecast is available at this as_of." }),
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
