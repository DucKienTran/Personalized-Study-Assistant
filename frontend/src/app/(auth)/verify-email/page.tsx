"use client";

import React, { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";

import { authService } from "@/services/auth.service";
import { APP_CONFIG } from "@/constants/app";
import { AUTH_ROUTES } from "@/constants/auth";

import { AuthBackgroundPattern } from "@/components/auth/AuthBackgroundPattern";
import {
  CheckCircleIcon,
  CancelIcon,
  ProgressActivityIcon,
} from "@/components/shared/icons";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

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
    <Card className="w-full max-w-md border-border bg-card/95 shadow-sm text-center">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold tracking-tight text-foreground">
          {APP_CONFIG.NAME}
        </CardTitle>
        <p className="text-sm text-muted-foreground">Account verification</p>
      </CardHeader>

      <CardContent>
        {status === "verifying" && (
          <div className="space-y-4 py-4">
            <ProgressActivityIcon size={40} className="mx-auto animate-spin text-primary" />
            <p className="text-sm font-medium text-muted-foreground">
              Verifying your email address...
            </p>
          </div>
        )}

        {status === "success" && (
          <div className="space-y-6 py-2">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
              <CheckCircleIcon size={32} />
            </div>

            <div className="space-y-2">
              <h2 className="text-xl font-bold text-foreground">Email Verified!</h2>
              <p className="text-sm leading-relaxed text-muted-foreground">
                Your account is now active. Redirecting to login in{" "}
                <span className="font-semibold text-primary">{countdown}s</span>...
              </p>
            </div>

            <Button size="lg" className="h-11 w-full" onClick={() => router.push(AUTH_ROUTES?.LOGIN || "/login")}>
              Go to login now
            </Button>
          </div>
        )}

        {status === "error" && (
          <div className="space-y-6 py-2">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <CancelIcon size={32} />
            </div>

            <div className="space-y-2">
              <h2 className="text-xl font-bold text-foreground">Verification Failed</h2>
              <p className="text-sm leading-relaxed text-muted-foreground">{errorMessage}</p>
            </div>

            <Button
              size="lg"
              className="h-11 w-full"
              render={<Link href={AUTH_ROUTES?.LOGIN || "/login"} />}
            >
              Back to login
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function VerifyEmailPage() {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4 py-8">
      <AuthBackgroundPattern />

      <div className="relative z-10 w-full max-w-md">
        <Suspense
          fallback={
            <Card className="w-full max-w-md border-border bg-card/95 shadow-sm p-8 text-center">
              <ProgressActivityIcon size={32} className="mx-auto animate-spin text-primary" />
              <p className="mt-4 text-sm text-muted-foreground">Loading...</p>
            </Card>
          }
        >
          <VerifyEmailContent />
        </Suspense>
      </div>
    </main>
  );
}