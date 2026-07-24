"use client";

import React, { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { authService } from "@/services/auth.service";
import { APP_CONFIG } from "@/constants/app";
import { AUTH_ROUTES } from "@/constants/auth";

interface ValidationErrorItem {
  loc?: (string | number)[];
  msg?: string;
}

interface ApiErrorResponse {
  response?: {
    status?: number;
    data?: {
      detail?: string | ValidationErrorItem[];
    };
  };
}

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"verifying" | "success" | "error">("verifying");
  const [errorMessage, setErrorMessage] = useState("");
  const [countdown, setCountdown] = useState(5);
  
  // Prevent duplicate API execution in React 18 Strict Mode
  const verificationAttempted = useRef(false);

  const parseErrorMessage = (err: unknown): string => {
    if (typeof err === "object" && err !== null) {
      const apiErr = err as ApiErrorResponse;
      const detail = apiErr.response?.data?.detail;

      if (typeof detail === "string") {
        return detail;
      }

      if (Array.isArray(detail) && detail.length > 0) {
        const firstErr = detail[0];
        if (firstErr?.msg) {
          const fieldName = firstErr.loc?.[1] ? `${firstErr.loc[1]}: ` : "";
          return `${fieldName}${firstErr.msg}`;
        }
      }
    }
    return "Failed to verify email. The link may be invalid or expired.";
  };

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setErrorMessage("Verification token is missing from the link.");
      return;
    }

    if (verificationAttempted.current) return;
    verificationAttempted.current = true;

    const executeVerification = async () => {
      try {
        await authService.verifyEmail({ token });
        setStatus("success");
      } catch (err: unknown) {
        setStatus("error");
        setErrorMessage(parseErrorMessage(err));
      }
    };

    executeVerification();
  }, [token]);

  // Countdown and Auto-redirect on success
  useEffect(() => {
    if (status !== "success") return;

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          router.push(AUTH_ROUTES?.LOGIN || "/login");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [status, router]);

  return (
    <div className="w-full max-w-md bg-white rounded-3xl shadow-xl p-8 border border-[#f3e8ff] text-center select-none">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-[#581c87] mb-2">{APP_CONFIG.NAME}</h1>
        <p className="text-sm text-[#7e22ce]">Account Verification</p>
      </div>

      {/* State 1: Verifying */}
      {status === "verifying" && (
        <div className="py-8 space-y-4">
          <div className="w-12 h-12 border-4 border-[#e9d5ff] border-t-[#7c3aed] rounded-full animate-spin mx-auto" />
          <p className="text-[15px] font-medium text-[#6b21a8]">
            Verifying your email address...
          </p>
        </div>
      )}

      {/* State 2: Success */}
      {status === "success" && (
        <div className="py-4 space-y-6 animate-fade-in">
          <div className="w-16 h-16 bg-[#f3e8ff] text-[#7c3aed] rounded-full flex items-center justify-center mx-auto text-3xl font-bold">
            ✓
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-[#581c87]">Email Verified!</h2>
            <p className="text-[14px] text-[#6b21a8] font-medium leading-relaxed">
              Your account is now active. Redirecting to login in{" "}
              <span className="font-bold text-[#7c3aed]">{countdown}s</span>...
            </p>
          </div>

          <div className="pt-2">
            <button
              onClick={() => router.push(AUTH_ROUTES?.LOGIN || "/login")}
              className="w-full py-2.5 bg-[#7c3aed] hover:bg-[#6d28d9] text-white text-[14px] font-semibold rounded-full shadow-sm transition-colors duration-150"
            >
              Go to Login Now
            </button>
          </div>
        </div>
      )}

      {/* State 3: Error */}
      {status === "error" && (
        <div className="py-4 space-y-6 animate-fade-in">
          <div className="w-16 h-16 bg-[#fef2f2] text-[#dc2626] rounded-full flex items-center justify-center mx-auto text-2xl font-bold">
            ✕
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-[#991b1b]">Verification Failed</h2>
            <p className="text-[14px] text-[#7f1d1d] font-medium leading-relaxed">
              {errorMessage}
            </p>
          </div>

          <div className="pt-2 space-y-3">
            <Link
              href={AUTH_ROUTES?.LOGIN || "/login"}
              className="block w-full py-2.5 bg-[#7c3aed] hover:bg-[#6d28d9] text-white text-[14px] font-semibold rounded-full shadow-sm transition-colors duration-150"
            >
              Back to Login
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#faf5ff] p-4">
      <Suspense
        fallback={
          <div className="w-full max-w-md bg-white rounded-3xl shadow-xl p-8 border border-[#f3e8ff] text-center">
            <div className="w-10 h-10 border-4 border-[#e9d5ff] border-t-[#7c3aed] rounded-full animate-spin mx-auto mb-4" />
            <p className="text-sm text-[#6b21a8] font-medium">Loading...</p>
          </div>
        }
      >
        <VerifyEmailContent />
      </Suspense>
    </div>
  );
}