"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { NotebookOut } from "@/types/notebook";

interface DeleteNotebookDialogProps {
  notebook: NotebookOut | null;
  deleting: boolean;
  error: string | null;
  onClose: () => void;
  onConfirm: () => void;
}

export function DeleteNotebookDialog({
  notebook,
  deleting,
  error,
  onClose,
  onConfirm,
}: DeleteNotebookDialogProps) {
  return (
    <Dialog open={notebook !== null} onOpenChange={(open) => !open && !deleting && onClose()}>
      <DialogContent showCloseButton={!deleting}>
        <DialogHeader>
          <DialogTitle>Delete notebook?</DialogTitle>
          <DialogDescription>
            Deleting <span className="font-medium text-foreground">{notebook?.title}</span> will
            permanently remove its conversations, quizzes, attempts, and summaries. Uploaded
            documents will remain in your document library.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
            {error}
          </p>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose} disabled={deleting}>
            Cancel
          </Button>
          <Button type="button" variant="destructive" onClick={onConfirm} disabled={deleting}>
            {deleting ? "Deleting..." : "Delete notebook"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
