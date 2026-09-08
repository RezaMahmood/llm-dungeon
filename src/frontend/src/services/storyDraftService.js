import axios from "axios";

const client = axios.create({
  baseURL: "/api",
});

function authHeaders(token) {
  return { headers: { "X-Custom-Authorization": `Bearer ${token}` } };
}

export async function createDraft(token, idea) {
  const response = await client.post("/manage/stories/drafts", idea ? { idea } : {}, authHeaders(token));
  return response.data;
}

export async function getDraft(token, draftId) {
  const response = await client.get(`/manage/stories/drafts/${draftId}`, authHeaders(token));
  return response.data;
}

export async function patchDraft(token, draftId, updates) {
  const response = await client.patch(`/manage/stories/drafts/${draftId}`, updates, authHeaders(token));
  return response.data;
}

// One pass over the idea (#227): the response's draft carries the suggested worldPrompt,
// and nothing else about the draft changes.
export async function suggestWorldPrompt(token, draftId, idea) {
  const response = await client.post(`/manage/stories/drafts/${draftId}/world-prompt`, { idea }, authHeaders(token));
  return response.data;
}

export async function generateStory(token, draftId) {
  const response = await client.post(`/manage/stories/drafts/${draftId}/generate`, {}, authHeaders(token));
  return response.data;
}

export async function listStories(token) {
  const response = await client.get("/manage/stories", authHeaders(token));
  return response.data;
}

export async function getStory(token, storyId) {
  const response = await client.get(`/manage/stories/${storyId}`, authHeaders(token));
  return response.data;
}

export async function publishStory(token, storyId) {
  const response = await client.post(`/manage/stories/${storyId}/publish`, {}, authHeaders(token));
  return response.data;
}

export async function unpublishStory(token, storyId) {
  const response = await client.post(`/manage/stories/${storyId}/unpublish`, {}, authHeaders(token));
  return response.data;
}

export async function deleteStory(token, storyId) {
  const response = await client.delete(`/manage/stories/${storyId}`, authHeaders(token));
  return response.data;
}

// Requests the raw response text rather than a parsed object (axios's default JSON
// parse would discard the exact bytes) — the viewer and the download both reuse this
// same string, which is what makes them byte-identical by construction (FR-002, SC-001).
export async function getStoryConfiguration(token, storyId) {
  const response = await client.get(`/manage/stories/${storyId}/configuration`, {
    ...authHeaders(token),
    transformResponse: (r) => r,
  });
  return response.data;
}

export async function createEditDraft(token, storyId) {
  const response = await client.post(`/manage/stories/${storyId}/edit-drafts`, {}, authHeaders(token));
  return response.data;
}

export async function saveDraftToStory(token, draftId) {
  const response = await client.post(`/manage/stories/drafts/${draftId}/save`, {}, authHeaders(token));
  return response.data;
}

export async function importStoryConfiguration(token, body) {
  const response = await client.post("/manage/stories/import", body, authHeaders(token));
  return response.data;
}

export default {
  createDraft,
  getDraft,
  patchDraft,
  suggestWorldPrompt,
  generateStory,
  listStories,
  getStory,
  publishStory,
  unpublishStory,
  deleteStory,
  getStoryConfiguration,
  createEditDraft,
  saveDraftToStory,
  importStoryConfiguration,
};
