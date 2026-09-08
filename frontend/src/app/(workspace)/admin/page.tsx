
"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { AccessNotFound } from "@/components/shared/AccessNotFound";
import { useAuth } from "@/hooks/useAuth";
import { userService } from "@/services/user.service";
import type { UserResponse, UserStatus } from "@/types";

type AdminForm = {
  full_name: string;
  email: string;
  password: string;
  confirm_password: string;
};

const EMPTY_FORM: AdminForm = {
  full_name: "",
  email: "",
  password: "",
  confirm_password: "",
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(new Date(value));
}

export default function AdminPage() {
  const { currentUser, loading: authLoading } = useAuth();

  const [users, setUsers] = useState<UserResponse[]>([]);
  const [statuses, setStatuses] = useState<UserStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<AdminForm>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (currentUser?.role_name !== "admin") return;

    let cancelled = false;

    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const [allUsers, allStatuses] = await Promise.all([
          userService.getAllUsers(),
          userService.getAllUserStatuses(),
        ]);

        if (!cancelled) {
          setUsers(allUsers);
          setStatuses(allStatuses);
        }
      } catch {
        if (!cancelled) setError("Could not load admin data.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [authLoading, currentUser]);

  const statusByUserId = useMemo(
    () => new Map(statuses.map((item) => [item.user_id, item])),
    [statuses],
  );

  const stats = useMemo(
    () => ({
      total: users.length,
      active: users.filter((user) => user.is_active).length,
      online: statuses.filter((status) => status.status === "online").length,
      admins: users.filter((user) => user.role_name === "admin").length,
    }),
    [statuses, users],
  );

  const handleCreateAdmin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMessage(null);
    setError(null);

    if (form.password !== form.confirm_password) {
      setError("Passwords do not match.");
      return;
    }

    try {
      setSubmitting(true);
      const result = await userService.createAdmin({
        email: form.email.trim(),
        full_name: form.full_name.trim() || undefined,
        password: form.password,
        confirm_password: form.confirm_password,
      });
      setMessage(result.detail);
      setForm(EMPTY_FORM);
    } catch {
      setError("Could not create admin account.");
    } finally {
      setSubmitting(false);
    }
  };

  if (authLoading) return null;

  if (currentUser?.role_name !== "admin") {
    return <AccessNotFound />;
  }

  return (
    <div className="h-full overflow-y-auto bg-background">
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-6">
          <p className="text-sm font-medium text-muted-foreground">Administration</p>
          <h1 className="mt-1 font-heading text-2xl font-semibold tracking-tight text-foreground">
            User management
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Review account and presence information, or invite another administrator.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Total users", stats.total],
            ["Active accounts", stats.active],
            ["Online now", stats.online],
            ["Admins", stats.admins],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl border border-border bg-card p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {label}
              </p>
              <p className="mt-2 text-2xl font-semibold text-foreground">{value}</p>
            </div>
          ))}
        </div>

        <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <section className="min-w-0 rounded-2xl border border-border bg-card">
            <div className="border-b border-border px-4 py-4 sm:px-5">
              <h2 className="font-semibold text-foreground">All users</h2>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Account information and current presence state.
              </p>
            </div>

            {loading ? (
              <div className="p-8 text-center text-sm text-muted-foreground">Loading users…</div>
            ) : error && users.length === 0 ? (
              <div className="p-8 text-center text-sm text-destructive">{error}</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[820px] text-left text-sm">
                  <thead className="bg-muted/40 text-xs text-muted-foreground">
                    <tr>
                      <th className="px-5 py-3 font-medium">User</th>
                      <th className="px-5 py-3 font-medium">Role</th>
                      <th className="px-5 py-3 font-medium">Account</th>
                      <th className="px-5 py-3 font-medium">Presence</th>
                      <th className="px-5 py-3 font-medium">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {users.map((user) => {
                      const presence = statusByUserId.get(user.id);
                      const isOnline = presence?.status === "online";

                      return (
                        <tr key={user.id} className="hover:bg-muted/20">
                          <td className="px-5 py-4">
                            <p className="font-medium text-foreground">
                              {user.full_name || "Unnamed user"}
                            </p>
                            <p className="mt-0.5 text-xs text-muted-foreground">{user.email}</p>
                          </td>
                          <td className="px-5 py-4 capitalize text-foreground">{user.role_name}</td>
                          <td className="px-5 py-4">
                            <span className="rounded-full border border-border px-2.5 py-1 text-xs text-foreground">
                              {user.is_active ? "Active" : "Inactive"}
                            </span>
                          </td>
                          <td className="px-5 py-4">
                            <div className="flex items-center gap-2">
                              <span
                                className={`h-2 w-2 rounded-full ${
                                  isOnline ? "bg-emerald-500" : "bg-muted-foreground/40"
                                }`}
                              />
                              <span className="text-foreground">
                                {presence?.message ?? "Unknown"}
                              </span>
                            </div>
                          </td>
                          <td className="px-5 py-4 text-muted-foreground">
                            {formatDate(user.created_at)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <aside className="rounded-2xl border border-border bg-card p-5 xl:self-start">
            <h2 className="font-semibold text-foreground">Create admin</h2>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              The new admin follows the existing email-verification flow before the account is created.
            </p>

            <form className="mt-5 space-y-4" onSubmit={handleCreateAdmin}>
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-foreground">Full name</span>
                <input
                  value={form.full_name}
                  onChange={(e) => setForm((prev) => ({ ...prev, full_name: e.target.value }))}
                  className="h-10 w-full rounded-xl border border-border bg-background px-3 outline-none focus:ring-2 focus:ring-primary/20"
                  placeholder="Optional"
                />
              </label>

              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-foreground">Email</span>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
                  className="h-10 w-full rounded-xl border border-border bg-background px-3 outline-none focus:ring-2 focus:ring-primary/20"
                />
              </label>

              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-foreground">Password</span>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={form.password}
                  onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
                  className="h-10 w-full rounded-xl border border-border bg-background px-3 outline-none focus:ring-2 focus:ring-primary/20"
                />
              </label>

              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-foreground">Confirm password</span>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={form.confirm_password}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, confirm_password: e.target.value }))
                  }
                  className="h-10 w-full rounded-xl border border-border bg-background px-3 outline-none focus:ring-2 focus:ring-primary/20"
                />
              </label>

              {message && <p className="text-xs text-emerald-700">{message}</p>}
              {error && <p className="text-xs text-destructive">{error}</p>}

              <button
                type="submit"
                disabled={submitting}
                className="h-10 w-full rounded-xl bg-foreground px-4 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitting ? "Creating…" : "Create admin"}
              </button>
            </form>
          </aside>
        </div>
      </div>
    </div>
  );
}
