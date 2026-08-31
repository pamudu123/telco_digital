import { api, isAbortError } from "./api.js";
import { SOURCE_REPOSITORY_URL } from "./config.js";
import { badge, el, statusBox } from "./dom.js";
import { errorBox } from "./customer-360.js";

const IMPACT = [
  ["Selfcare", "Next best action, churn-aware service, roaming guidance — later capabilities."],
  ["Loyalty", "Reward ranking and retention actions — later capabilities."],
  ["adReach", "Audience intelligence and propensity — later capabilities."],
  ["Viber", "Channel selection — later capabilities."],
  ["Mobile Money", "Graph fraud scores are live; review recommendations stay later."],
  ["SFA", "Demand forecasts and retailer twins are live; visit priorities stay later."],
  ["Lottery", "Secondary lens; abuse investigation later."],
];

function evidenceLabel(path) {
  if (path.endsWith(".ipynb")) return "Executed notebook";
  if (path.endsWith("metrics.json")) return "Metrics";
  if (path.includes("/artifacts/")) return "Model artifact";
  if (path.endsWith("/tables/")) return "Tables";
  if (path.endsWith("/plots/")) return "Plots";
  if (path.endsWith(".md")) return "Documentation";
  return path.split("/").pop() || path;
}

function evidenceUrl(path) {
  const view = path.endsWith("/") ? "tree" : "blob";
  return `${SOURCE_REPOSITORY_URL}/${view}/main/${path.replace(/\/$/, "")}`;
}

function evidenceList(paths) {
  const submitted = (paths || []).filter((path) => !path.endsWith("/plots/"));
  if (!submitted.length) return badge("Not submitted", "planned");
  return el(
    "ul",
    { className: "evidence-list" },
    submitted.map((path) =>
      el("li", {}, [
        el("a", {
          href: evidenceUrl(path),
          target: "_blank",
          rel: "noopener noreferrer",
          text: evidenceLabel(path),
        }),
      ]),
    ),
  );
}

export async function renderStatus(root, { signal } = {}) {
  root.replaceChildren(statusBox("loading", "Loading capability status…"));
  try {
    const [data, health, models, lag] = await Promise.allSettled([
      api.status({ signal }),
      api.health({ signal }),
      api.models({ signal }),
      api.projectionLag({ signal }),
    ]).then((results) => results.map((item) => (item.status === "fulfilled" ? item.value : item.reason)));
    if (signal?.aborted) return;
    if (data instanceof Error) throw data;
    const table = el("table", { className: "table" }, [
      el("thead", {}, [
        el("tr", {}, [
          el("th", { text: "#" }),
          el("th", { text: "Capability" }),
          el("th", { text: "Status" }),
          el("th", { text: "Demonstrated scenario" }),
          el("th", { text: "Applications" }),
          el("th", { text: "Live evidence" }),
        ]),
      ]),
      el(
        "tbody",
        {},
        data.capabilities.map((item) =>
          el("tr", {}, [
            el("td", { text: item.number }),
            el("td", { text: item.name }),
            el("td", {}, [
              badge(item.status, item.status === "POC complete" ? "live" : "planned"),
            ]),
            el("td", { text: item.demonstrated_scenario }),
            el("td", { text: (item.consuming_applications || []).join(", ") }),
            el("td", {}, [evidenceList(item.evidence)]),
          ]),
        ),
      ),
    ]);
    const healthCard =
      health instanceof Error
        ? errorBox(health, "Health endpoint unavailable.")
        : el("article", { className: "card" }, [
            el("h3", { text: "Health" }),
            badge(health.slice || "live", "live"),
            el("p", { text: `status=${health.status} environment=${health.environment}` }),
          ]);
    const lagCard =
      lag instanceof Error
        ? el("article", { className: "card" }, [
            el("h3", { text: "Projection lag" }),
            badge("Not connected", "unknown"),
            el("p", {
              text: "Connect PostgreSQL to view pending events and projection timing.",
            }),
          ])
        : el("article", { className: "card" }, [
            el("h3", { text: "Projection lag" }),
            badge("Graph projection", "live"),
            el("p", {
              text: `pending=${lag.pending_count} processed=${lag.processed_count} lag_seconds=${lag.lag_seconds}`,
            }),
          ]);
    const modelRows = models instanceof Error ? [] : models.models || [];
    const modelsCard =
      models instanceof Error
        ? errorBox(models, "Model catalog unavailable.")
        : el("article", { className: "card" }, [
            el("h3", { text: "Served model versions" }),
            badge("Prediction", "live"),
            el(
              "ul",
              {},
              modelRows.map((item) =>
                el("li", {
                  text: `${item.name} ${item.version} (${item.kind}${item.served ? ", served" : ""})`,
                }),
              ),
            ),
          ]);
    root.replaceChildren(
      el("div", { className: "page-header" }, [
        el("div", {}, [
          el("h1", { text: "POC status and application impact" }),
          el("p", { text: data.notes }),
        ]),
        badge("Live evidence", "live"),
      ]),
      el("section", { className: "card" }, [
        el("h2", { text: "FastAPI platform" }),
        el("p", { text: "Live health, outbox projection lag and served model versions from capability 12." }),
        el("div", { className: "impact-grid" }, [healthCard, lagCard, modelsCard]),
      ]),
      el("section", { className: "card" }, [
        el("h2", { text: "Capability status" }),
        el("p", {
          text: "Open the retained documentation, executed notebooks, metrics, tables and model artifacts for each completed capability.",
        }),
        el("div", { className: "table-scroll" }, [table]),
      ]),
      el("section", { className: "card" }, [
        el("h2", { text: "Application impact examples" }),
        el("p", { text: "These examples are future intelligence, not live output." }),
        el(
          "div",
          { className: "impact-grid" },
          IMPACT.map(([title, detail]) =>
            el("article", { className: "card" }, [
              el("h3", { text: title }),
              badge("POC planned", "planned"),
              el("p", { text: detail }),
            ]),
          ),
        ),
      ]),
    );
  } catch (error) {
    if (signal?.aborted || isAbortError(error)) return;
    root.replaceChildren(errorBox(error, "Could not load capability status."));
  }
}
