"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";

import { summaryService, SummaryLevel, SummaryFormat, SummaryHistoryItem } from "@/services/summary.service";
import { documentService, DocumentListItem } from "@/services/document.service";
import * as Icons from "@/components/shared/icons";

const LEVEL_OPTIONS: { value: SummaryLevel; label: string }[] = [
    { value: "short", label: "Ngắn gọn" },
    { value: "normal", label: "Chuẩn" },
    { value: "detailed", label: "Chi tiết" },
];

const FORMAT_OPTIONS: { value: SummaryFormat; label: string }[] = [
    { value: "paragraph", label: "Đoạn văn" },
    { value: "bullet", label: "Gạch đầu dòng" },
    { value: "markdown", label: "Markdown" },
];

export default function DocumentSummaryPage() {
    const params = useParams<{ id: string }>();
    const documentId = Number(params.id);
    const searchParams = useSearchParams();

    const [document, setDocument] = useState<DocumentListItem | null>(null);
    const [history, setHistory] = useState<SummaryHistoryItem[]>([]);
    const defaultTitle = document ? `Bản tóm tắt ${document.title}` : "Bản tóm tắt tài liệu";


    const [level, setLevel] = useState<SummaryLevel>("normal");
    const [format, setFormat] = useState<SummaryFormat>("markdown");
    const [instruction, setInstruction] = useState("");
    const [showInstruction, setShowInstruction] = useState(false);

    const [title, setTitle] = useState("");
    const [summary, setSummary] = useState<string | null>(null);
    const [viewingHistoryId, setViewingHistoryId] = useState<number | null>(null);

    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);
    const [saveSuccess, setSaveSuccess] = useState(false);

    const [duplicateTarget, setDuplicateTarget] = useState<SummaryHistoryItem | null>(null);

    const resultRef = useRef<HTMLDivElement>(null);


    useEffect(() => {
        documentService.getDocument(documentId).then(setDocument);
        summaryService.listHistory(documentId).then(setHistory).catch(() => { });

        const summaryIdParam = searchParams.get("summaryId");
        if (summaryIdParam) {
            loadSummaryDetail(Number(summaryIdParam));
        }
    }, [documentId]);

    const handleGenerate = async () => {
        setLoading(true);
        setError(null);
        setViewingHistoryId(null);
        setTitle("");
        try {
            const text = await summaryService.summarize({ document_id: documentId, level, format, instruction: instruction.trim() || undefined });
            setSummary(text);
        } catch (err: any) {
            setError(err?.response?.data?.detail || "Không tạo được tóm tắt. Vui lòng thử lại.");
        } finally {
            setLoading(false);
        }
    };

    const handleCopy = async () => {
        if (!summary) return;
        await navigator.clipboard.writeText(summary);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
    };

    const doSave = async (finalTitle: string) => {
        if (!summary) return;
        setSaving(true);
        setError(null);
        try {
            const saved = await summaryService.save({
            document_id: documentId,
            title: finalTitle,
            summary_text: summary,
            level,
            format,
            instruction: instruction.trim() || undefined,
        });

        setViewingHistoryId(saved.summary_id);

        const refreshed = await summaryService.listHistory(documentId);

        setHistory(refreshed);
            setSaveSuccess(true);
            setTimeout(() => setSaveSuccess(false), 1500);
        } catch (err: any) {
            setError(err?.response?.data?.detail || "Lưu thất bại. Vui lòng thử lại.");
        } finally {
            setSaving(false);
        }
    };

    const handleSaveClick = async () => {
        if (!summary) return;

        const finalTitle = title.trim() || defaultTitle;

        // Đang xem một bản ghi đã lưu -> luôn UPDATE
        if (viewingHistoryId !== null) {
            setSaving(true);
            setError(null);

            try {
                await summaryService.update({
                    summary_id: viewingHistoryId,
                    summary_text: summary,
                    title: finalTitle,
                });

                const refreshed = await summaryService.listHistory(documentId);
                setHistory(refreshed);

                setTitle(finalTitle);

                setSaveSuccess(true);
                setTimeout(() => setSaveSuccess(false), 1500);
            } catch (err: any) {
                setError(err?.response?.data?.detail || "Cập nhật thất bại.");
            } finally {
                setSaving(false);
            }

            return;
        }

        // Chưa có bản ghi -> tạo mới như cũ
        const duplicate = history.find((h) => h.title === finalTitle);

        if (duplicate) {
            setDuplicateTarget(duplicate);
            return;
        }

        doSave(finalTitle);
    };

    const handleOverwrite = async () => {
        if (!duplicateTarget || !summary) return;
        setSaving(true);
        setError(null);
        const target = duplicateTarget;
        setDuplicateTarget(null);
        try {
            await summaryService.update({
                summary_id: target.id,
                summary_text: summary,
                title: title.trim() || target.title,
            });
            const refreshed = await summaryService.listHistory(documentId);
            setHistory(refreshed);
            setSaveSuccess(true);
            setTimeout(() => setSaveSuccess(false), 1500);
        } catch (err: any) {
            setError(err?.response?.data?.detail || "Ghi đè thất bại.");
        } finally {
            setSaving(false);
        }
    };

    const handleCreateNewAnyway = () => {
        const target = duplicateTarget;
        setDuplicateTarget(null);
        if (target) doSave(getUniqueTitle(target.title));
    };

    const loadSummaryDetail = async (summaryId: number) => {
        setError(null);
        try {
            const detail = await summaryService.getDetail(summaryId);
            setViewingHistoryId(detail.id);
            setLevel(detail.level as SummaryLevel);
            setFormat(detail.format as SummaryFormat);
            setTitle(detail.title);
            setInstruction(detail.instruction || "");
            setSummary(detail.summary_text);
            setTimeout(() => {
                resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 100);
        } catch {
            setError("Không tải được bản tóm tắt này.");
        }
    };

    const handleViewHistory = (item: SummaryHistoryItem) => {
        loadSummaryDetail(item.id);
    };
    const isViewingSaved = viewingHistoryId !== null;
    const getUniqueTitle = (base: string) => {
        const existingTitles = new Set(history.map((h) => h.title));
        if (!existingTitles.has(base)) return base;
        let i = 1;
        while (existingTitles.has(`${base} (${i})`)) i++;
        return `${base} (${i})`;
    };



    return (
        <div className="max-w-4xl mx-auto space-y-6 pt-4">
            <div className="space-y-1.5">
                <Link href="/summary" className="text-xs text-gray-400 hover:text-[#2e5f3f] transition-colors">
                    ← Chọn tài liệu khác
                </Link>
                <h1 className="text-2xl font-bold tracking-tight text-gray-900">Tóm tắt tài liệu</h1>
            </div>

            {/* Controls */}
            <div className="bg-white border border-gray-100 rounded-2xl p-5 space-y-4">
                <div className="flex flex-wrap items-center gap-6">
                    <div className="space-y-1.5">
                        <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Độ dài</p>
                        <div className="flex gap-1.5">
                            {LEVEL_OPTIONS.map((opt) => (
                                <button key={opt.value} onClick={() => setLevel(opt.value)}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${level === opt.value ? "bg-[#e6f4ea] text-[#2e5f3f]" : "text-gray-500 hover:bg-gray-50"}`}>
                                    {opt.label}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className="space-y-1.5">
                        <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Định dạng</p>
                        <div className="flex gap-1.5">
                            {FORMAT_OPTIONS.map((opt) => (
                                <button key={opt.value} onClick={() => setFormat(opt.value)}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${format === opt.value ? "bg-[#e6f4ea] text-[#2e5f3f]" : "text-gray-500 hover:bg-gray-50"}`}>
                                    {opt.label}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                <div>
                    <button
                        onClick={() => setShowInstruction((v) => !v)}
                        className="px-3 py-2 rounded-lg text-xs font-medium text-gray-500 hover:text-[#2e5f3f] hover:bg-gray-50 transition-colors"
                    >
                        {showInstruction ? "− Ẩn yêu cầu tuỳ chỉnh" : "+ Thêm yêu cầu tuỳ chỉnh"}
                    </button>
                    {showInstruction && (
                        <div className="mt-2 bg-gray-100 rounded-xl p-1">
                            <textarea
                                value={instruction}
                                onChange={(e) => setInstruction(e.target.value)}
                                placeholder="Ví dụ: tập trung vào phần công thức, bỏ qua phần giới thiệu..."
                                rows={2}
                                className="w-full text-xs bg-transparent p-2.5 focus:outline-none resize-none placeholder:text-gray-400"
                            />
                        </div>
                    )}
                </div>

                <button onClick={handleGenerate} disabled={loading}
                    className="px-4 py-2 text-xs font-medium bg-[#3b7a52] hover:bg-[#2e5f3f] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg shadow-sm transition-colors">
                    {loading ? "Đang tạo..." : summary ? "Tạo lại" : "Tạo tóm tắt"}
                </button>
            </div>

            {/* Title + Save bar */}
            {summary && !loading && (
                <div className="space-y-1.5">
                    <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wider px-1">Tiêu đề bản tóm tắt</p>
                    <div className="bg-white border border-gray-100 rounded-2xl p-3 flex items-center gap-2">
                        <div className="flex-1 flex items-center gap-2 bg-gray-100 rounded-xl px-3 py-2.5">
                            <Icons.PenIcon className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                            <input
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                placeholder={defaultTitle}
                                className="flex-1 text-sm text-gray-800 placeholder:text-gray-400 bg-transparent focus:outline-none"
                            />
                        </div>
                        <button
                            onClick={handleSaveClick}
                            disabled={saving}
                            className={`shrink-0 flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl text-xs font-medium transition-colors disabled:opacity-40 ${saveSuccess ? "bg-emerald-100 text-emerald-700" : "bg-amber-50 text-amber-700 hover:bg-amber-100"
                                }`}
                        >
                            {saveSuccess ? <Icons.CheckIcon className="w-4 h-4" /> : <Icons.SaveIcon className="w-4 h-4" />}
                            {saveSuccess ? "Đã lưu" : "Lưu bản ghi"}
                        </button>
                    </div>
                </div>
            )}

            {/* Result */}
            <div className="bg-white border border-gray-100 rounded-2xl p-6 min-h-[240px]">
                {isViewingSaved && (
                    <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-50">
                        <span className="text-[11px] text-blue-500 font-medium">Đang xem bản đã lưu</span>
                        <button onClick={() => { setViewingHistoryId(null); }} className="text-[11px] text-gray-400 hover:text-[#2e5f3f]">
                            Quay lại tạo mới
                        </button>
                    </div>
                )}

                {loading && (
                    <div className="space-y-3">
                        <div className="h-4 bg-gray-100 rounded w-3/4 animate-pulse" />
                        <div className="h-4 bg-gray-100 rounded w-full animate-pulse" />
                        <div className="h-4 bg-gray-100 rounded w-5/6 animate-pulse" />
                    </div>
                )}

                {!loading && error && (
                    <div className="text-center py-8 space-y-3">
                        <p className="text-sm text-red-500">{error}</p>
                        <button onClick={handleGenerate} className="px-4 py-2 text-xs font-medium bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg">Thử lại</button>
                    </div>
                )}

                {!loading && !error && !summary && (
                    <div className="text-center py-12 text-sm text-gray-400">
                        Chọn cấu hình bên trên rồi bấm &quot;Tạo tóm tắt&quot; để bắt đầu.
                    </div>
                )}

                {!loading && !error && summary && (
                    <div className="space-y-4">
                        <div className="flex justify-end">
                            <button
                                onClick={handleCopy}
                                title="Sao chép"
                                className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition-colors ${copied ? "bg-emerald-100 text-emerald-700" : "bg-blue-50 text-blue-600 hover:bg-blue-100"
                                    }`}
                            >
                                {copied ? <Icons.CheckIcon className="w-4 h-4" /> : <Icons.DocumentDuplicateIcon className="w-4 h-4" />}
                                {copied ? "Đã sao chép" : "Sao chép"}
                            </button>
                        </div>
                        <ReactMarkdown
                            components={{
                                h1: (p) => <h1 className="text-lg font-bold text-gray-900 mt-4 mb-2" {...p} />,
                                h2: (p) => <h2 className="text-base font-bold text-gray-900 mt-4 mb-2" {...p} />,
                                h3: (p) => <h3 className="text-sm font-bold text-gray-800 mt-3 mb-1.5" {...p} />,
                                p: (p) => <p className="text-sm text-gray-600 leading-relaxed mb-3" {...p} />,
                                ul: (p) => <ul className="list-disc list-inside text-sm text-gray-600 space-y-1 mb-3" {...p} />,
                                ol: (p) => <ol className="list-decimal list-inside text-sm text-gray-600 space-y-1 mb-3" {...p} />,
                                strong: (p) => <strong className="font-semibold text-gray-800" {...p} />,
                            }}
                        >
                            {summary}
                        </ReactMarkdown>
                    </div>
                )}
            </div>

            {/* Lịch sử tóm tắt đã lưu */}
            {history.length > 0 && (
                <div className="space-y-2">
                    <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wider px-1">Lịch sử tóm tắt</p>
                    <div className="space-y-2">
                        {history.map((item) => (
                            <button key={item.id} onClick={() => handleViewHistory(item)}
                                className={`w-full flex items-center justify-between text-left bg-white border rounded-xl p-3 transition-colors ${viewingHistoryId === item.id ? "border-[#3b7a52] bg-[#e6f4ea]/30" : "border-gray-100 hover:border-gray-200"}`}>
                                <div className="min-w-0">
                                    <p className="text-xs font-medium text-gray-800 truncate">{item.title}</p>
                                    <p className="text-[10px] text-gray-400 mt-0.5">
                                        {LEVEL_OPTIONS.find((l) => l.value === item.level)?.label} · {FORMAT_OPTIONS.find((f) => f.value === item.format)?.label} · {new Date(item.created_at).toLocaleDateString("vi-VN")}
                                    </p>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Modal xác nhận trùng tên */}
            {duplicateTarget && (
                <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4 space-y-4">
                        <p className="text-sm text-gray-700">
                            Bản tóm tắt <span className="font-semibold">&quot;{duplicateTarget.title}&quot;</span> đã tồn tại, bạn có muốn tạo bản ghi mới không?
                        </p>
                        <div className="flex justify-end gap-2">
                            <button onClick={() => setDuplicateTarget(null)} className="px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded-lg">Huỷ</button>
                            <button onClick={handleOverwrite} className="px-3 py-1.5 text-xs font-medium bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg">Ghi đè bản cũ</button>
                            <button onClick={handleCreateNewAnyway} className="px-3 py-1.5 text-xs font-medium bg-[#3b7a52] hover:bg-[#2e5f3f] text-white rounded-lg">Tạo bản mới</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}