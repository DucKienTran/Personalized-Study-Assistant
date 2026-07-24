export interface UserResponse {
  id: number;
  email: string;
  role_name: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface CurrentUser {
  id: number;
  email: string;
  role: string;
  permissions: string[];
}

export interface UserStatus {
  user_id: number;
  email: string;
  role: string;
  status: string;
  message: string;
  last_active?: number | null;
}

export interface ChangePassword {
  old_password: string;
  new_password: string;
  confirm_new_password: string;
}