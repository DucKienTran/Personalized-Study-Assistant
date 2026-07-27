"use client";

import React, { useState } from "react";

import { userService } from "@/services/user.service";
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
    <div className="flex min-h-full items-center justify-center bg-[#F8FAF8] px-4 py-12">
      <div className="w-full max-w-md">
        <Card className="border-border bg-card/95 shadow-sm">
          <CardHeader className="space-y-2 text-center">
            <CardTitle className="text-2xl font-bold tracking-tight text-foreground">
              Change password
            </CardTitle>
            <CardDescription className="text-sm leading-relaxed text-muted-foreground">
              Update the password for your account.
            </CardDescription>
          </CardHeader>

          <CardContent>
            {isSuccess && (
              <div
                role="status"
                className="mb-6 flex items-start gap-3 rounded-xl border border-primary/20 bg-primary/10 p-4 text-sm text-primary"
              >
                <CheckCircleIcon size={18} className="mt-0.5 shrink-0" />
                <span className="leading-relaxed">
                  Password changed successfully. Your other sessions have been signed out.
                </span>
              </div>
            )}

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
                    className="h-11 pl-10"
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
                    className="h-11 pl-10"
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
      </div>
    </div>
  );
}