import axios from "axios";

const client = axios.create({
  baseURL: "/api",
});

export async function login(token) {
  const response = await client.post(
    "/auth/login",
    {},
    { headers: { "X-Custom-Authorization": `Bearer ${token}` } },
  );
  return response.data;
}

export async function getMe(token) {
  const response = await client.get("/auth/me", {
    headers: { "X-Custom-Authorization": `Bearer ${token}` },
  });
  return response.data;
}

export async function logout(token) {
  const response = await client.post(
    "/auth/logout",
    {},
    { headers: { "X-Custom-Authorization": `Bearer ${token}` } },
  );
  return response.data;
}

export default { login, getMe, logout };
