import axios from "axios";

const client = axios.create({
  baseURL: "/api",
});

export async function listSessions(token) {
  const response = await client.get("/manage/sessions", {
    headers: { "X-Custom-Authorization": `Bearer ${token}` },
  });
  return response.data;
}

export async function deleteSession(token, sessionId) {
  const response = await client.delete(`/manage/sessions/${sessionId}`, {
    headers: { "X-Custom-Authorization": `Bearer ${token}` },
  });
  return response.data;
}

export default { listSessions, deleteSession };
