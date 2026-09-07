import axios from "axios";

const client = axios.create({
  baseURL: "/api",
});

export async function listAdventures(token) {
  const response = await client.get("/game/adventures", {
    headers: { "X-Custom-Authorization": `Bearer ${token}` },
  });
  return response.data;
}

export async function getAdventure(token, adventureId) {
  const response = await client.get(`/game/adventures/${adventureId}`, {
    headers: { "X-Custom-Authorization": `Bearer ${token}` },
  });
  return response.data;
}

/** Creates a play session and returns its opening narrative (008-core-gameplay-done,
 * contracts/api.md) — supersedes the retired `startGame`/`POST /game/start`. */
export async function createSession(token, { adventureId, characterName, characterType }) {
  const response = await client.post(
    "/game/sessions",
    { adventureId, characterName, characterType },
    { headers: { "X-Custom-Authorization": `Bearer ${token}` } },
  );
  return response.data;
}

/** Submits one free-text action and returns the resulting turn (or the session's
 * concluded/rate-limited/lockout/in-progress state via the thrown axios error's
 * `response.status`). */
export async function submitInteraction(token, sessionId, input) {
  const response = await client.post(
    `/game/sessions/${sessionId}/interactions`,
    { input },
    { headers: { "X-Custom-Authorization": `Bearer ${token}` } },
  );
  return response.data;
}

/** Reactivates one of the player's own, non-concluded sessions (FR-015). */
export async function resumeSession(token, sessionId) {
  const response = await client.post(
    `/game/sessions/${sessionId}/resume`,
    {},
    { headers: { "X-Custom-Authorization": `Bearer ${token}` } },
  );
  return response.data;
}

/** Lists the caller's own in-progress games, newest activity first
 * (009-save-and-continue, contracts/api.md). */
export async function listSavedGames(token) {
  const response = await client.get("/game/sessions", {
    headers: { "X-Custom-Authorization": `Bearer ${token}` },
  });
  return response.data;
}

/** Returns one of the caller's own sessions in full, including every turn, so the play
 * surface can be rebuilt exactly as it was left (FR-006). */
export async function getSession(token, sessionId) {
  const response = await client.get(`/game/sessions/${sessionId}`, {
    headers: { "X-Custom-Authorization": `Bearer ${token}` },
  });
  return response.data;
}

/** Records a labelled, timestamped checkpoint marker on the caller's session
 * (FR-003, FR-005). The label is always generated server-side. */
export async function saveCheckpoint(token, sessionId) {
  const response = await client.post(
    `/game/sessions/${sessionId}/checkpoints`,
    {},
    { headers: { "X-Custom-Authorization": `Bearer ${token}` } },
  );
  return response.data;
}

export default {
  listAdventures,
  getAdventure,
  createSession,
  submitInteraction,
  resumeSession,
  listSavedGames,
  getSession,
  saveCheckpoint,
};
