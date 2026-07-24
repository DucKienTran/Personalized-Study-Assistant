"use client";

import React, { createContext, useCallback, useEffect, useState } from "react";
import { authService } from "@/services/auth.service";
import { userService } from "@/services/user.service";
import { tokenStorage } from "@/services/api";
import { CurrentUser, UserLogin } from "@/types";

export interface AuthContextType {
  currentUser: CurrentUser | null;
  authenticated: boolean;
  loading: boolean;
  login: (credentials: UserLogin) => Promise<void>;
  logout: () => Promise<void>;
  reloadCurrentUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchCurrentUser = useCallback(async (): Promise<CurrentUser> => {
    const user = await userService.getCurrentUser();
    setCurrentUser(user);
    return user;
  }, []);

  const initializeAuth = useCallback(async () => {
    setLoading(true);

    // 1. Try fetching current user with existing access token
    const token = tokenStorage.get();
    if (token) {
      try {
        await fetchCurrentUser();
        setLoading(false);
        return;
      } catch {
        // Access token in storage is invalid/expired, fall through to refresh attempt
      }
    }

    // 2. Attempt session restoration using HttpOnly refresh cookie
    try {
      const response = await authService.refreshToken();
      tokenStorage.set(response.access_token);
      await fetchCurrentUser();
    } catch {
      // Refresh failed or no session cookie exists -> clear state
      tokenStorage.clear();
      setCurrentUser(null);
    } finally {
      setLoading(false);
    }
  }, [fetchCurrentUser]);

  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  const login = async (credentials: UserLogin): Promise<void> => {
    const response = await authService.login(credentials);
    tokenStorage.set(response.access_token);

    try {
      await fetchCurrentUser();
    } catch (error) {
      tokenStorage.clear();
      setCurrentUser(null);
      throw error;
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await authService.logout();
    } catch {
      // Gracefully clear token even if server logout request fails
    } finally {
      tokenStorage.clear();
      setCurrentUser(null);
    }
  };

  const reloadCurrentUser = async (): Promise<void> => {
    if (tokenStorage.get()) {
      try {
        await fetchCurrentUser();
      } catch {
        // Graceful handling for explicit profile reload attempts
      }
    }
  };

  const value: AuthContextType = {
    currentUser,
    authenticated: Boolean(currentUser),
    loading,
    login,
    logout,
    reloadCurrentUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};