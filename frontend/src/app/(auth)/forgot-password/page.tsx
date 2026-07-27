"use client";

import React, { useState } from "react";
import Link from "next/link";

import { authService } from "@/services/auth.service";
import { APP_CONFIG } from "@/constants/app";
import { AUTH_ROUTES } from "@/constants/auth";

import { AuthBackgroundPattern } from "@/components/auth/AuthBackgroundPattern";
import {
  MailIcon,
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

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const parseErrorMessage = (err: unknown): string => {
    if (typeof err === "object" && err !== null) {
      const apiErr = err as ApiErrorResponse;
      const detail = apiErr.response?.data?.detail;
      if (typeof detail === "string") return detail;
    }
    return "Something went wrong. Please try again.";
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (loading) return;

    setError("");
    setLoading(true);

    try {
      await authService.forgotPassword({ email: email.trim() });
      setIsSuccess(true);
    } catch (err) {
      setError(parseErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4 py-8">
      <AuthBackgroundPattern />

      <div className="relative z-10 w-full max-w-md">
        <Card className="border-border bg-card/95 shadow-sm backdrop-blur-md transition-shadow duration-200 hover:shadow-md">
          {isSuccess ? (
            <>
              <CardHeader className="space-y-3 text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <CheckCircleIcon size={32} />
                </div>

                <CardTitle className="text-2xl font-bold text-foreground text-balance">
                  Check your email
                </CardTitle>

                <CardDescription className="text-sm leading-relaxed text-muted-foreground">
                  If an account exists for
                </CardDescription>

                <p className="break-all font-semibold text-foreground">{email}</p>
              </CardHeader>

              <CardContent>
                <div className="rounded-xl border border-border bg-muted p-4 text-left">
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    We&apos;ve sent a password reset link. Open your inbox and
                    follow the link to choose a new password.
                  </p>
                </div>

                <Button
                  nativeButton={false}
                  size="lg"
                  className="mt-6 h-11 w-full"
                  render={<Link href={AUTH_ROUTES.LOGIN} />}
                >
                  Back to login
                </Button>

                <button
                  type="button"
                  onClick={() => setIsSuccess(false)}
                  className="mt-4 text-sm font-medium text-primary transition-colors hover:text-[var(--primary-hover)]"
                >
                  Use another email
                </button>
              </CardContent>
            </>
          ) : (
            <>
              <CardHeader className="space-y-3 text-center">
                <CardTitle className="text-balance text-3xl font-bold tracking-tight text-foreground">
                  {APP_CONFIG.NAME}
                </CardTitle>

                <CardDescription className="text-sm leading-relaxed text-muted-foreground">
                  Enter your email and we&apos;ll send you a reset link.
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
                    <Label htmlFor="email">Email address</Label>

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
                        onChange={(e) => setEmail(e.target.value)}
                        className="h-11 pl-10"
                        required
                      />
                    </div>
                  </div>

                  <Button type="submit" size="lg" className="h-11 w-full gap-2" disabled={loading}>
                    {loading ? (
                      <>
                        <ProgressActivityIcon size={18} className="animate-spin" />
                        <span>Sending link...</span>
                      </>
                    ) : (
                      <>
                        <span>Send reset link</span>
                        <ArrowForwardIcon size={18} className="transition-transform duration-200 group-hover/button:translate-x-1" />
                      </>
                    )}
                  </Button>
                </form>

                <div className="mt-8 border-t border-border pt-6 text-center text-sm text-muted-foreground">
                  Remembered your password?{" "}
                  <Link
                    href={AUTH_ROUTES.LOGIN}
                    className="font-semibold text-primary transition-colors hover:text-[var(--primary-hover)]"
                  >
                    Log in
                  </Link>
                </div>
              </CardContent>
            </>
          )}
        </Card>
      </div>
    </main>
  );
}