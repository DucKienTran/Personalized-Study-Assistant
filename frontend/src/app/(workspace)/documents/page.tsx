"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { documentService, DocumentListItem } from "@/services/document.service";
import * as Icons from "@/components/shared/icons";

const STATUS_LABEL: Record<string, { text: string; className: string }> = {
    pending: { text: "Chưa xử lý", className: "bg-gray-100 text-gray-500" },
    completed: { text: "Đã xử lý", className: "bg-blue-50 text-blue-600" },
    failed: { text: "Lỗi xử lý", className: "bg-red-50 text-red-500" },
};

const LibrarySkeleton = () => (
    <div className="max-w-5xl mx-auto space-y-4 pt-4 w-full">
        <div className="h-7 bg-gray-200 rounded-md w-48 animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
            {[1, 2, 3, 4].map((i) => <div key={i} className="h-28 bg-white border border-gray-100 rounded-2xl animate-pulse" />)}
        </div>
    </div>
);

export default function DocumentLibraryPage() {
    const router = useRouter();
    const [docs, setDocs] = useState<DocumentListItem[] | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [deletingId, setDeletingId] = useState<number | null>(null);

    const fetchDocs = () => {
        documentService.listDocuments({ limit: 100 })
            .then(setDocs)
            .catch(() => setError("Không tải được danh sách tài liệu."));
    };

    useEffect(() => { fetchDocs(); }, []);

    const handleDelete = async (id: number, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!confirm("Xoá tài liệu này? Toàn bộ tóm tắt liên quan sẽ bị xoá vĩnh viễn.")) return;
        setDeletingId(id);
        try {
            await documentService.deleteDocument(id);
            setDocs((prev) => prev?.filter((d) => d.id !== id) ?? null);
        } catch {
            alert("Xoá thất bại, thử lại sau.");
        } finally {
            setDeletingId(null);
        }
    };

    if (error) return <div className="max-w-5xl mx-auto pt-4 text-center text-sm text-red-500">{error}</div>;
    if (!docs) return <LibrarySkeleton />;

    return (
        <div className="max-w-5xl mx-auto space-y-6 pt-4">
            <div className="space-y-1.5">
                <h1 className="text-2xl font-bold tracking-tight text-gray-900">Thư viện của tôi</h1>
                <p className="text-gray-500 text-xs">Toàn bộ tài liệu bạn đã tải lên.</p>
            </div>

            {docs.length === 0 ? (
                <div className="bg-white border border-dashed border-gray-200 rounded-2xl p-10 text-center space-y-3">
                    <Icons.DocumentIcon className="w-10 h-10 mx-auto text-gray-300" />
                    <p className="text-sm text-gray-500">Bạn chưa tải lên tài liệu nào.</p>
                    <button onClick={() => window.dispatchEvent(new Event("open-upload-modal"))}
                        className="px-4 py-2 text-xs font-medium bg-[#3b7a52] hover:bg-[#2e5f3f] text-white rounded-lg shadow-sm">
                        Tải tài liệu lên
                    </button>
                </div>
            ) : (
                <div className="flex flex-col gap-3"> {/* 👈 đổi từ "grid grid-cols-1 md:grid-cols-2 gap-4" */}
                    {docs.map((doc) => (
                        <div key={doc.id} onClick={() => router.push(`/documents/${doc.id}/summary`)}
                            className="bg-white border border-gray-100 hover:border-blue-200 hover:bg-blue-50/20 rounded-2xl p-4 cursor-pointer transition-all duration-200 group flex items-center justify-between">
                            <div className="flex items-center gap-3 min-w-0">
                                <span className="p-2 bg-blue-50/60 rounded-xl text-blue-500 shrink-0">
                                    <Icons.DocumentIcon className="w-5 h-5" />
                                </span>
                                <div className="min-w-0">
                                    <p className="font-medium text-sm text-gray-800 truncate">{doc.title}</p>
                                    {doc.created_at && (
                                        <p className="text-[11px] text-gray-400 mt-0.5">{new Date(doc.created_at).toLocaleDateString("vi-VN")}</p>
                                    )}
                                </div>
                            </div>
                            <button
                                onClick={(e) => handleDelete(doc.id, e)}
                                disabled={deletingId === doc.id}
                                title="Xoá tài liệu"
                                className="shrink-0 p-1.5 rounded-lg text-gray-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all disabled:opacity-40"
                            >
                                <Icons.TrashIcon className="w-4 h-4" />
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}