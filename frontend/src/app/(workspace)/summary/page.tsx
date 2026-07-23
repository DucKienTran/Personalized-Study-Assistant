"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {summaryService} from "@/services/summary.service";
import { documentService, DocumentListItem } from "@/services/document.service"; // 👈 đổi từ summaryService
import * as Icons from "@/components/shared/icons";


const STATUS_LABEL: Record<string, { text: string; className: string }> = {
        pending: { text: "Not Processed", className: "bg-gray-100 text-gray-500" },
    completed: { text: "Summarized", className: "bg-blue-50 text-blue-600" },
    failed: { text: "Processing Failed", className: "bg-red-50 text-red-500" },
};

const PickerSkeleton = () => (
    <div className="max-w-3xl mx-auto space-y-4 pt-4 w-full">
        <div className="h-7 bg-gray-200 rounded-md w-56 animate-pulse" />
        <div className="h-4 bg-gray-100 rounded-md w-72 animate-pulse" />
        <div className="space-y-3 mt-6">
            {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 bg-white border border-gray-100 rounded-2xl animate-pulse" />
            ))}
        </div>
    </div>
);

export default function SummaryPickerPage() {
    const router = useRouter();
    const [docs, setDocs] = useState<DocumentListItem[] | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let mounted = true;
        documentService
            .listDocuments({ limit: 50 })
            .then((data) => { if (mounted) setDocs(data); })
            .catch(() => { if (mounted) setError("Failed to load document list. Please try again later."); });
        return () => { mounted = false; };
    }, []);

    if (error) {
        return (
            <div className="max-w-3xl mx-auto pt-4 text-center space-y-3">
                <p className="text-sm text-red-500">{error}</p>
                <button
                    onClick={() => window.location.reload()}
                    className="px-4 py-2 text-xs font-medium bg-[#3b7a52] hover:bg-[#2e5f3f] text-white rounded-lg"
                >
                                        Retry
                </button>
            </div>
        );
    }

    if (!docs) return <PickerSkeleton />;

    return (
        <div className="max-w-3xl mx-auto space-y-6 pt-4">
                        <div className="space-y-1.5">
                <h1 className="text-2xl font-bold tracking-tight text-gray-900">Summarize Document</h1>
                <p className="text-gray-500 text-xs">Select a document to start summarizing.</p>
            </div>

            {docs.length === 0 ? (
                <div className="bg-white border border-dashed border-gray-200 rounded-2xl p-10 text-center space-y-3">
                    <Icons.DocumentIcon className="w-10 h-10 mx-auto text-gray-300" />
                    <p className="text-sm text-gray-500">Bạn chưa tải lên tài liệu nào.</p>
                    <button
                        onClick={() => window.dispatchEvent(new Event("open-upload-modal"))}
                        className="px-4 py-2 text-xs font-medium bg-[#3b7a52] hover:bg-[#2e5f3f] text-white rounded-lg shadow-sm"
                    >
                        Tải tài liệu lên
                    </button>
                </div>
            ) : (
                <div className="space-y-3">
                    {docs.map((doc) => {
                        const statusInfo = STATUS_LABEL[doc.status] ?? STATUS_LABEL.pending;
                        return (
                            <button
                                key={doc.id}
                                onClick={() => router.push(`/documents/${doc.id}/summary`)}
                                className="w-full flex items-center justify-between bg-white border border-gray-100 hover:border-blue-200 hover:bg-blue-50/30 rounded-2xl p-4 text-left transition-all duration-200"
                            >
                                <div className="flex items-center gap-3 min-w-0">
                                    <span className="p-2 bg-blue-50/60 rounded-xl text-blue-500 shrink-0">
                                        <Icons.DocumentIcon className="w-5 h-5" />
                                    </span>
                                    <div className="min-w-0">
                                        <p className="font-medium text-sm text-gray-800 truncate">{doc.title}</p>
                                        {doc.created_at && (
                                            <p className="text-[11px] text-gray-400 mt-0.5">
                                                {new Date(doc.created_at).toLocaleDateString("vi-VN")}
                                            </p>
                                        )}
                                    </div>
                                </div>
                                <span className={`text-[11px] font-medium px-2.5 py-1 rounded-full shrink-0 ${statusInfo.className}`}>
                                    {statusInfo.text}
                                </span>
                            </button>
                        );
                    })}
                </div>
            )}
        </div>
    );
}