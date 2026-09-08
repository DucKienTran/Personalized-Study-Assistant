import api from "./api";
import {
  MessageResponse,
  UserRegister,
  UserResponse,
  UserStatus,
} from "@/types";

class UserService {
  /**
   * Get the currently authenticated user.
   */
  async getCurrentUser(): Promise<UserResponse> {
    const response = await api.get<UserResponse>("/users/me");
    return response.data;
  }

  async getAllUsers(): Promise<UserResponse[]> {
    const response = await api.get<UserResponse[]>("/users/all");
    return response.data;
  }

  async getAllUserStatuses(): Promise<UserStatus[]> {
    const response = await api.get<UserStatus[]>("/users/get-status");
    return response.data;
  }

  async createAdmin(data: UserRegister): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>("/users/admin", data);
    return response.data;
  }

  /**
   * Change the authenticated user's password.
   */
  async changePassword(payload: {
    old_password: string;
    new_password: string;
    confirm_new_password: string;
  }): Promise<MessageResponse> {
    const response = await api.put<MessageResponse>(
      "/users/change-password",
      payload
    );
    return response.data;
  }
}

export const userService = new UserService();