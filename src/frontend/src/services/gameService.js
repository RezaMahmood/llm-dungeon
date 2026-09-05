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

export async function startGame(token, { adventureId, characterName, characterType }) {
  const response = await client.post(
    "/game/start",
    { adventureId, characterName, characterType },
    { headers: { "X-Custom-Authorization": `Bearer ${token}` } },
  );
  return response.data;
}

export default { listAdventures, getAdventure, startGame };
