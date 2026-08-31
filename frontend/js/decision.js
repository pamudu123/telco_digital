import { badge, el } from "./dom.js";

export function decisionPanel(data, error) {
  if (error) {
    return el("section", { className: "card" }, [
      el("header", {}, [el("h3", { text: "Decision" }), badge("Unavailable", "unknown")]),
      el("p", { text: "Next-best action could not be loaded. Recorded facts remain live." }),
    ]);
  }
  if (!data) {
    return el("section", { className: "card" }, [
      el("header", {}, [el("h3", { text: "Decision" }), badge("Recommend", "recommend")]),
      el("p", { text: "A next-best action appears when recommendations, traits and churn are available." }),
    ]);
  }
  const explanation = data.explanation || {};
  const alternatives = explanation.alternatives || [];
  const codes = data.reason_codes || [];
  return el("section", { className: "card" }, [
    el("header", {}, [el("h3", { text: "Decision" }), badge("Recommend", "recommend")]),
    el("p", {
      text: data.target_plan_code
        ? `${String(data.action || "").replaceAll("_", " ")} • ${data.target_plan_code}`
        : String(data.action || "NO ACTION").replaceAll("_", " "),
    }),
    el("dl", { className: "feature-list" }, [
      el("div", {}, [el("dt", { text: "What" }), el("dd", { text: explanation.what || "Unknown" })]),
      el("div", {}, [el("dt", { text: "Why" }), el("dd", { text: explanation.why || "Unknown" })]),
      el("div", {}, [
        el("dt", { text: "Alternatives" }),
        el("dd", { text: alternatives.length ? alternatives.join(", ") : "None" }),
      ]),
    ]),
    codes.length
      ? el(
          "p",
          { className: "meta" },
          codes.flatMap((code, index) => [
            index ? " " : null,
            badge(String(code).replaceAll("_", " "), "recommend"),
          ]),
        )
      : null,
    el("p", { className: "meta", text: data.decision_set_version }),
  ]);
}

