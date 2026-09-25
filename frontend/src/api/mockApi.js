// Mock API — mirrors the real Django REST endpoints.
// When the backend is ready, swap the body of each function for a real
// fetch/axios call. Every function name + return shape stays the same,
// so no component code needs to change.
import {
  mockPRs,
  mockPRDetail,
  mockComments,
  mockEvaluationSummary,
} from "./mockData";

// Simulates network latency so loading states can be tested
const delay = (ms = 300) => new Promise((res) => setTimeout(res, ms));

// GET /api/prs/
export async function getPRs() {
  await delay();
  return mockPRs;
}

// GET /api/prs/{id}/
export async function getPRDetail(id) {
  await delay();
  const pr = mockPRDetail[id];
  if (!pr) throw new Error(`PR ${id} not found`);
  return pr;
}

// GET /api/prs/{id}/comments/
export async function getComments(id) {
  await delay();
  return mockComments[id] || [];
}

// POST /api/prs/{id}/comments/
export async function postComment(id, body) {
  await delay();
  const newComment = {
    id: Date.now(),
    user: "yourname",
    body,
    line_ref: null,
    created_at: new Date().toISOString(),
  };
  if (!mockComments[id]) mockComments[id] = [];
  mockComments[id].push(newComment);
  return newComment;
}

// GET /api/evaluation/summary/
export async function getEvaluationSummary() {
  await delay();
  return mockEvaluationSummary;
}

/*
  REAL VERSION (swap in once Django backend is live):

  const BASE_URL = import.meta.env.VITE_API_URL;

  export async function getPRs() {
    const res = await fetch(`${BASE_URL}/api/prs/`);
    if (!res.ok) throw new Error("Failed to fetch PRs");
    return res.json();
  }
*/
