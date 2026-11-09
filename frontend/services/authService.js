import api from "./api";

export async function registerUser({ name, email, password }) {
  const response = await api.post("/api/v1/auth/register", {
    name,
    email,
    password,
  });

  return response.data;
}

export async function loginUser({ email, password }) {
  const formData = new URLSearchParams();

  formData.append("username", email);
  formData.append("password", password);

  const response = await api.post("/api/v1/auth/login", formData, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });

  return response.data;
}

export async function getCurrentUser(token) {
  const response = await api.get("/api/v1/auth/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.data;
}
