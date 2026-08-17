"use client";

import React, { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";
import { AUTH_ROUTES } from "@/constants/auth";
import RedirectLoading from "@/components/states/RedirectLoading";
import { AuthShell } from "@/components/auth/AuthShell";
import {
  ArrowForwardIcon,
  LockIcon,
  MailIcon,
  ProgressActivityIcon,
  WarningIcon,
} from "@/components/shared/icons";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

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
    if (typeof detail === "string") return detail;

    if (Array.isArray(detail) && detail.length > 0) {
      const firstError = detail[0];
      if (firstError?.msg) {
        const field = firstError.loc?.[1] != null ? `${String(firstError.loc[1])}: ` : "";
        return `${field}${firstError.msg}`;
      }
    }

    switch (apiError.response.status) {
      case 401:
        return "Invalid email or password.";
      case 422:
        return "Validation failed. Please verify your input.";
      case 429:
        return "Too many login attempts. Please try again later.";
      case 500:
        return "Internal server error. Please try again later.";
      default:
        return "Login failed. Please try again.";
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
      setTimeout(() => router.replace(redirectTarget), 600);
    } catch (err) {
      setError(parseErrorMessage(err));
      setLoading(false);
    }
  };

  if (showRedirectLoading) {
    return <RedirectLoading message="Login successful! Entering the system..." />;
  }

  return (
    <AuthShell>
      <Card className="border border-border bg-card shadow-[0_24px_70px_-38px_var(--primary-shadow)] ring-0">
        <CardHeader className="space-y-3 border-b border-border pb-6 text-center sm:text-left">
          <p className="text-xs font-semibold tracking-[0.16em] text-accent uppercase">
            Your learning desk
          </p>
          <CardTitle className="font-heading text-3xl font-medium tracking-tight sm:text-4xl">
            Welcome back
          </CardTitle>
          <CardDescription className="leading-6">
            Sign in to continue where you left off.
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-1">
          {error && (
            <Alert variant="destructive" className="mb-6 bg-destructive/5">
              <WarningIcon size={18} />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="email">Email address</Label>
              <div className="relative">
                <MailIcon size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="user@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-12 rounded-lg bg-background/60 pl-10"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link
                  href={AUTH_ROUTES.FORGOT_PASSWORD}
                  className="text-sm font-medium text-primary underline-offset-4 hover:text-[var(--primary-hover)] hover:underline"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <LockIcon size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-12 rounded-lg bg-background/60 pl-10"
                  required
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Checkbox
                id="remember-me"
                checked={rememberMe}
                onCheckedChange={(checked) => setRememberMe(Boolean(checked))}
              />
              <Label htmlFor="remember-me" className="cursor-pointer font-normal text-muted-foreground">
                Remember me
              </Label>
            </div>

            <Button type="submit" size="lg" className="h-12 w-full gap-2 rounded-lg hover:bg-[var(--primary-hover)]" disabled={loading}>
              {loading ? (
                <>
                  <ProgressActivityIcon size={18} className="animate-spin" />
                  <span>Signing in...</span>
                </>
              ) : (
                <>
                  <span>Log in</span>
                  <ArrowForwardIcon size={18} />
                </>
              )}
            </Button>
          </form>

          <div className="mt-7 border-t border-border pt-6 text-center text-sm text-muted-foreground">
            New to LearningAid?{" "}
            <Link href={AUTH_ROUTES.REGISTER} className="font-semibold text-primary underline-offset-4 hover:text-[var(--primary-hover)] hover:underline">
              Create account
            </Link>
          </div>
        </CardContent>
      </Card>
    </AuthShell>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<RedirectLoading message="Loading..." />}>
      <LoginForm />
    </Suspense>
  );
}
