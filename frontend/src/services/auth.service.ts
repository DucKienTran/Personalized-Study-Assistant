import api from "./api";

export const authService = {
  // Login api
  login: async (email: string, password: string) => {
    const response = await api.post("/auth/login", {
      email,
      password,
    });
    return response.data;
  },
  
  // Logout api
  logout: async () => {
    try {
      const response = await api.post("/auth/logout");
      return response.data;
    } finally {
      // Luôn xoá local storage dù API thành công hay lỗi
      localStorage.removeItem("access_token");
    }
  },

  // Register
  register: async (data: any) => {
    const response = await api.post("/auth/register", data);
    return response.data;
  },

  // Register admin
  registerAdmin: async (data: any, adminKey: string) => {
    const url = `/auth/register-admin?admin_key=${encodeURIComponent(adminKey)}`;
    const response = await api.post(url, data);
    return response.data;
  }
};