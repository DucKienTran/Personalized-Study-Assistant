"use client";

import React, { useState } from "react";
import Link from "next/link";

import { authService } from "@/services/auth.service";
import { AUTH_ROUTES } from "@/constants/auth";

import { AuthShell } from "@/components/auth/AuthShell";
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
import { Alert, AlertDescription } from "@/components/ui/alert";

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
    <AuthShell>
        <Card className="border border-border bg-card shadow-[0_24px_70px_-38px_var(--primary-shadow)] ring-0">
          {isSuccess ? (
            <>
              <CardHeader className="space-y-3 text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <CheckCircleIcon size={32} />
                </div>

                <CardTitle className="font-heading text-3xl font-medium text-foreground text-balance">
                  Check your email
                </CardTitle>

                <CardDescription className="text-sm leading-relaxed text-muted-foreground">
                  If an account exists for
                </CardDescription>

                <p className="break-all font-semibold text-foreground">{email}</p>
              </CardHeader>

              <CardContent>
                <div className="rounded-lg border border-border bg-muted/60 p-4 text-left">
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    We&apos;ve sent a password reset link. Open your inbox and
                    follow the link to choose a new password.
                  </p>
                </div>

                <Button
                  nativeButton={false}
                  size="lg"
                  className="mt-6 h-12 w-full rounded-lg hover:bg-[var(--primary-hover)]"
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
              <CardHeader className="space-y-3 border-b border-border pb-6 text-center sm:text-left">
                <p className="text-xs font-semibold tracking-[0.16em] text-accent uppercase">
                  Account recovery
                </p>
                <CardTitle className="font-heading text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
                  Reset your password
                </CardTitle>

                <CardDescription className="text-sm leading-relaxed text-muted-foreground">
                  Enter your email and we&apos;ll send you a secure reset link.
                </CardDescription>
              </CardHeader>

              <CardContent className="pt-1">
                {error && (
                  <Alert variant="destructive" className="mb-6 bg-destructive/5">
                    <WarningIcon size={18} />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
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
                        className="h-12 rounded-lg bg-background/60 pl-10"
                        required
                      />
                    </div>
                  </div>

                  <Button type="submit" size="lg" className="h-12 w-full gap-2 rounded-lg hover:bg-[var(--primary-hover)]" disabled={loading}>
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
    </AuthShell>
  );
}
