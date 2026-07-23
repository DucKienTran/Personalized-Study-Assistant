"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";

/**
 * Toast dùng chung toàn hệ thống.
 *
 * LÝ DO TỒN TẠI: window.alert()/window.confirm() là dialog native của trình duyệt,
 * khi bật lên sẽ khiến window bắn sự kiện `blur` thật (mất focus cấp OS/browser-chrome),
 * gây tính nhầm vi phạm trong cơ chế chống gian lận Exam Mode. Toast render thuần trong
 * DOM của trang nên KHÔNG bao giờ gây window.blur.
 *
 * Cách dùng:
 *   const { toasts, showToast, dismissToast } = useToast();
 *   showToast("Nội dung...", "warning");
 *   <ToastContainer toasts={toasts} onDismiss={dismissToast} />
 */

export type ToastVariant = "info" | "warning" | "danger" | "success";

export interface ToastItem {
    id: number;
    message: string;
    variant: ToastVariant;
    duration: number; // ms
}

const VARIANT_STYLE: Record<
    ToastVariant,
    { bg: string; border: string; text: string; iconWrap: string; bar: string }
> = {
    info: {
        bg: "bg-white",
        border: "border-blue-200",
        text: "text-blue-600",
        iconWrap: "bg-blue-50 text-blue-600",
        bar: "bg-blue-400",
    },
    warning: {
        bg: "bg-white",
        border: "border-amber-200",
        text: "text-amber-700",
        iconWrap: "bg-amber-50 text-amber-700",
        bar: "bg-amber-400",
    },
    danger: {
        bg: "bg-white",
        border: "border-red-200",
        text: "text-red-600",
        iconWrap: "bg-red-50 text-red-600",
        bar: "bg-red-500",
    },
    success: {
        bg: "bg-white",
        border: "border-emerald-200",
        text: "text-emerald-700",
        iconWrap: "bg-emerald-100 text-emerald-700",
        bar: "bg-emerald-500",
    },
};

// Icon Heroicons-outline (strokeWidth 1.5), inline để không phụ thuộc icons.tsx
// TODO: nếu muốn đồng bộ tuyệt đối, chuyển 4 icon này sang components/shared/icons.tsx
function VariantIcon({ variant }: { variant: ToastVariant }) {
    const common = { className: "w-5 h-5", strokeWidth: 1.5, stroke: "currentColor", fill: "none", viewBox: "0 0 24 24" };
    switch (variant) {
        case "warning":
            return (
                <svg {...common}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m0 3.75h.007M10.29 3.86l-8.18 14.18A1.5 1.5 0 003.5 20.5h17a1.5 1.5 0 001.39-2.46L13.71 3.86a1.5 1.5 0 00-2.42 0z" />
                </svg>
            );
        case "danger":
            return (
                <svg {...common}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376C1.83 17.938 2.905 20 4.697 20h14.606c1.792 0 2.867-2.062 1.9-3.874L14.5 4.876c-.896-1.68-3.104-1.68-4 0L2.697 16.126z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 15.75h.007" />
                </svg>
            );
        case "success":
            return (
                <svg {...common}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75l1.5 1.5 3.75-3.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
            );
        default:
            return (
                <svg {...common}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
                </svg>
            );
    }
}

/** 1 toast đơn, có thanh tiến độ tự đếm ngược tới lúc auto-dismiss */
function ToastCard({ toast, onDismiss }: { toast: ToastItem; onDismiss: (id: number) => void }) {
    const style = VARIANT_STYLE[toast.variant];
    const [mounted, setMounted] = useState(false);
    const [shrinking, setShrinking] = useState(false);

    useEffect(() => {
        // 2 bước để đảm bảo transition CSS chạy đúng lúc mount (enter animation)
        const raf = requestAnimationFrame(() => setMounted(true));
        const shrinkTimer = setTimeout(() => setShrinking(true), 30);
        const dismissTimer = setTimeout(() => onDismiss(toast.id), toast.duration);
        return () => {
            cancelAnimationFrame(raf);
            clearTimeout(shrinkTimer);
            clearTimeout(dismissTimer);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [toast.id]);

    return (
        <div
            role="alert"
            className={`pointer-events-auto w-full max-w-sm overflow-hidden rounded-2xl border ${style.border} ${style.bg} shadow-xl transition-all duration-300 ease-out ${
                mounted ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-2"
            }`}
        >
            <div className="flex items-start gap-3 p-4">
                <span className={`shrink-0 p-2 rounded-xl ${style.iconWrap}`}>
                    <VariantIcon variant={toast.variant} />
                </span>
                <p className="flex-1 text-sm text-gray-700 leading-snug pt-1 whitespace-pre-line">{toast.message}</p>
                <button
                    type="button"
                    onClick={() => onDismiss(toast.id)}
                    className="shrink-0 p-1 rounded-lg text-gray-300 hover:text-gray-500 hover:bg-gray-50 transition-colors active:scale-95"
                    aria-label="Đóng thông báo"
                >
                    <svg className="w-4 h-4" strokeWidth={1.5} stroke="currentColor" fill="none" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
            <div className="h-1 w-full bg-gray-100">
                <div
                    className={`h-full ${style.bar} transition-all ease-linear`}
                    style={{
                        width: shrinking ? "0%" : "100%",
                        transitionDuration: shrinking ? `${toast.duration}ms` : "0ms",
                    }}
                />
            </div>
        </div>
    );
}

/** Stack toast cố định góc trên, tự xếp chồng khi có nhiều toast cùng lúc */
export function ToastContainer({ toasts, onDismiss }: { toasts: ToastItem[]; onDismiss: (id: number) => void }) {
    if (toasts.length === 0) return null;
    return (
        <div className="fixed top-6 left-1/2 -translate-x-1/2 z-[60] flex flex-col items-center gap-2 px-4 w-full pointer-events-none">
            {toasts.map((t) => (
                <ToastCard key={t.id} toast={t} onDismiss={onDismiss} />
            ))}
        </div>
    );
}

/** Hook quản lý hàng đợi toast — dùng trong page cần thay alert()/confirm() */
export function useToast() {
    const [toasts, setToasts] = useState<ToastItem[]>([]);
    const idRef = useRef(0);

    const dismissToast = useCallback((id: number) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    const showToast = useCallback((message: string, variant: ToastVariant = "info", duration = 2500) => {
        const id = ++idRef.current;
        setToasts((prev) => [...prev, { id, message, variant, duration }]);
        return id;
    }, []);

    return { toasts, showToast, dismissToast };
}
