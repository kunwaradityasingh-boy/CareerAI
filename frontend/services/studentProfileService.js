import api from "./api";

export async function getStudentProfile(token) {
  const response = await api.get("/api/v1/students/me/profile", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.data;
}

export async function saveStudentProfile(token, profileData) {
  const response = await api.put("/api/v1/students/me/profile", profileData, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.data;
}
