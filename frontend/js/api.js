import { API_BASE_URL } from "./config.js";

export class ApiError extends Error {
  constructor(status, payload) {
    super(payload?.detail || `Request failed (${status})`);
    this.status = status;
    this.payload = payload;
    this.source = payload?.source || payload?.detail?.source;
  }
}

async function request(path) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`);
  } catch {
    throw new ApiError(503, { source: "unavailable", detail: "API is unreachable" });
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(response.status, payload);
  }
  return payload;
}

export const api = {
  overview: (asOf) => request(`/showcase/overview${asOf ? `?as_of=${encodeURIComponent(asOf)}` : ""}`),
  evidence: (asOf) => request(`/showcase/evidence${asOf ? `?as_of=${encodeURIComponent(asOf)}` : ""}`),
  personas: () => request("/showcase/personas"),
  status: () => request("/showcase/status"),
  walkthroughs: () => request("/showcase/walkthroughs"),
  customer360: (ref, asOf) =>
    request(`/customers/${encodeURIComponent(ref)}/360${asOf ? `?as_of=${encodeURIComponent(asOf)}` : ""}`),
  retailer: (ref, asOf) =>
    request(
      `/showcase/sfa/retailers/${encodeURIComponent(ref)}${asOf ? `?as_of=${encodeURIComponent(asOf)}` : ""}`,
    ),
};
