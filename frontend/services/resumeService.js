import api from "./api";

export async function analyzeResumeText(payload, token) {
  const response = await api.post("/api/v1/resume/analyze-text", payload, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data;
}

export async function uploadResumeFile(formData, token) {
  const response = await api.post("/api/v1/resume/upload", formData, {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}

export async function getResumeHistory(token) {
  const response = await api.get("/api/v1/resume/history", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data;
}

export async function getResumeAnalysis(analysisId, token) {
  const response = await api.get(`/api/v1/resume/${analysisId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data;
}

export async function deleteResumeAnalysis(analysisId, token) {
  const response = await api.delete(`/api/v1/resume/${analysisId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data;
}
