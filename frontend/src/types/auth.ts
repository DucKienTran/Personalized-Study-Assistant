export interface UserRegister {
  email: string;
  password: string;
  confirm_password: string;
  full_name?: string | null;
}

export interface UserLogin {
  email: string;
  password: string;
  remember_me: boolean;
}

export interface VerifyEmailRequest {
  token: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
  confirm_new_password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}