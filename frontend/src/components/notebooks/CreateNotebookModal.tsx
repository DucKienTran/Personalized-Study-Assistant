// components/notebooks/CreateNotebookModal.tsx
"use client";

import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { notebookService } from "@/services/notebook.service"; // điều chỉnh import path nếu cần
import { NotebookOut } from "@/types/notebook";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (notebook: NotebookOut) => void;
  initialNotebook?: {
    id: number;
    title: string;
    description: string | null;
    color: string;
  };
}

const ACCENT_COLORS = [
  "#46583a", // Warm Olive Green (Default)
  "#8a8175", // Taupe / Muted Brown
  "#4a6fa5", // Slate Blue
  "#c08a3e", // Warm Ochre
  "#a05a4a", // Terracotta Rust
];

export function CreateNotebookModal({
  isOpen,
  onClose,
  onSuccess,
  initialNotebook,
}: ModalProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [selectedColor, setSelectedColor] = useState(ACCENT_COLORS[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isEditing = Boolean(initialNotebook);

  useEffect(() => {
    if (!isOpen) return;
    setTitle(initialNotebook?.title ?? "");
    setDescription(initialNotebook?.description ?? "");
    setSelectedColor(initialNotebook?.color ?? ACCENT_COLORS[0]);
    setError(null);
  }, [initialNotebook, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const saved = initialNotebook
        ? await notebookService.updateNotebook(initialNotebook.id, {
            title: title.trim(),
            description: description.trim(),
            color: selectedColor,
          })
        : await notebookService.createNotebook({
            title: title.trim(),
            description: description.trim() || undefined,
            color: selectedColor,
          });

      // Reset form
      setTitle("");
      setDescription("");
      setSelectedColor(ACCENT_COLORS[0]);
      
      onSuccess(saved);
      onClose();
    } catch (err: any) {
      setError(
        err?.response?.data?.message ||
          `Failed to ${isEditing ? "update" : "create"} notebook. Please try again.`
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[500px] rounded-2xl bg-[#f7f5f0] border-border p-8 shadow-xl">
        <DialogHeader className="text-center space-y-2 mb-2">
          <DialogTitle className="font-heading text-2xl text-foreground font-semibold">
            {isEditing ? "Edit notebook" : "Create a new notebook"}
          </DialogTitle>
          <p className="text-sm text-muted-foreground">
            {isEditing
              ? "Update this notebook's details and accent color."
              : "Set up a quiet corner for a new subject or topic."}
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="p-3 rounded-xl bg-destructive/10 text-destructive text-xs font-medium">
              {error}
            </div>
          )}

          {/* Notebook Title */}
          <div className="space-y-2 text-left">
            <label className="text-sm font-medium text-foreground">
              Notebook title
            </label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Biology 101, Fall Quarter"
              required
              className="rounded-xl bg-card border-border/80 h-11 text-sm focus-visible:ring-primary focus-visible:border-primary shadow-2xs"
            />
          </div>

          {/* Description */}
          <div className="space-y-2 text-left">
            <label className="text-sm font-medium text-foreground">
              Description (optional)
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What will you learn here?"
              rows={3}
              className="rounded-xl bg-card border-border/80 text-sm focus-visible:ring-primary focus-visible:border-primary shadow-2xs resize-none"
            />
          </div>

          {/* Accent Color Selection */}
          <div className="space-y-2 text-left">
            <label className="text-sm font-medium text-foreground">
              Accent color
            </label>
            <div className="flex items-center gap-3 pt-1">
              {ACCENT_COLORS.map((color) => {
                const isSelected = selectedColor === color;
                return (
                  <button
                    key={color}
                    type="button"
                    onClick={() => setSelectedColor(color)}
                    className={`w-8 h-8 rounded-full transition-transform duration-150 flex items-center justify-center ${
                      isSelected ? "scale-110 ring-2 ring-offset-2 ring-primary" : "hover:scale-105"
                    }`}
                    style={{ backgroundColor: color }}
                    aria-label={`Select color ${color}`}
                  />
                );
              })}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-center gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="rounded-xl bg-card border-border hover:bg-secondary text-foreground px-6 h-10 text-sm font-medium"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={loading || !title.trim()}
              className="rounded-xl bg-primary hover:bg-[var(--primary-hover)] text-primary-foreground px-6 h-10 text-sm font-medium shadow-2xs"
            >
              {loading
                ? isEditing
                  ? "Saving..."
                  : "Creating..."
                : isEditing
                  ? "Save Changes"
                  : "Create Notebook"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
