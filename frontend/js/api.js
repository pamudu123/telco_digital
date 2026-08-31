import { API_BASE_URL } from "./config.js";

export class ApiError extends Error {
  constructor(status, payload) {
    super(payload?.detail || `Request failed (${status})`);
    this.status = status;
    this.payload = payload;
    this.source = payload?.source || payload?.detail?.source;
  }
}

export function isAbortError(error) {
  return Boolean(error && error.name === "AbortError");
}

function asOfQuery(path, asOf) {
  return asOf ? `${path}?as_of=${encodeURIComponent(asOf)}` : path;
}

async function request(path, options = {}) {
  const { signal } = options;
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, signal ? { signal } : {});
  } catch (error) {
    if (isAbortError(error)) throw error;
    throw new ApiError(503, { source: "unavailable", detail: "API is unreachable" });
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(response.status, payload);
  }
  return payload;
}

export const api = {
  overview: (asOf, options) => request(asOfQuery("/showcase/overview", asOf), options),
  evidence: (asOf, options) => request(asOfQuery("/showcase/evidence", asOf), options),
  personas: (options) => request("/showcase/personas", options),
  status: (options) => request("/showcase/status", options),
  walkthroughs: (options) => request("/showcase/walkthroughs", options),
  customer360: (ref, asOf, options) =>
    request(asOfQuery(`/customers/${encodeURIComponent(ref)}/360`, asOf), options),
  customerFeatures: (ref, asOf, options) =>
    request(asOfQuery(`/customers/${encodeURIComponent(ref)}/features`, asOf), options),
  customerBehaviour: (ref, asOf, options) =>
    request(asOfQuery(`/customers/${encodeURIComponent(ref)}/behaviour`, asOf), options),
  customerChurn: (ref, asOf, options) =>
    request(asOfQuery(`/customers/${encodeURIComponent(ref)}/churn`, asOf), options),
  customerFraud: (ref, asOf, options) =>
    request(asOfQuery(`/customers/${encodeURIComponent(ref)}/fraud`, asOf), options),
  customerRecommendations: (ref, asOf, destination, options) => {
    const path = asOfQuery(`/customers/${encodeURIComponent(ref)}/recommendations`, asOf);
    const separator = path.includes("?") ? "&" : "?";
    return request(
      destination ? `${path}${separator}destination=${encodeURIComponent(destination)}` : path,
      options,
    );
  },
  eventMemory: (ref, asOf, destination, options) => {
    const path = asOfQuery(`/customers/${encodeURIComponent(ref)}/event-memory`, asOf);
    const separator = path.includes("?") ? "&" : "?";
    return request(
      destination ? `${path}${separator}destination=${encodeURIComponent(destination)}` : path,
      options,
    );
  },
  graphSummary: (asOf, options) => request(asOfQuery("/showcase/graph/summary", asOf), options),
  graphCustomer: (ref, asOf, options) =>
    request(asOfQuery(`/showcase/graph/customers/${encodeURIComponent(ref)}`, asOf), options),
  retailer: (ref, asOf, options) =>
    request(asOfQuery(`/showcase/sfa/retailers/${encodeURIComponent(ref)}`, asOf), options),
};
