"use client";

import { AddDocumentModal } from "@/components/notebooks/AddDocumentModal";

interface UploadModalProps {
    isOpen: boolean;
    onClose: () => void;
    onUploaded: () => void;
}

export default function UploadModal({ isOpen, onClose, onUploaded }: UploadModalProps) {
    return (
      <AddDocumentModal
        isOpen={isOpen}
        showExisting={false}
        onClose={onClose}
        onSuccess={onUploaded}
      />
    );
}
