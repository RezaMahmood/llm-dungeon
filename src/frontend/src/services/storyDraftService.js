import axios from "axios";

const client = axios.create({
  baseURL: "/api",
});

function authHeaders(token) {
  return { headers: { Authorization: `Bearer ${token}` } };
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

export async function postMessage(token, draftId, message) {
  const response = await client.post(`/manage/stories/drafts/${draftId}/messages`, { message }, authHeaders(token));
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

export default { createDraft, getDraft, patchDraft, postMessage, listStories, getStory };
