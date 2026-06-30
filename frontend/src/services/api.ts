import axios from "axios";

// Khởi tạo instance Axios kết nối sang API Backend
const api = axios.create({
  // Bổ sung thêm /api/v1 vào cuối baseURL để khớp với backend FastAPI
  baseURL: (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") + "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

// Tự động đính kèm Token vào Header của request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export default api;