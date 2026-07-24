// src/app/login/page.tsx
"use client";

import React, { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import RedirectLoading from "@/components/states/RedirectLoading";
import {AuthBackgroundPattern} from "@/components/auth/AuthBackgroundPattern";
import {
  MailIcon,
  LockIcon,
  WarningIcon,
  ProgressActivityIcon,
  ArrowForwardIcon,
} from "@/components/shared/icons";
import { APP_CONFIG } from "@/constants/app";
import { AUTH_ROUTES } from "@/constants/auth";

interface ValidationErrorItem {
  msg?: string;
  loc?: (string | number)[];
}

interface ApiErrorResponse {
  response?: {
    status?: number;
    data?: {
      detail?: string | ValidationErrorItem[];
    };
  };
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showRedirectLoading, setShowRedirectLoading] = useState(false);

  // Target URL after successful authentication
  const redirectTarget = searchParams.get("redirect") || "/";

  const parseErrorMessage = (err: unknown): string => {
    if (typeof err !== "object" || err === null) {
      return "An unexpected error occurred. Please try again.";
    }

    const apiError = err as ApiErrorResponse;

    if (!apiError.response) {
      return "Unable to connect to server. Please try again.";
    }

    const detail = apiError.response.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail) && detail.length > 0) {
      const firstError = detail[0];
      if (firstError?.msg) {
        const fieldName = firstError.loc?.[1] ? `${firstError.loc[1]}: ` : "";
        return `${fieldName}${firstError.msg}`;
      }
    }

    switch (apiError.response.status) {
      case 401:
        return "Invalid email or password.";
      case 422:
        return "Validation failed. Please verify your input format.";
      case 429:
        return "Too many login attempts. Please try again later.";
      case 500:
        return "Internal server error. Please try again later.";
      default:
        return "Login failed. Please check your credentials and try again.";
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (loading) return;

    setError("");
    setLoading(true);

    try {
      await login({
        email: email.trim(),
        password,
        remember_me: rememberMe,
      });

      setShowRedirectLoading(true);

      setTimeout(() => {
        router.replace(redirectTarget);
      }, 600);
    } catch (err: unknown) {
      setError(parseErrorMessage(err));
      setLoading(false);
    }
  };

  if (showRedirectLoading) {
    return <RedirectLoading message="Login successful! Entering the system..." />;
  }

  return (
    <div className="relative min-h-screen w-full overflow-hidden flex items-center justify-center bg-[#f2f7f4] font-sans p-4 select-none">
      {/* Decorative Auth Background Pattern */}
      <AuthBackgroundPattern />

      {/* Main Card Container */}
      <div className="relative z-10 w-full max-w-[420px] bg-white/95 backdrop-blur-md p-8 sm:p-10 rounded-2xl shadow-xl border border-[#d2ebd9]/80 transition-all duration-300">
        
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl sm:text-[28px] font-bold tracking-tight text-[#2e4a38] font-serif">
            {APP_CONFIG.NAME}
          </h1>
          <p className="text-xs sm:text-sm text-[#5c7a65] mt-1.5 font-medium">
            Welcome back! Please enter your details.
          </p>
        </div>

        {/* Centralized Error Alert Box */}
        {error && (
          <div
            role="alert"
            className="flex items-center gap-2 p-3.5 mb-6 text-xs sm:text-sm font-medium text-red-700 bg-red-50/90 border border-red-200 rounded-xl shadow-sm animate-fade-in"
          >
            <WarningIcon size={18} className="shrink-0 text-red-500" />
            <span className="leading-snug">{error}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Email Input */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-[#4a6351] mb-1.5">
              Email Address
            </label>
            <div className="relative flex items-center">
              <span className="absolute left-3.5 text-gray-400 flex items-center pointer-events-none">
                <MailIcon size={20} />
              </span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-[#f9fbf9] border border-[#cbdcd0] rounded-xl text-sm text-gray-900 placeholder-[#a3b8ab] focus:outline-none focus:border-[#428a5d] focus:ring-2 focus:ring-[#428a5d]/20 transition-all"
                placeholder="user@example.com"
                autoComplete="email"
              />
            </div>
          </div>

          {/* Password Input */}
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-[#4a6351]">
                Password
              </label>
              <Link
                href={AUTH_ROUTES.FORGOT_PASSWORD}
                className="text-xs font-medium text-[#428a5d] hover:text-[#2e5f3f] hover:underline focus:outline-none transition-colors"
              >
                Forgot password?
              </Link>
            </div>
            <div className="relative flex items-center">
              <span className="absolute left-3.5 text-gray-400 flex items-center pointer-events-none">
                <LockIcon size={20} />
              </span>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-[#f9fbf9] border border-[#cbdcd0] rounded-xl text-sm text-gray-900 placeholder-[#a3b8ab] focus:outline-none focus:border-[#428a5d] focus:ring-2 focus:ring-[#428a5d]/20 transition-all"
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </div>
          </div>

          {/* Remember Me Option */}
          <div className="flex items-center pt-0.5">
            <input
              id="remember-me"
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="w-4 h-4 text-[#3b7a52] bg-[#f9fbf9] border-[#cbdcd0] rounded focus:ring-[#428a5d] focus:ring-offset-0 cursor-pointer accent-[#3b7a52]"
            />
            <label
              htmlFor="remember-me"
              className="ml-2.5 text-xs sm:text-sm font-medium text-[#4a6351] cursor-pointer select-none"
            >
              Remember me
            </label>
          </div>

          {/* Submit Button */}
          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-[#3b7a52] hover:bg-[#2e5f3f] active:bg-[#244b32] text-white text-sm font-semibold rounded-xl shadow-md hover:shadow-lg transition-all duration-200 disabled:bg-[#cbd5e1] disabled:cursor-not-allowed disabled:shadow-none flex items-center justify-center gap-2 group focus:outline-none focus:ring-2 focus:ring-[#3b7a52] focus:ring-offset-1"
            >
              {loading ? (
                <>
                  <ProgressActivityIcon size={18} className="animate-spin" />
                  <span>Signing in...</span>
                </>
              ) : (
                <>
                  <span>Log In</span>
                  <ArrowForwardIcon size={18} className="transition-transform group-hover:translate-x-0.5" />
                </>
              )}
            </button>
          </div>
        </form>

        {/* Footer Link */}
        <div className="mt-8 text-center text-xs sm:text-sm text-[#6b8775]">
          New user?{" "}
          <Link
            href={AUTH_ROUTES.REGISTER}
            className="font-semibold text-[#3b7a52] hover:text-[#2e5f3f] hover:underline ml-1 transition-colors"
          >
            Create account
          </Link>
        </div>

      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<RedirectLoading message="Loading..." />}>
      <LoginForm />
    </Suspense>
  );
}