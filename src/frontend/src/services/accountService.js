import axios from "axios";

const client = axios.create({
  baseURL: "/api",
});

export async function addAccount(token, email, roles) {
  const response = await client.post(
    "/admin/accounts",
    { email, roles },
    { headers: { Authorization: `Bearer ${token}` } },
  );
  return response.data;
}

export async function listAccounts(token) {
  const response = await client.get("/admin/accounts", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
}

export default { addAccount, listAccounts };
