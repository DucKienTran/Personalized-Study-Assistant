export const AUTH_CONFIG = {
  COOKIE_NAME: "refresh_token",
  COOKIE_MAX_AGE: 7 * 24 * 60 * 60, //Tính bằng giây
};

export const AUTH_ROUTES = {
  LOGIN: "/login",
  REGISTER: "/register",
  VERIFY_EMAIL: "/verify-email",
  FORGOT_PASSWORD: "/forgot-password",
  RESET_PASSWORD: "/reset-password",
} as const;

export const TOKEN_KEY = "access_token";

export const AUTH_EXCLUDED_ENDPOINTS = [
  "/auth/login",
  "/auth/token/refresh",
  "/auth/logout",
  "/auth/register",
  "/auth/verify-email",
  "/auth/forgot-password",
  "/auth/reset-password",
] as const;