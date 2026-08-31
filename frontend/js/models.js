import { api, isAbortError } from "./api.js";
import { errorBox } from "./customer-360.js";
import { decisionPanel } from "./decision.js";
import { badge, el, statusBox } from "./dom.js";

export async function renderModels(root, { signal } = {}) {
  root.replaceChildren(statusBox("loading", "Loading decision evidence…"));
  let personas;
  try {
    personas = await api.personas({ signal });
  } catch (error) {
    if (signal?.aborted || isAbortError(error)) return;
    root.replaceChildren(errorBox(error, "Could not load personas."));
    return;
  }
  if (signal?.aborted) return;

  const params = new URLSearchParams(window.location.hash.split("?")[1] || "");
  const selected = params.get("ref") || "U001";
  const asOf = params.get("as_of") || "";
  const destination = (params.get("destination") || (selected === "U001" ? "SG" : "")).trim();

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
        placeholder: "2026-08-20T12:00:00+00:00",
        "aria-label": "As of timestamp",
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
    el("button", { type: "submit", text: "Load next-best action" }),
  ]);
  toolbar.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(toolbar);
    const next = new URLSearchParams({ ref: String(data.get("ref") || "U001") });
    const nextAsOf = String(data.get("as_of") || "").trim();
    const nextDest = String(data.get("destination") || "").trim();
    if (nextAsOf) next.set("as_of", nextAsOf);
    if (nextDest) next.set("destination", nextDest);
    window.location.hash = `#/models?${next.toString()}`;
  });

  const results = el("div", { className: "page-results" });
  root.replaceChildren(
    el("div", { className: "page-header" }, [
      el("div", {}, [
        el("h1", { text: "Models and Decisions" }),
        el("p", {
          text: "Live next-best actions from the decision engine. Computed twins are live on Customer 360.",
        }),
      ]),
      badge("Live evidence", "live"),
    ]),
    toolbar,
    results,
  );

  results.replaceChildren(statusBox("loading", "Evaluating next-best action…"));
  try {
    const decision = await api.customerDecision(
      selected,
      asOf || undefined,
      destination || undefined,
      { signal },
    );
    if (signal?.aborted) return;
    results.replaceChildren(
      decisionPanel(decision),
      el("section", { className: "card" }, [
        el("header", {}, [el("h3", { text: "Digital twins" }), badge("Live evidence", "live")]),
        el("p", {
          text: "Computed twins are live on Customer 360. This page scores next-best actions only.",
        }),
        el("a", {
          href: `#/customer-360?ref=${encodeURIComponent(selected)}`,
          text: "Open Customer 360 twin",
        }),
      ]),
    );
  } catch (error) {
    if (signal?.aborted || isAbortError(error)) return;
    results.replaceChildren(errorBox(error, `Could not evaluate a decision for ${selected}.`));
  }
}
