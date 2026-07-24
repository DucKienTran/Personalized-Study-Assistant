"use client";

import React, { useState } from "react";
import Link from "next/link";
import { authService } from "@/services/auth.service";
import { APP_CONFIG } from "@/constants/app";
import { AUTH_ROUTES } from "@/constants/auth";
import { UserRegister } from "@/types";

interface ValidationErrorItem {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
}

interface ApiErrorResponse {
  response?: {
    status?: number;
    data?: {
      detail?: string | ValidationErrorItem[];
    };
  };
}

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const parseErrorMessage = (err: unknown): string => {
    if (typeof err === "object" && err !== null) {
      const apiErr = err as ApiErrorResponse;
      const detail = apiErr.response?.data?.detail;

      // Handle standard string error response (e.g. 400 Bad Request, 409 Conflict)
      if (typeof detail === "string") {
        return detail;
      }

      // Handle FastAPI 422 Unprocessable Entity array
      if (Array.isArray(detail) && detail.length > 0) {
        const firstErr = detail[0];
        if (firstErr?.msg) {
          // Extract field name from loc array (e.g., ["body", "email"] -> "email")
          const fieldName = firstErr.loc?.[1] ? `${firstErr.loc[1]}: ` : "";
          return `${fieldName}${firstErr.msg}`;
        }
      }
    }
    return "Registration failed. Please check your information and try again.";
  };

  const validateForm = (): boolean => {
    // 1. Email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      setError("email: Please enter a valid email address.");
      return false;
    }

    // 2. Password strength validation
    if (password.length < 8) {
      setError("password: Must be at least 8 characters long.");
      return false;
    }

    const hasLetter = /[a-zA-Z]/.test(password);
    const hasNumber = /[0-9]/.test(password);
    if (!hasLetter || !hasNumber) {
      setError("password: Must contain at least one letter and one number.");
      return false;
    }

    // 3. Confirm password match
    if (password !== confirmPassword) {
      setError("confirm_password: Passwords do not match!");
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (loading) return;
    setError("");

    if (!validateForm()) return;

    setLoading(true);

    try {
      const payload: UserRegister = {
        email: email.trim(),
        password: password,
        confirm_password: confirmPassword,
        full_name: fullName.trim() || null,
      };

      await authService.register(payload);
      setIsSuccess(true);
    } catch (err: unknown) {
      setError(parseErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  // Success state view
  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#faf5ff] p-4 select-none">
        <div className="w-full max-w-md bg-white rounded-3xl shadow-xl p-8 border border-[#f3e8ff] text-center space-y-6 animate-fade-in">
          <div className="w-16 h-16 bg-[#f3e8ff] text-[#7c3aed] rounded-full flex items-center justify-center mx-auto text-2xl font-bold">
            ✓
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-[#581c87]">
              Registration Successful
            </h1>
            <p className="text-[15px] text-[#6b21a8] leading-relaxed font-medium">
              Please check your email to verify your account.
            </p>
          </div>

          <div className="pt-2">
            <Link
              href={AUTH_ROUTES?.LOGIN || "/login"}
              className="inline-block w-full py-2.5 bg-[#7c3aed] hover:bg-[#6d28d9] text-white text-[14px] font-semibold rounded-full shadow-sm transition-colors duration-150"
            >
              Go to Login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#faf5ff] p-4 select-none">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl p-8 border border-[#f3e8ff]">
        
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-[#581c87] mb-2">
            {APP_CONFIG.NAME}
          </h1>
          <p className="text-sm text-[#7e22ce]">Create your new account</p>
        </div>

        {/* Error Banner with Field Prefix support */}
        {error && (
          <div
            role="alert"
            className="p-3 mb-5 text-[13px] font-medium text-[#991b1b] bg-[#fef2f2] border border-[#fca5a5] rounded-lg text-center animate-fade-in capitalize-first"
          >
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="relative border-b border-[#e9d5ff] focus-within:border-[#7c3aed] transition-colors duration-200 pb-1.5">
            <label className="block text-[13px] font-medium text-[#6b21a8] mb-1">
              Full Name (Optional)
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full bg-transparent text-[15px] text-black focus:outline-none placeholder-[#d8b4fe]"
              placeholder="John Doe"
              autoComplete="name"
            />
          </div>

          <div className="relative border-b border-[#e9d5ff] focus-within:border-[#7c3aed] transition-colors duration-200 pb-1.5">
            <label className="block text-[13px] font-medium text-[#6b21a8] mb-1">
              Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-transparent text-[15px] text-black focus:outline-none placeholder-[#d8b4fe]"
              placeholder="name@example.com"
              autoComplete="email"
            />
          </div>

          <div className="relative border-b border-[#e9d5ff] focus-within:border-[#7c3aed] transition-colors duration-200 pb-1.5">
            <label className="block text-[13px] font-medium text-[#6b21a8] mb-1">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-transparent text-[15px] text-black focus:outline-none placeholder-[#d8b4fe]"
              placeholder="Min. 8 chars, letter & number"
              autoComplete="new-password"
            />
          </div>

          <div className="relative border-b border-[#e9d5ff] focus-within:border-[#7c3aed] transition-colors duration-200 pb-1.5">
            <label className="block text-[13px] font-medium text-[#6b21a8] mb-1">
              Confirm password
            </label>
            <input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full bg-transparent text-[15px] text-black focus:outline-none placeholder-[#d8b4fe]"
              placeholder="••••••••"
              autoComplete="new-password"
            />
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-[#7c3aed] hover:bg-[#6d28d9] text-white text-[14px] font-semibold rounded-full shadow-sm transition-colors duration-150 disabled:bg-[#cbd5e1] disabled:cursor-not-allowed"
            >
              {loading ? "Processing..." : "Register"}
            </button>
          </div>
        </form>

        {/* Footer Link */}
        <div className="text-center mt-6 text-[13px] text-[#6b21a8]">
          Already have an account?{" "}
          <Link
            href={AUTH_ROUTES?.LOGIN || "/login"}
            className="font-semibold text-[#7c3aed] hover:underline"
          >
            Log in now
          </Link>
        </div>

      </div>
    </div>
  );
}