import api from "./api";
import { MessageResponse, UserResponse } from "@/types";

class UserService {
  /**
   * Get the currently authenticated user.
   */
  async getCurrentUser(): Promise<UserResponse> {
    const response = await api.get<UserResponse>("/users/me");
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