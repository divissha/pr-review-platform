// Real API client for the Django backend. Same function names as mockApi.js,
// so the pages only had to change their import.
const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.json()).detail || "";
    } catch {
      /* response had no JSON body */
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const getPRs = () => request("/api/prs/");
export const getPRDetail = (id) => request(`/api/prs/${id}/`);
export const getComments = (id) => request(`/api/prs/${id}/comments/`);
export const postComment = (id, body) =>
  request(`/api/prs/${id}/comments/`, { method: "POST", body: JSON.stringify({ body }) });
export const getEvaluationSummary = () => request("/api/evaluation/summary/");