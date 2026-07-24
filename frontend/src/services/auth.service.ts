import api from "./api";
import {
  ForgotPasswordRequest,
  MessageResponse,
  ResetPasswordRequest,
  TokenResponse,
  UserLogin,
  UserRegister,
  VerifyEmailRequest,
} from "@/types";

export class AuthService {
  async register(data: UserRegister): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>("/auth/register", data);
    return response.data;
  }

  async verifyEmail(data: VerifyEmailRequest): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>("/auth/verify-email", data);
    return response.data;
  }

  async forgotPassword(data: ForgotPasswordRequest): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>("/auth/forgot-password", data);
    return response.data;
  }

  async resetPassword(data: ResetPasswordRequest): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>("/auth/reset-password", data);
    return response.data;
  }

  async login(data: UserLogin): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>("/auth/login", data);
    return response.data;
  }

  async refreshToken(): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>("/auth/token/refresh");
    return response.data;
  }

  async logout(): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>("/auth/logout");
    return response.data;
  }
}

export const authService = new AuthService();