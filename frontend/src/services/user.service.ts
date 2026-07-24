import api from "./api";
import { CurrentUser } from "@/types";

class UserService {
  /**
   * Get the currently authenticated user.
   */
  async getCurrentUser(): Promise<CurrentUser> {
    const response = await api.get<CurrentUser>("/users/me");
    return response.data;
  }
}

export const userService = new UserService();