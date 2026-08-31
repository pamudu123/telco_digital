import { api, isAbortError } from "./api.js";
import { errorBox } from "./customer-360.js";
import { badge, el, provenanceLine, statusBox } from "./dom.js";

const DEFAULT_QUESTION = "Why is U001 receiving this recommendation?";

export async function renderCopilot(root, { signal } = {}) {
  root.replaceChildren(statusBox("loading", "Loading Copilot…"));
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
  const question = params.get("q") || DEFAULT_QUESTION;

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
    el("label", { className: "question-field", text: "Question" }, [
      el("input", {
        name: "q",
        type: "text",
        value: question,
        "aria-label": "Copilot question",
      }),
    ]),
    el("button", { type: "submit", text: "Ask Copilot" }),
  ]);
  toolbar.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(toolbar);
    const next = new URLSearchParams({
      ref: String(data.get("ref") || "U001"),
      q: String(data.get("q") || DEFAULT_QUESTION),
    });
    const nextAsOf = String(data.get("as_of") || "").trim();
    const nextDest = String(data.get("destination") || "").trim();
    if (nextAsOf) next.set("as_of", nextAsOf);
    if (nextDest) next.set("destination", nextDest);
    window.location.hash = `#/copilot?${next.toString()}`;
  });

  const results = el("div", { className: "page-results" });
  root.replaceChildren(
    el("div", { className: "page-header" }, [
      el("div", {}, [
        el("h1", { text: "Copilot" }),
        el("p", {
          text: "Read-only answers from the decision document. The model cannot invent plans, discounts or destinations.",
        }),
      ]),
      badge("Live evidence", "live"),
    ]),
    toolbar,
    results,
  );

  results.replaceChildren(statusBox("loading", "Building a grounded answer…"));
  try {
    const answer = await api.copilotAsk(
      {
        question,
        customer_ref: selected,
        as_of: asOf || undefined,
        destination: destination || undefined,
      },
      { signal },
    );
    if (signal?.aborted) return;
    const fromModel = answer.source === "openrouter_glm";
    results.replaceChildren(
      el("section", { className: "card" }, [
        el("header", { className: "page-header" }, [
          el("h2", { text: "Answer" }),
          badge(fromModel ? "Model" : "Fallback", fromModel ? "live" : "derived"),
        ]),
        el("p", { text: answer.answer }),
        el("p", { className: "meta", text: provenanceLine(answer) }),
        el("p", {
          className: "meta",
          text: [
            answer.copilot_set_version,
            answer.model || "no model",
            answer.fallback_reason || "grounded",
          ].join(" • "),
        }),
      ]),
      el("section", { className: "card" }, [
        el("header", {}, [el("h3", { text: "Provenance" }), badge("Derived", "derived")]),
        el(
          "ul",
          { className: "timeline" },
          (answer.used_facts || []).map((item) => el("li", {}, [el("div", { text: item })])),
        ),
        ...(answer.unknowns || []).map((item) =>
          el("p", {}, [badge("Unknown", "unknown"), " ", item]),
        ),
      ]),
    );
  } catch (error) {
    if (signal?.aborted || isAbortError(error)) return;
    results.replaceChildren(errorBox(error, `Could not answer for ${selected}.`));
  }
}
