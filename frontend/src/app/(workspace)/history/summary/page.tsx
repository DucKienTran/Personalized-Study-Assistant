// src/app/(workspace)/history/summary/page.tsx
"use client";

import React, { useEffect, useMemo, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { summaryService, SummaryHistoryItem, SummaryLevel, SummaryFormat } from "@/services/summary.service";
import { documentService, DocumentListItem } from "@/services/document.service";
import * as Icons from "@/components/shared/icons";
const LEVEL_LABEL: Record<SummaryLevel, string> = { short: "Ngắn gọn", normal: "Chuẩn", detailed: "Chi tiết" };
const FORMAT_LABEL: Record<SummaryFormat, string> = { paragraph: "Đoạn văn", bullet: "Gạch đầu dòng", markdown: "Markdown" };

const HistorySkeleton = () => (
    <div className="max-w-4xl mx-auto space-y-3 pt-4 w-full">
        <div className="h-7 bg-gray-200 rounded-md w-56 animate-pulse" />
        <div className="space-y-2 mt-6">
            {[1, 2, 3, 4].map((i) => <div key={i} className="h-16 bg-white border border-gray-100 rounded-xl animate-pulse" />)}
        </div>
    </div>
);

export default function SummaryHistoryPage() {
    const router = useRouter();
    const [items, setItems] = useState<SummaryHistoryItem[] | null>(null);
    const [docs, setDocs] = useState<DocumentListItem[]>([]);
    const [filterDocId, setFilterDocId] = useState<number | "all">("all");
    const [error, setError] = useState<string | null>(null);
    const [isFilterOpen, setIsFilterOpen] = useState(false);
    const filterRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (filterRef.current && !filterRef.current.contains(e.target as Node)) {
                setIsFilterOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    useEffect(() => {
        Promise.all([summaryService.listAllHistory(), documentService.listDocuments({ limit: 100 })])
            .then(([summaries, documents]) => { setItems(summaries); setDocs(documents); })
            .catch(() => setError("Không tải được lịch sử tóm tắt."));
    }, []);

    const docTitleMap = useMemo(() => {
        const map = new Map<number, string>();
        docs.forEach((d) => map.set(d.id, d.title));
        return map;
    }, [docs]);


    const selectedDocTitle = filterDocId === "all" ? "Tất cả tài liệu" : docTitleMap.get(filterDocId) || "Tất cả tài liệu";
    const filteredItems = useMemo(() => {
        if (!items) return [];
        if (filterDocId === "all") return items;
        return items.filter((i) => i.document_id === filterDocId);
    }, [items, filterDocId]);

    if (error) return <div className="max-w-4xl mx-auto pt-4 text-center text-sm text-red-500">{error}</div>;
    if (!items) return <HistorySkeleton />;

    return (
        <div className="max-w-4xl mx-auto space-y-6 pt-4">
            <div className="space-y-1.5">
                <h1 className="text-2xl font-bold tracking-tight text-gray-900">Lịch sử tóm tắt</h1>
            </div>

            {docs.length > 0 && (
                <div ref={filterRef} className="relative inline-block">
                    <button
                        onClick={() => setIsFilterOpen((v) => !v)}
                        className={`flex items-center gap-2 px-3.5 py-2 rounded-full transition-colors active:scale-95 ${
                            isFilterOpen ? "bg-gray-200 text-gray-700" : "text-gray-500 hover:bg-gray-100 hover:text-gray-700"
                        }`}
                    >
                        <Icons.FilterIcon className="w-4 h-4" />
                        <span className="text-xs font-medium">{selectedDocTitle}</span>
                    </button>

                    {isFilterOpen && (
                        <div className="absolute left-0 mt-2 w-56 bg-white border border-gray-100 rounded-xl shadow-lg py-1 z-30 text-xs animate-fadeIn">
                            <button
                                onClick={() => { setFilterDocId("all"); setIsFilterOpen(false); }}
                                className={`w-full text-left px-3.5 py-2 hover:bg-gray-50 transition-colors ${filterDocId === "all" ? "text-[#2e5f3f] font-semibold bg-[#e6f4ea]/50" : "text-gray-600"}`}
                            >
                                Tất cả tài liệu
                            </button>
                            {docs.map((d) => (
                                <button
                                    key={d.id}
                                    onClick={() => { setFilterDocId(d.id); setIsFilterOpen(false); }}
                                    className={`w-full text-left px-3.5 py-2 hover:bg-gray-50 transition-colors truncate ${filterDocId === d.id ? "text-[#2e5f3f] font-semibold bg-[#e6f4ea]/50" : "text-gray-600"}`}
                                >
                                    {d.title}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {filteredItems.length === 0 ? (
                <div className="bg-white border border-dashed border-gray-200 rounded-2xl p-10 text-center">
                    <p className="text-sm text-gray-500">Chưa có bản tóm tắt nào được lưu.</p>
                </div>
            ) : (
                <div className="flex flex-col gap-2">
                    {filteredItems.map((item) => (
                        <button
                            key={item.id}
                            onClick={() => router.push(`/documents/${item.document_id}/summary?summaryId=${item.id}`)}
                            className="w-full flex items-center justify-between text-left bg-white border border-gray-100 hover:border-blue-200 hover:bg-blue-50/20 rounded-xl p-3.5 transition-colors"
                        >
                            <div className="min-w-0">
                                <p className="text-xs font-medium text-gray-800 truncate">{item.title}</p>
                                <p className="text-[10px] text-gray-400 mt-0.5">
                                    {docTitleMap.get(item.document_id) || "Tài liệu không xác định"} · {LEVEL_LABEL[item.level as SummaryLevel]} · {FORMAT_LABEL[item.format as SummaryFormat]} · {new Date(item.created_at).toLocaleDateString("vi-VN")}
                                </p>
                            </div>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}