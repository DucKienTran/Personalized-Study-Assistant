// src/app/login/page.tsx
"use client";

import React, { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";

import RedirectLoading from "@/components/states/RedirectLoading";
import { AuthBackgroundPattern } from "@/components/auth/AuthBackgroundPattern";

import {
  MailIcon,
  LockIcon,
  WarningIcon,
  ProgressActivityIcon,
  ArrowForwardIcon,
} from "@/components/shared/icons";

import { APP_CONFIG } from "@/constants/app";
import { AUTH_ROUTES } from "@/constants/auth";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";

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

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail) && detail.length > 0) {
      const firstError = detail[0];

      if (firstError?.msg) {
        const field =
          firstError.loc?.[1] != null
            ? `${String(firstError.loc[1])}: `
            : "";

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

  const handleSubmit = async (
    e: React.FormEvent<HTMLFormElement>
  ) => {
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
    } catch (err) {
      setError(parseErrorMessage(err));
      setLoading(false);
    }
  };

  if (showRedirectLoading) {
    return (
      <RedirectLoading message="Login successful! Entering the system..." />
    );
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4 py-8">

      <AuthBackgroundPattern />

      <div className="relative z-10 w-full max-w-md">

        <Card className="border-border bg-card/95 shadow-sm backdrop-blur-md transition-shadow duration-200 hover:shadow-md">

          <CardHeader className="space-y-3 text-center">

            <CardTitle className="text-balance text-3xl font-bold tracking-tight text-foreground">
              {APP_CONFIG.NAME}
            </CardTitle>

            <CardDescription className="text-sm leading-relaxed text-muted-foreground">              Sign in to continue your learning journey.
            </CardDescription>

          </CardHeader>

          <CardContent>

            {error && (
              <div
                role="alert"
                className="mb-6 flex items-start gap-3 rounded-xl border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive"
              >
                <WarningIcon
                  size={18}
                  className="mt-0.5 shrink-0"
                />

                <span className="leading-relaxed">
                  {error}
                </span>
              </div>
            )}

            <form
              onSubmit={handleSubmit}
              className="space-y-6"
            >

              <div className="space-y-2">

                <Label htmlFor="email">
                  Email address
                </Label>

                <div className="relative">

                  <MailIcon
                    size={18}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  />

                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    placeholder="user@example.com"
                    value={email}
                    onChange={(e) =>
                      setEmail(e.target.value)
                    }
                    className="h-11 pl-10"
                    required
                  />

                </div>

              </div>

              <div className="space-y-2">

                <div className="flex items-center justify-between">

                  <Label htmlFor="password">
                    Password
                  </Label>

                  <Link
                    href={AUTH_ROUTES.FORGOT_PASSWORD}
                    className="text-sm font-medium text-primary transition-colors hover:text-[var(--primary-hover)]"
                  >
                    Forgot password?
                  </Link>

                </div>

                <div className="relative">

                  <LockIcon
                    size={18}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  />

                  <Input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) =>
                      setPassword(e.target.value)
                    }
                    className="h-11 pl-10"
                    required
                  />

                </div>

              </div>              <div className="flex items-center justify-between">

                <div className="flex items-center space-x-2">

                  <Checkbox
                    id="remember-me"
                    checked={rememberMe}
                    onCheckedChange={(checked) =>
                      setRememberMe(Boolean(checked))
                    }
                  />

                  <Label
                    htmlFor="remember-me"
                    className="cursor-pointer text-sm font-normal text-muted-foreground"
                  >
                    Remember me
                  </Label>

                </div>

              </div>

              <Button
                type="submit"
                size="lg"
                className="h-11 w-full gap-2"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <ProgressActivityIcon
                      size={18}
                      className="animate-spin"
                    />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>Log in</span>

                    <ArrowForwardIcon
                      size={18}
                      className="transition-transform duration-200 group-hover/button:translate-x-1"
                    />
                  </>
                )}
              </Button>

            </form>

            <div className="mt-8 border-t border-border pt-6 text-center text-sm text-muted-foreground">

              New to LearningAid?{" "}

              <Link
                href={AUTH_ROUTES.REGISTER}
                className="font-semibold text-primary transition-colors hover:text-[var(--primary-hover)]"
              >
                Create account
              </Link>

            </div>

          </CardContent>

        </Card>

      </div>

    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <RedirectLoading message="Loading..." />
      }
    >
      <LoginForm />
    </Suspense>
  );
}