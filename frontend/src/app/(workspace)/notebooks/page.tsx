"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { NotebookCard } from "@/components/notebooks/NotebookCard";
import { CreateNotebookModal } from "@/components/notebooks/CreateNotebookModal";
import { DeleteNotebookDialog } from "@/components/notebooks/DeleteNotebookDialog";
import { Icon } from "@/components/shared/icons";
import { Button } from "@/components/ui/button";
import { notebookService } from "@/services/notebook.service";
import { NotebookOut } from "@/types/notebook";

export default function NotebooksPage() {
  const searchParams = useSearchParams();
  const requestedTab = searchParams.get("tab");
  const initialTab =
    requestedTab === "assistant" || requestedTab === "summary"
      ? requestedTab
      : undefined;
  const [notebooks, setNotebooks] = useState<NotebookOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingNotebook, setEditingNotebook] = useState<NotebookOut | null>(null);
  const [deletingNotebook, setDeletingNotebook] = useState<NotebookOut | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const fetchNotebooks = async () => {
    try {
      setLoading(true);
      const data = await notebookService.getNotebooks();
      setNotebooks(data);
    } catch (err) {
      console.error("Failed to load notebooks:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotebooks();
  }, []);

  const handleCreated = (newNotebook: NotebookOut) => {
    setNotebooks((prev) =>
      editingNotebook
        ? prev.map((notebook) => notebook.id === newNotebook.id ? newNotebook : notebook)
        : [newNotebook, ...prev]
    );
    setEditingNotebook(null);
  };

  const handleDelete = async () => {
    if (!deletingNotebook) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await notebookService.deleteNotebook(deletingNotebook.id);
      setNotebooks((prev) => prev.filter((notebook) => notebook.id !== deletingNotebook.id));
      setDeletingNotebook(null);
    } catch (error: any) {
      setDeleteError(error?.response?.data?.detail || "Failed to delete notebook. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  };

  const shouldScroll = notebooks.length > 8;

  return (
    <div className="h-full w-full overflow-hidden p-6 text-foreground lg:p-8">
      <main className="mx-auto flex h-full min-h-0 max-w-7xl flex-col">
        {/* Page Header */}
        <div className="mb-5 flex shrink-0 items-center justify-between border-b border-border/60 pb-5 lg:mb-6">
          <div>
            <h1 className="font-heading text-3xl font-bold tracking-tight text-foreground">
              Notebooks
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              All your subjects and topics in one place.
            </p>
          </div>

          <Button
            onClick={() => {
              setEditingNotebook(null);
              setIsModalOpen(true);
            }}
            className="rounded-xl bg-primary hover:bg-[var(--primary-hover)] text-primary-foreground shadow-2xs px-4 py-2.5 flex items-center gap-2 text-sm font-medium"
          >
            <Icon name="add" className="text-lg" />
            <span>New Notebook</span>
          </Button>
        </div>

        {/* Content Body */}
        <div className={`min-h-0 flex-1 ${shouldScroll ? "overflow-y-auto pr-2" : "overflow-hidden"}`}>
        {loading ? (
          <div className="grid h-full grid-cols-2 gap-4 lg:grid-cols-4 lg:gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-40 animate-pulse rounded-2xl bg-muted/60" />
            ))}
          </div>
        ) : notebooks.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card p-12 text-center">
            <div className="w-12 h-12 rounded-2xl bg-secondary text-muted-foreground flex items-center justify-center mb-4 text-2xl">
              <Icon name="auto_stories" />
            </div>
            <h3 className="font-heading text-lg font-semibold text-foreground">
              No notebooks yet
            </h3>
            <p className="text-xs text-muted-foreground max-w-sm mt-1 mb-6">
              Create your first notebook to organize your learning materials and start chatting with AI.
            </p>
            <Button
              onClick={() => {
                setEditingNotebook(null);
                setIsModalOpen(true);
              }}
              className="rounded-xl bg-primary hover:bg-[var(--primary-hover)] text-primary-foreground flex items-center gap-2"
            >
              <Icon name="add" className="text-lg" />
              Create Notebook
            </Button>
          </div>
        ) : (
          <div
            className={`grid grid-cols-2 gap-4 lg:grid-cols-4 lg:gap-6 ${
              shouldScroll
                ? "auto-rows-[minmax(160px,auto)] pb-2"
                : "notebook-grid-fixed h-full [&>div]:min-h-0"
            }`}
            style={
              !shouldScroll
                ? ({
                    "--notebook-rows-mobile": Math.max(1, Math.ceil(notebooks.length / 2)),
                    "--notebook-rows-desktop": Math.max(1, Math.ceil(notebooks.length / 4)),
                  } as React.CSSProperties)
                : undefined
            }
          >
            {notebooks.map((nb) => (
              <NotebookCard
                key={nb.id}
                notebook={nb}
                variant="full"
                initialTab={initialTab}
                fitViewport={!shouldScroll}
                onEdit={(notebook) => {
                  setEditingNotebook(notebook);
                  setIsModalOpen(true);
                }}
                onDelete={(notebook) => {
                  setDeleteError(null);
                  setDeletingNotebook(notebook);
                }}
              />
            ))}
          </div>
        )}
        </div>
      </main>

      {/* Modal */}
      <CreateNotebookModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingNotebook(null);
        }}
        onSuccess={handleCreated}
        initialNotebook={editingNotebook ?? undefined}
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
  );
}
