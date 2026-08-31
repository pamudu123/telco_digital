import { api, isAbortError } from "./api.js";
import { badge, el, formatDate, provenanceLine, statusBox } from "./dom.js";
import { errorBox } from "./customer-360.js";
import { decisionPanel } from "./decision.js";

function stale(signal) {
  return Boolean(signal?.aborted);
}

function situationCard(data) {
  const situation = data.current_situation || {};
  const unknowns = (data.unknowns || []).map((item) =>
    el("p", {}, [badge("Unknown", "unknown"), " ", item]),
  );
  return el("section", { className: "card" }, [
    el("header", {}, [el("h2", { text: "Current situation" }), badge("Derived", "derived")]),
    el("p", {
      text: situation.destination_known
        ? `${situation.destination_name || situation.destination} • source ${situation.source}`
        : "No current travel situation at this as_of.",
    }),
    el("dl", { className: "feature-list" }, [
      el("div", {}, [
        el("dt", { text: "Destination known" }),
        el("dd", { text: situation.destination_known ? "Yes" : "No" }),
      ]),
      el("div", {}, [
        el("dt", { text: "Duration known" }),
        el("dd", { text: situation.duration_known ? `${situation.duration_days} days` : "Unknown" }),
      ]),
    ]),
    el("p", { className: "meta", text: `${data.episode_set_version} • ${provenanceLine(data)}` }),
    ...unknowns,
  ]);
}

function episodeCard(match) {
  const episode = match.episode;
  return el("article", { className: "card" }, [
    el("header", { className: "page-header" }, [
      el("div", {}, [
        el("h3", { text: `${episode.destination_name} travel episode` }),
        el("p", { text: `${episode.customer_ref} • ${formatDate(episode.start_at)}` }),
      ]),
      badge(match.rank.replaceAll("_", " "), "derived"),
    ]),
    el("dl", { className: "feature-list" }, [
      el("div", {}, [el("dt", { text: "Similarity" }), el("dd", { text: String(match.similarity) })]),
      el("div", {}, [
        el("dt", { text: "Duration" }),
        el("dd", { text: episode.duration_known ? `${episode.duration_days} days` : "Unknown" }),
      ]),
      el("div", {}, [
        el("dt", { text: "Usage" }),
        el("dd", { text: episode.metrics?.usage_gb == null ? "Unknown" : `${episode.metrics.usage_gb} GB` }),
      ]),
      el("div", {}, [
        el("dt", { text: "Plan selected" }),
        el("dd", { text: episode.actions.plan_selected || "None" }),
      ]),
      el("div", {}, [el("dt", { text: "Outcome" }), el("dd", { text: episode.outcome })]),
    ]),
    el("p", { className: "meta", text: (match.reasons || []).join(" • ") || "Ranked historical episode" }),
  ]);
}

function historyList(episodes) {
  if (!episodes.length) {
    return statusBox("empty", "No historical travel episodes at this as_of.");
  }
  return el(
    "ol",
    { className: "timeline" },
    episodes.map((episode) =>
      el("li", {}, [
        el("time", { text: formatDate(episode.start_at) }),
        el("div", {}, [
          el("div", {
            text: `${episode.destination_name}: ${episode.duration_known ? `${episode.duration_days} days` : "duration unknown"}, ${episode.metrics?.usage_gb == null ? "usage unknown" : `${episode.metrics.usage_gb} GB`}, ${episode.actions?.plan_selected || "no roam plan"}`,
          }),
          el("small", { text: episode.outcome }),
        ]),
        badge("Derived", "derived"),
      ]),
    ),
  );
}

export async function renderJourney(root, { signal } = {}) {
  root.replaceChildren(statusBox("loading", "Loading event memory…"));
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
  const destination = (params.get("destination") || "").trim();

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
    el("label", { text: "As of date (optional)" }, [
      el("input", {
        name: "as_of",
        type: "date",
        value: asOf.slice(0, 10),
        "aria-label": "As of date",
      }),
    ]),
    el("label", { text: "Query destination" }, [
      el("input", {
        name: "destination",
        type: "text",
        value: destination,
        placeholder: "SG",
        "aria-label": "Destination country",
      }),
    ]),
    el("button", { type: "submit", text: "Recall episodes" }),
  ]);
  toolbar.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(toolbar);
    const next = new URLSearchParams({ ref: String(data.get("ref") || "U001") });
    const nextAsOf = String(data.get("as_of") || "").trim();
    const nextDest = String(data.get("destination") || "").trim();
    if (nextAsOf) next.set("as_of", nextAsOf);
    if (nextDest) next.set("destination", nextDest);
    window.location.hash = `#/journey?${next.toString()}`;
  });

  const results = el("div", { className: "page-results" });
  root.replaceChildren(
    el("div", { className: "page-header" }, [
      el("div", {}, [
        el("h1", { text: "Journey and Event Memory" }),
        el("p", {
          text: "Derived travel episodes, similar-event matches, catalogue offers and a next-best action.",
        }),
      ]),
      badge("Live evidence", "live"),
    ]),
    toolbar,
    results,
  );

  results.replaceChildren(statusBox("loading", "Recalling similar historical episodes…"));
  const [memoryOutcome, recsOutcome, decisionOutcome] = await Promise.allSettled([
    api.eventMemory(selected, asOf || undefined, destination || undefined, { signal }),
    api.customerRecommendations(selected, asOf || undefined, destination || undefined, { signal }),
    api.customerDecision(selected, asOf || undefined, destination || undefined, { signal }),
  ]);
  if (stale(signal)) return;
  if (memoryOutcome.status === "rejected") {
    if (isAbortError(memoryOutcome.reason)) return;
    results.replaceChildren(errorBox(memoryOutcome.reason, `Could not recall episodes for ${selected}.`));
    return;
  }
  const data = memoryOutcome.value;
  const matches = data.matches || [];
  const recs = recsOutcome.status === "fulfilled" ? recsOutcome.value : null;
  const recsError =
    recsOutcome.status === "rejected" && !isAbortError(recsOutcome.reason) ? recsOutcome.reason : null;
  const decision = decisionOutcome.status === "fulfilled" ? decisionOutcome.value : null;
  const decisionError =
    decisionOutcome.status === "rejected" && !isAbortError(decisionOutcome.reason)
      ? decisionOutcome.reason
      : null;
  results.replaceChildren(
    situationCard(data),
    el("section", { className: "card" }, [
      el("header", {}, [el("h2", { text: "Retrieved episodes" }), badge("Derived", "derived")]),
      matches.length
        ? el(
            "div",
            { className: "grid grid-2" },
            matches.map((match) => episodeCard(match)),
          )
        : statusBox("empty", "No similar episodes retrieved."),
    ]),
    el("section", { className: "card" }, [
      el("header", {}, [el("h2", { text: "Historical travel episodes" }), badge("Derived", "derived")]),
      historyList(data.historical_episodes || []),
    ]),
    recommendationPanel(recs, recsError),
    decisionPanel(decision, decisionError),
  );
}

function recommendationPanel(data, error) {
  if (error) {
    return el("section", { className: "card" }, [
      el("header", {}, [el("h3", { text: "Recommendation" }), badge("Unavailable", "unknown")]),
      el("p", { text: "Catalogue ranking could not be loaded. Retrieved episodes remain live." }),
    ]);
  }
  if (!data) {
    return el("section", { className: "card" }, [
      el("header", {}, [el("h3", { text: "Recommendation" }), badge("Recommend", "recommend")]),
      el("p", { text: "Ranked catalogue offers appear when a destination is known." }),
    ]);
  }
  const ranked = data.ranked || [];
  return el("section", { className: "card" }, [
    el("header", {}, [el("h3", { text: "Recommendation" }), badge("Recommend", "recommend")]),
    el("p", {
      text: data.primary
        ? `${data.mode.replaceAll("_", " ")} • ${data.primary.plan_code} (${data.primary.scenario_label})`
        : `${data.mode.replaceAll("_", " ")} • no catalogue offer`,
    }),
    ranked.length
      ? el(
          "ol",
          { className: "timeline" },
          ranked.map((item) =>
            el("li", {}, [
              el("div", {}, [
                el("div", { text: `${item.plan_code} • ${item.plan_name}` }),
                el("small", {
                  text: `${item.scenario_label} • score ${item.score} • ${(item.reasons || []).join(" • ")}`,
                }),
              ]),
              badge("Recommend", "recommend"),
            ]),
          ),
        )
      : el("p", { text: "No active roaming catalogue offer was ranked." }),
    el("p", { className: "meta", text: data.recommendation_set_version }),
    ...(data.uncertainty || []).map((item) =>
      el("p", {}, [
        badge(item.status, item.status === "unknown" ? "unknown" : "recommend"),
        " ",
        `${item.name.replaceAll("_", " ")}: ${item.value || item.note || item.status}`,
      ]),
    ),
  ]);
}
