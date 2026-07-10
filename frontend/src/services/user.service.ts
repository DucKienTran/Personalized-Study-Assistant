import api from "./api";

// Interface giống với Schema UserResponse trong backend 
export interface UserProfile {
    id: number;
    email: string;
    role_name: string;
    full_name?: string | null;
    is_active: boolean;
    created_at: string;
    updated_at?: string | null;
}

export const userService = {
    getMe: async (): Promise<UserProfile> => {
        const response = await api.get("/users/me");
        return response.data;
    },
};