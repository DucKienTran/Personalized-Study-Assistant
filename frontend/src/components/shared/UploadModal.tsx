"use client";

import React, { useRef, useState } from "react";
import { documentService, DocumentListItem } from "@/services/document.service";
import * as Icons from "@/components/shared/icons";

interface UploadModalProps {
    isOpen: boolean;
    onClose: () => void;
    onUploaded: (doc: DocumentListItem) => void;
}

export default function UploadModal({ isOpen, onClose, onUploaded }: UploadModalProps) {
    const inputRef = useRef<HTMLInputElement>(null);
    const [file, setFile] = useState<File | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    if (!isOpen) return null;

    const resetAndClose = () => {
        if (uploading) return; // không cho đóng dở chừng khi đang upload
        setFile(null);
        setError(null);
        onClose();
    };

    const validateAndSetFile = (f: File) => {
        if (!f.name.toLowerCase().endsWith(".pdf")) {
            setError("Hệ thống chỉ hỗ trợ file định dạng PDF.");
            return;
        }
        setError(null);
        setFile(f);
    };

    const handleConfirm = async () => {
        if (!file) return;
        setUploading(true);
        setError(null);
        try {
            const doc = await documentService.uploadDocument(file);
            onUploaded(doc);
            setFile(null);
        } catch (err: any) {
            setError(err?.response?.data?.detail || "Tải tệp thất bại. Vui lòng thử lại.");
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-base font-bold text-gray-900">Tải tệp tài liệu mới lên</h2>
                    <button onClick={resetAndClose} disabled={uploading} className="text-gray-400 hover:text-gray-600 text-lg disabled:opacity-40">×</button>
                </div>

                <input
                    ref={inputRef}
                    type="file"
                    accept="application/pdf"
                    className="hidden"
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) validateAndSetFile(f); }}
                />

                <div
                    onClick={() => !uploading && inputRef.current?.click()}
                    onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={(e) => {
                        e.preventDefault();
                        setIsDragging(false);
                        const f = e.dataTransfer.files?.[0];
                        if (f) validateAndSetFile(f);
                    }}
                    className={`group border-2 border-dashed rounded-xl p-8 text-center flex flex-col items-center justify-center transition-colors cursor-pointer ${
                        isDragging ? "border-[#3b7a52] bg-[#e6f4ea]/40" : "border-[#cbdcd0] hover:border-[#3b7a52]"
                    }`}
                >
                    <Icons.DocumentIcon className="w-12 h-12 mb-4 text-[#cbdcd0] group-hover:text-[#3b7a52] transition-colors" />
                    {file ? (
                        <p className="font-medium text-sm text-[#2e5f3f] truncate max-w-full">{file.name}</p>
                    ) : (
                        <p className="font-medium text-sm text-gray-500 group-hover:text-[#2e5f3f] transition-colors">
                            Kéo thả file PDF vào đây, hoặc bấm để chọn
                        </p>
                    )}
                </div>

                {error && <p className="text-xs text-red-500 mt-3">{error}</p>}

                <div className="mt-6 flex justify-end space-x-3">
                    <button onClick={resetAndClose} disabled={uploading} className="px-4 py-2 text-xs font-medium text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50">
                        Hủy bỏ
                    </button>
                    <button
                        onClick={handleConfirm}
                        disabled={!file || uploading}
                        className="px-4 py-2 text-xs font-medium bg-[#3b7a52] hover:bg-[#2e5f3f] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg shadow-sm"
                    >
                        {uploading ? "Đang tải lên..." : "Xác nhận"}
                    </button>
                </div>
            </div>
        </div>
    );
}