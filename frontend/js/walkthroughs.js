import { api, isAbortError } from "./api.js";
import { badge, el, statusBox } from "./dom.js";
import { errorBox } from "./customer-360.js";

export async function renderWalkthroughs(root, { signal } = {}) {
  root.replaceChildren(statusBox("loading", "Loading guided demonstrations…"));
  try {
    const data = await api.walkthroughs({ signal });
    if (signal?.aborted) return;
    root.replaceChildren(
      el("div", { className: "page-header" }, [
        el("div", {}, [
          el("h1", { text: "Golden-scenario walkthroughs" }),
          el("p", {
            text: "Facts and reconstructed context are live. Inferences and recommendations stay POC planned.",
          }),
        ]),
      ]),
      ...data.walkthroughs.map((item) =>
        el("article", { className: "card walkthrough" }, [
          el("header", { className: "page-header" }, [
            el("div", {}, [
              el("h2", { text: item.title }),
              el("p", {
                text: `${item.customer_ref || item.retailer_ref || ""} • ${item.applications.join(", ")}`,
              }),
            ]),
            badge("Recorded facts available", "fact"),
          ]),
          el("p", { text: `Current evidence: ${item.current_evidence}` }),
          el("p", {}, [badge("POC planned", "planned"), ` Later: ${item.later_intelligence}`]),
          el(
            "ol",
            {},
            item.steps.map((step) =>
              el("li", { dataset: { live: String(step.live) } }, [
                el("strong", { text: `${step.number}. ${step.title}` }),
                " — ",
                step.summary,
                " ",
                badge(step.live ? "Live facts" : "POC planned", step.live ? "fact" : "planned"),
              ]),
            ),
          ),
          item.customer_ref
            ? el("a", { href: `#/customer-360?ref=${encodeURIComponent(item.customer_ref)}`, text: "Open Customer 360" })
            : el("a", { href: "#/retail", text: "Open Retail and SFA" }),
        ]),
      ),
    );
  } catch (error) {
    if (signal?.aborted || isAbortError(error)) return;
    root.replaceChildren(errorBox(error, "Could not load walkthroughs."));
  }
}
