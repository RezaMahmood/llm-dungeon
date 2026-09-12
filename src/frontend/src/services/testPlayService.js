import axios from "axios";

const client = axios.create({
  baseURL: "/api",
});

/** Starts a test-play session against a story's current saved configuration — works on an
 * unpublished story (010-story-test-play-done, contracts/api.md FR-001). */
export async function startTestPlay(token, storyId) {
  const response = await client.post(
    `/manage/stories/${storyId}/test-play`,
    {},
    { headers: { "X-Custom-Authorization": `Bearer ${token}` } },
  );
  return response.data;
}

/** Submits one test instruction and returns its narrative response (FR-002, FR-004). */
export async function submitTestPlayInstruction(token, sessionId, input) {
  const response = await client.post(
    `/manage/test-play-sessions/${sessionId}/interactions`,
    { input },
    { headers: { "X-Custom-Authorization": `Bearer ${token}` } },
  );
  return response.data;
}

/** Aborts and permanently deletes the session (FR-005). */
export async function deleteTestPlaySession(token, sessionId) {
  const response = await client.delete(`/manage/test-play-sessions/${sessionId}`, {
    headers: { "X-Custom-Authorization": `Bearer ${token}` },
  });
  return response.data;
}

/** Rehydrates a session, e.g. after a browser refresh. */
export async function getTestPlaySession(token, sessionId) {
  const response = await client.get(`/manage/test-play-sessions/${sessionId}`, {
    headers: { "X-Custom-Authorization": `Bearer ${token}` },
  });
  return response.data;
}
