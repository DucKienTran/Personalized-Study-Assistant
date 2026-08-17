"use client";

import React, { useState } from "react";

import { userService } from "@/services/user.service";
import { AuthShell } from "@/components/auth/AuthShell";
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
import { Alert, AlertDescription } from "@/components/ui/alert";

interface ApiErrorResponse {
  response?: {
    data?: {
      detail?: string;
    };
  };
}

export default function ChangePasswordPage() {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
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
    return "Failed to change password. Please try again.";
  };

  const validate = (): boolean => {
    if (newPassword.length < 8) {
      setError("new_password: Must be at least 8 characters long.");
      return false;
    }

    const hasLetter = /[a-zA-Z]/.test(newPassword);
    const hasNumber = /[0-9]/.test(newPassword);

    if (!hasLetter || !hasNumber) {
      setError("new_password: Must contain at least one letter and one number.");
      return false;
    }

    if (newPassword === oldPassword) {
      setError("new_password: Must be different from your current password.");
      return false;
    }

    if (newPassword !== confirmPassword) {
      setError("confirm_password: Passwords do not match.");
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (loading) return;

    setError("");
    if (!validate()) return;

    setLoading(true);

    try {
      await userService.changePassword({
        old_password: oldPassword,
        new_password: newPassword,
        confirm_new_password: confirmPassword,
      });
      setIsSuccess(true);
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(parseErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell>
        <Card className="border border-border bg-card shadow-[0_24px_70px_-38px_var(--primary-shadow)] ring-0">
          <CardHeader className="space-y-3 border-b border-border pb-6 text-center sm:text-left">
            <p className="text-xs font-semibold tracking-[0.16em] text-accent uppercase">
              Account security
            </p>
            <CardTitle className="font-heading text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
              Change password
            </CardTitle>
            <CardDescription className="text-sm leading-relaxed text-muted-foreground">
              Update the password for your account.
            </CardDescription>
          </CardHeader>

          <CardContent className="pt-1">
            {isSuccess && (
              <Alert role="status" className="mb-6 border-primary/20 bg-primary/5 text-primary">
                <CheckCircleIcon size={18} />
                <AlertDescription className="text-primary">
                  Password changed successfully. Your other sessions have been signed out.
                </AlertDescription>
              </Alert>
            )}

            {error && (
              <Alert variant="destructive" className="mb-6 bg-destructive/5">
                <WarningIcon size={18} />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="old-password">Current password</Label>
                <div className="relative">
                  <LockIcon
                    size={18}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  />
                  <Input
                    id="old-password"
                    type="password"
                    autoComplete="current-password"
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    className="h-12 rounded-lg bg-background/60 pl-10"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="new-password">New password</Label>
                <div className="relative">
                  <LockIcon
                    size={18}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  />
                  <Input
                    id="new-password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="Minimum 8 characters"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="h-12 rounded-lg bg-background/60 pl-10"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm-new-password">Confirm new password</Label>
                <div className="relative">
                  <LockIcon
                    size={18}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  />
                  <Input
                    id="confirm-new-password"
                    type="password"
                    autoComplete="new-password"
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
                    <span>Updating...</span>
                  </>
                ) : (
                  <>
                    <span>Update password</span>
                    <ArrowForwardIcon
                      size={18}
                      className="transition-transform duration-200 group-hover/button:translate-x-1"
                    />
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
    </AuthShell>
  );
}
