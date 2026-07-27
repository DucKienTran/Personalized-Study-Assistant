"use client";

import React, { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { authService } from "@/services/auth.service";
import { APP_CONFIG } from "@/constants/app";
import { AUTH_ROUTES } from "@/constants/auth";

import { AuthBackgroundPattern } from "@/components/auth/AuthBackgroundPattern";
import {
  LockIcon,
  WarningIcon,
  CheckCircleIcon,
  ProgressActivityIcon,
  ArrowForwardIcon,
} from "@/components/shared/icons";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";

interface ApiErrorResponse {
  response?: {
    data?: {
      detail?: string;
    };
  };
}

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const parseErrorMessage = (err: unknown): string => {
    if (typeof err === "object" && err !== null) {
      const apiErr = err as ApiErrorResponse;
      const detail = apiErr.response?.data?.detail;
      if (typeof detail === "string") return detail;
    }
    return "Failed to reset password. The link may be invalid or expired.";
  };

  const validate = (): boolean => {
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

    if (password !== confirmPassword) {
      setError("confirm_password: Passwords do not match.");
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (loading) return;

    setError("");

    if (!token) {
      setError("Reset token is missing from the link.");
      return;
    }

    if (!validate()) return;

    setLoading(true);

    try {
      await authService.resetPassword({
        token,
        new_password: password,
        confirm_new_password: confirmPassword,
      });
      setIsSuccess(true);
    } catch (err) {
      setError(parseErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <Card className="w-full max-w-md border-border bg-card/95 shadow-sm text-center">
        <CardHeader className="space-y-3">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10 text-destructive">
            <WarningIcon size={32} />
          </div>
          <CardTitle className="text-2xl font-bold text-foreground">Invalid link</CardTitle>
          <CardDescription className="text-sm leading-relaxed text-muted-foreground">
            This password reset link is missing or invalid. Request a new one.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <Button
            size="lg"
            className="h-11 w-full"
            render={<Link href={AUTH_ROUTES.FORGOT_PASSWORD} />}
          >
            Request new link
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (isSuccess) {
    return (
      <Card className="w-full max-w-md border-border bg-card/95 shadow-sm text-center">
        <CardHeader className="space-y-3">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
            <CheckCircleIcon size={32} />
          </div>
          <CardTitle className="text-2xl font-bold text-foreground">Password updated</CardTitle>
          <CardDescription className="text-sm leading-relaxed text-muted-foreground">
            Your password has been reset. You can now log in with your new password.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <Button
            size="lg"
            className="h-11 w-full"
            render={<Link href={AUTH_ROUTES.LOGIN} />}
          >
            Go to login
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md border-border bg-card/95 shadow-sm backdrop-blur-md transition-shadow duration-200 hover:shadow-md">
      <CardHeader className="space-y-3 text-center">
        <CardTitle className="text-balance text-3xl font-bold tracking-tight text-foreground">
          {APP_CONFIG.NAME}
        </CardTitle>
        <CardDescription className="text-sm leading-relaxed text-muted-foreground">
          Choose a new password for your account.
        </CardDescription>
      </CardHeader>

      <CardContent>
        {error && (
          <div
            role="alert"
            className="mb-6 flex items-start gap-3 rounded-xl border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive"
          >
            <WarningIcon size={18} className="mt-0.5 shrink-0" />
            <span className="leading-relaxed">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="password">New password</Label>
            <div className="relative">
              <LockIcon
                size={18}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                placeholder="Minimum 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-11 pl-10"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirm-password">Confirm new password</Label>
            <div className="relative">
              <LockIcon
                size={18}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <Input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                placeholder="Repeat your new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="h-11 pl-10"
                required
              />
            </div>
          </div>

          <Button type="submit" size="lg" className="h-11 w-full gap-2" disabled={loading}>
            {loading ? (
              <>
                <ProgressActivityIcon size={18} className="animate-spin" />
                <span>Updating...</span>
              </>
            ) : (
              <>
                <span>Reset password</span>
                <ArrowForwardIcon size={18} className="transition-transform duration-200 group-hover/button:translate-x-1" />
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default function ResetPasswordPage() {
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
          <ResetPasswordForm />
        </Suspense>
      </div>
    </main>
  );
}