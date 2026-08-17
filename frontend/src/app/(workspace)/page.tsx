"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { useAuth } from "@/hooks/useAuth";
import { dashboardService } from "@/services/dashboard.service";
import { notebookService } from "@/services/notebook.service";
import { DashboardStatsOut } from "@/types/dashboard";
import { NotebookOut } from "@/types/notebook";
import { Skeleton } from "@/components/ui/skeleton";
import { NotebookCard } from "@/components/notebooks/NotebookCard";
import { StatCards } from "@/components/dashboard/StatCards";
import { CreateNotebookModal } from "@/components/notebooks/CreateNotebookModal";
import { DeleteNotebookDialog } from "@/components/notebooks/DeleteNotebookDialog";
import { LibraryIcon, AddIcon } from "@/components/shared/icons";

export default function Homepage() {
  const { currentUser, loading: authLoading } = useAuth();

  const [stats, setStats] = useState<DashboardStatsOut | null>(null);
  const [notebooks, setNotebooks] = useState<NotebookOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingNotebook, setEditingNotebook] = useState<NotebookOut | null>(null);
  const [deletingNotebook, setDeletingNotebook] = useState<NotebookOut | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const displayName =
    currentUser?.full_name ?? currentUser?.email?.split("@")[0] ?? "there";

  useEffect(() => {
    if (authLoading) return;

    let cancelled = false;

    async function load() {
      try {
        const [statsRes, notebooksRes] = await Promise.all([
          dashboardService.getStats(),
          notebookService.getNotebooks(),
        ]);

        if (cancelled) return;

        setStats(statsRes);
        setNotebooks(
          [...notebooksRes]
            .sort(
              (a, b) =>
                new Date(b.updated_at ?? b.created_at).getTime() -
                new Date(a.updated_at ?? a.created_at).getTime()
            )
            .slice(0, 4)
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [authLoading]);

  const handleDelete = async () => {
    if (!deletingNotebook) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await notebookService.deleteNotebook(deletingNotebook.id);
      setNotebooks((prev) => prev.filter((notebook) => notebook.id !== deletingNotebook.id));
      setStats((prev) =>
        prev ? { ...prev, notebook_count: Math.max(0, prev.notebook_count - 1) } : prev
      );
      setDeletingNotebook(null);
    } catch (error: any) {
      setDeleteError(error?.response?.data?.detail || "Failed to delete notebook. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-full w-full p-4 sm:p-6 lg:p-8">
        <div className="mx-auto flex max-w-5xl flex-col gap-5">
          <div className="space-y-3">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-48" />
          </div>

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="rounded-xl border border-border bg-card p-4 lg:p-5">
                <Skeleton className="mb-2 h-8 w-8 rounded-full lg:mb-4 lg:h-10 lg:w-10" />
                <Skeleton className="mb-2 h-8 w-12" />
                <Skeleton className="h-3 w-20" />
              </div>
            ))}
          </div>

          <div className="flex flex-col gap-4">
            <Skeleton className="h-5 w-40" />
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 lg:gap-6">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-40 rounded-xl" />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full w-full p-4 sm:p-6 lg:p-8">
      <div className="mx-auto flex max-w-5xl flex-col gap-5 lg:gap-6">
        <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
          <div className="space-y-1.5">
            <h1 className="font-heading text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
              Welcome back, {displayName}
            </h1>
            <p className="text-sm text-muted-foreground">
              Your quiet corner for deep learning.
            </p>
          </div>

          <button
            onClick={() => {
              setEditingNotebook(null);
              setIsCreateModalOpen(true);
            }}
            className="flex shrink-0 cursor-pointer items-center gap-1.5 self-start rounded-[10px] bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 sm:self-auto"
          >
            <AddIcon size={18} />
            New Notebook
          </button>
        </div>

        <StatCards
          stats={
            stats ?? {
              notebook_count: 0,
              document_count: 0,
              message_count: 0,
              quiz_count: 0,
            }
          }
        />

        <div className="flex flex-col gap-3 lg:gap-4">
          <div className="flex items-center justify-between">
            <h2 className="font-heading text-lg font-semibold text-foreground">
              Recent Notebooks
            </h2>
            <Link
              href="/notebooks"
              className="text-sm font-medium text-primary hover:underline"
            >
              View all
            </Link>
          </div>

          {notebooks.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-10 text-center">
              <LibraryIcon size={32} className="mx-auto mb-3 text-muted-foreground" />
              <p className="font-heading text-base font-medium text-foreground">
                No notebooks yet
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                Create your first notebook to get started.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 lg:gap-6">
              {notebooks.map((notebook) => (
                <NotebookCard
                  key={notebook.id}
                  notebook={notebook}
                  variant="dashboard"
                  onEdit={(selected) => {
                    setEditingNotebook(selected);
                    setIsCreateModalOpen(true);
                  }}
                  onDelete={(selected) => {
                    setDeleteError(null);
                    setDeletingNotebook(selected);
                  }}
                />
              ))}
            </div>
          )}
        </div>

        <CreateNotebookModal
          isOpen={isCreateModalOpen}
          onClose={() => {
            setIsCreateModalOpen(false);
            setEditingNotebook(null);
          }}
          initialNotebook={editingNotebook ?? undefined}
          onSuccess={(savedNotebook) => {
            setNotebooks((prev) =>
              editingNotebook
                ? prev.map((notebook) => notebook.id === savedNotebook.id ? savedNotebook : notebook)
                : [savedNotebook, ...prev].slice(0, 4)
            );
            if (!editingNotebook) {
              setStats((prev) =>
                prev ? { ...prev, notebook_count: prev.notebook_count + 1 } : prev
              );
            }
            setEditingNotebook(null);
          }}
        />
        <DeleteNotebookDialog
          notebook={deletingNotebook}
          deleting={isDeleting}
          error={deleteError}
          onClose={() => {
            setDeletingNotebook(null);
            setDeleteError(null);
          }}
          onConfirm={handleDelete}
        />
      </div>
    </div>
  );
}
