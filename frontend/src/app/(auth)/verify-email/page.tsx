"use client";

import React, { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";

import { authService } from "@/services/auth.service";
import { AUTH_ROUTES } from "@/constants/auth";

import { AuthShell } from "@/components/auth/AuthShell";
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
    <Card className="w-full border border-border bg-card text-center shadow-[0_24px_70px_-38px_var(--primary-shadow)] ring-0">
      <CardHeader className="space-y-2 border-b border-border pb-6">
        <p className="text-xs font-semibold tracking-[0.16em] text-accent uppercase">
          Account verification
        </p>
        <CardTitle className="font-heading text-3xl font-medium tracking-tight text-foreground">
          Verify your email
        </CardTitle>
        <p className="text-sm text-muted-foreground">Confirming your account securely.</p>
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
              <h2 className="font-heading text-2xl font-medium text-foreground">Email verified</h2>
              <p className="text-sm leading-relaxed text-muted-foreground">
                Your account is now active. Redirecting to login in{" "}
                <span className="font-semibold text-primary">{countdown}s</span>...
              </p>
            </div>

            <Button size="lg" className="h-12 w-full rounded-lg hover:bg-[var(--primary-hover)]" onClick={() => router.push(AUTH_ROUTES?.LOGIN || "/login")}>
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
              <h2 className="font-heading text-2xl font-medium text-foreground">Verification failed</h2>
              <p className="text-sm leading-relaxed text-muted-foreground">{errorMessage}</p>
            </div>

            <Button
              size="lg"
              className="h-12 w-full rounded-lg hover:bg-[var(--primary-hover)]"
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
    <AuthShell>
        <Suspense
          fallback={
            <Card className="w-full border border-border bg-card p-8 text-center ring-0">
              <ProgressActivityIcon size={32} className="mx-auto animate-spin text-primary" />
              <p className="mt-4 text-sm text-muted-foreground">Loading...</p>
            </Card>
          }
        >
          <VerifyEmailContent />
        </Suspense>
    </AuthShell>
  );
}
