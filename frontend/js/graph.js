import { api } from "./api.js";
import { badge, el, formatNumber, provenanceLine, statusBox } from "./dom.js";

function countTable(title, rows) {
  return el("section", { className: "card" }, [
    el("header", {}, [el("h2", { text: title }), badge("Graph projection", "graph")]),
    el("table", { className: "table" }, [
      el("tbody", {}, (rows || []).map((row) =>
        el("tr", {}, [el("td", { text: row.kind }), el("td", { text: formatNumber(row.total) })]),
      )),
    ]),
  ]);
}

export async function renderGraph(root) {
  root.replaceChildren(statusBox("loading", "Loading managed Neo4j projection…"));
  try {
    const [data, customer] = await Promise.all([
      api.graphSummary(),
      api.graphCustomer("U009"),
    ]);
    root.replaceChildren(
      el("div", { className: "page-header" }, [
        el("div", {}, [el("h1", { text: "Graph Explorer" }), el("p", { text: `${data.projection} • ${data.as_of}` })]),
        badge(data.reconciled ? "Reconciled" : "Review", data.reconciled ? "live" : "warning"),
      ]),
      el("div", { className: "grid grid-2" }, [countTable("Managed nodes", data.node_counts), countTable("Managed relationships", data.relationship_counts)]),
      el("section", { className: "card" }, [
        el("header", {}, [el("h2", { text: "Shared-device evidence" }), badge("Graph projection", "graph")]),
        data.shared_devices?.length
          ? el("table", { className: "table" }, [el("tbody", {}, data.shared_devices.map((row) => el("tr", {}, [el("td", { text: row.device_ref }), el("td", { text: `${row.customers} customers` })])))])
          : statusBox("empty", "No shared devices at this as_of."),
        el("p", { className: "meta", text: provenanceLine({ source: data.source, as_of: data.as_of, dataset_version: data.projection }) }),
      ]),
      el("section", { className: "card" }, [
        el("header", {}, [el("h2", { text: "Customer graph context — U009" }), badge("Graph projection", "graph")]),
        customer.available
          ? el("dl", { className: "feature-list" }, Object.entries(customer.values).map(([name, value]) =>
            el("div", {}, [el("dt", { text: name.replaceAll("_", " ") }), el("dd", { text: formatNumber(value) })]),
          ))
          : statusBox("empty", "Customer graph context unavailable", customer.unknowns?.join(" ")),
      ]),
    );
  } catch (error) {
    root.replaceChildren(statusBox("error", "Neo4j unavailable", error.message));
  }
}
