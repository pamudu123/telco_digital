import { api, isAbortError } from "./api.js";
import { badge, el, statusBox } from "./dom.js";
import { errorBox } from "./customer-360.js";

const IMPACT = [
  ["Selfcare", "Next best action, churn-aware service, roaming guidance — later capabilities."],
  ["Loyalty", "Reward ranking and retention actions — later capabilities."],
  ["adReach", "Audience intelligence and propensity — later capabilities."],
  ["Viber", "Channel selection — later capabilities."],
  ["Mobile Money", "Graph fraud evidence — later capabilities."],
  ["SFA", "Forecasts and visit priorities — later capabilities."],
  ["Lottery", "Secondary lens; abuse investigation later."],
];

export async function renderStatus(root, { signal } = {}) {
  root.replaceChildren(statusBox("loading", "Loading capability status…"));
  try {
    const data = await api.status({ signal });
    if (signal?.aborted) return;
    const table = el("table", { className: "table" }, [
      el("thead", {}, [
        el("tr", {}, [
          el("th", { text: "#" }),
          el("th", { text: "Capability" }),
          el("th", { text: "Status" }),
          el("th", { text: "Demonstrated scenario" }),
          el("th", { text: "Applications" }),
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
          ]),
        ),
      ),
    ]);
    root.replaceChildren(
      el("div", { className: "page-header" }, [
        el("div", {}, [
          el("h1", { text: "POC status and application impact" }),
          el("p", { text: data.notes }),
        ]),
      ]),
      el("section", { className: "card" }, [
        el("h2", { text: "Capability status" }),
        table,
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
      el("section", { className: "card" }, [
        el("h2", { text: "Retained capability-00 artifacts" }),
        el("p", { text: "These links are labeled artifacts. They do not backfill live metric cards." }),
        el(
          "ul",
          {},
          (data.artifacts || []).map((item) =>
            el("li", {}, [
              el("strong", { text: item.title }),
              " — ",
              item.description,
              " (",
              badge(item.source, "unknown"),
              " ",
              item.path,
              ")",
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
