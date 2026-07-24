"use client";

import { useContext } from "react";
import { AuthContext, AuthContextType } from "@/contexts/AuthContext";

/**
 * Custom hook to consume the AuthContext.
 * Ensures the hook is used inside an AuthProvider component tree.
 */
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  return context;
};