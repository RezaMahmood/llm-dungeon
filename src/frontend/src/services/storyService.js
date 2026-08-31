import axios from "axios";

const client = axios.create({
  baseURL: "/api",
});

function authHeaders(token, extraHeaders) {
  return { headers: { Authorization: `Bearer ${token}`, ...extraHeaders } };
}

export async function createStory(token, fields) {
  const response = await client.post("/manage/stories", fields, authHeaders(token));
  return response.data;
}

export async function updateStory(token, storyId, fields) {
  const response = await client.patch(`/manage/stories/${storyId}`, fields, authHeaders(token));
  return response.data;
}

export async function deleteStory(token, storyId) {
  const response = await client.delete(`/manage/stories/${storyId}`, authHeaders(token));
  return response.data;
}

export async function uploadCoverImage(token, storyId, file) {
  const response = await client.post(
    `/manage/stories/${storyId}/cover-image`,
    file,
    authHeaders(token, { "Content-Type": file.type || "application/octet-stream", "X-File-Name": file.name }),
  );
  return response.data;
}

export async function suggestOutline(token, idea) {
  const response = await client.post("/manage/stories/suggest-outline", { idea }, authHeaders(token));
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

export default {
  createStory,
  updateStory,
  deleteStory,
  uploadCoverImage,
  suggestOutline,
  listStories,
  getStory,
};
