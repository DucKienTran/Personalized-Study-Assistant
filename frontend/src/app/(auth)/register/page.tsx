"use client";

import React, { useState } from "react";
import Link from "next/link";

import { authService } from "@/services/auth.service";

import { AUTH_ROUTES } from "@/constants/auth";

import { UserRegister } from "@/types";

import { AuthShell } from "@/components/auth/AuthShell";

import {
  MailIcon,
  LockIcon,
  PersonIcon,
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
    return "Registration failed. Please check your information and try again.";
  };

  const validateForm = (): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailRegex.test(email.trim())) {
      setError("email: Please enter a valid email address.");
      return false;
    }

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

    if (!validateForm()) return;

    setLoading(true);

    try {
      const payload: UserRegister = {
        email: email.trim(),
        password,
        confirm_password: confirmPassword,
        full_name: fullName.trim() || null,
      };

      await authService.register(payload);
      setIsSuccess(true);
    } catch (err) {
      setError(parseErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <AuthShell>
          <Card className="border border-border bg-card text-center shadow-[0_24px_70px_-38px_var(--primary-shadow)] ring-0">
            <CardHeader className="space-y-3">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
                <CheckCircleIcon size={32} />
              </div>

              <CardTitle className="font-heading text-3xl font-medium text-foreground text-balance">
                Check your email
              </CardTitle>

              <CardDescription className="text-sm leading-relaxed text-muted-foreground">
                We&apos;ve sent a verification email to
              </CardDescription>

              <p className="break-all font-semibold text-foreground">{email}</p>
            </CardHeader>

            <CardContent>
              <div className="rounded-lg border border-border bg-muted/60 p-4 text-left">
                <p className="text-sm leading-relaxed text-muted-foreground">
                  If this email is awaiting verification, a new verification
                  email has been sent.
                </p>

                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                  Open your inbox and click the verification link to activate
                  your account before signing in.
                </p>
              </div>

              <Button
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
          </Card>
      </AuthShell>
    );
  }

  return (
    <AuthShell>
        <Card className="border border-border bg-card shadow-[0_24px_70px_-38px_var(--primary-shadow)] ring-0">
          <CardHeader className="space-y-3 border-b border-border pb-6 text-center sm:text-left">
            <p className="text-xs font-semibold tracking-[0.16em] text-accent uppercase">
              Begin a new chapter
            </p>
            <CardTitle className="font-heading text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
              Create your account
            </CardTitle>

            <CardDescription className="text-sm leading-relaxed text-muted-foreground">
              Set up your learning space in a few moments.
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
                <Label htmlFor="full-name">
                  Full name <span className="font-normal text-muted-foreground">(optional)</span>
                </Label>

                <div className="relative">
                  <PersonIcon
                    size={18}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  />

                  <Input
                    id="full-name"
                    type="text"
                    autoComplete="name"
                    placeholder="John Doe"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="h-12 rounded-lg bg-background/60 pl-10"
                  />
                </div>
              </div>

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

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>

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
                    className="h-12 rounded-lg bg-background/60 pl-10"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm-password">Confirm password</Label>

                <div className="relative">
                  <LockIcon
                    size={18}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  />

                  <Input
                    id="confirm-password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="Repeat your password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="h-12 rounded-lg bg-background/60 pl-10"
                    required
                  />
                </div>
              </div>

              <Button type="submit" size="lg" className="h-12 w-full gap-2 rounded-lg hover:bg-[var(--primary-hover)]" disabled={loading}>
                {loading ? (
                  <>
                    <ProgressActivityIcon size={18} className="animate-spin" />
                    <span>Creating account...</span>
                  </>
                ) : (
                  <>
                    <span>Create account</span>
                    <ArrowForwardIcon size={18} className="transition-transform duration-200 group-hover/button:translate-x-1" />
                  </>
                )}
              </Button>
            </form>

            <div className="mt-8 border-t border-border pt-6 text-center text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link
                href={AUTH_ROUTES.LOGIN}
                className="font-semibold text-primary transition-colors hover:text-[var(--primary-hover)]"
              >
                Log in
              </Link>
            </div>
          </CardContent>
        </Card>
    </AuthShell>
  );
}
