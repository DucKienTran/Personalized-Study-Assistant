"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/shared/icons";

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
    { border: string; iconWrap: string; bar: string; icon: string }
> = {
    info: {
        border: "border-primary/25",
        iconWrap: "bg-primary/10 text-primary",
        bar: "bg-primary",
        icon: "info",
    },
    warning: {
        border: "border-accent/30",
        iconWrap: "bg-accent/10 text-accent",
        bar: "bg-accent",
        icon: "warning",
    },
    danger: {
        border: "border-destructive/30",
        iconWrap: "bg-destructive/10 text-destructive",
        bar: "bg-destructive",
        icon: "error_outline",
    },
    success: {
        border: "border-chart-2/30",
        iconWrap: "bg-chart-2/10 text-chart-2",
        bar: "bg-chart-2",
        icon: "check_circle",
    },
};

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
            className={`pointer-events-auto w-full max-w-sm overflow-hidden rounded-xl border bg-card text-card-foreground ${style.border} shadow-lg transition-all duration-300 ease-out ${
                mounted ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-2"
            }`}
        >
            <div className="flex items-start gap-3 p-4">
                <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-[8px] ${style.iconWrap}`}>
                    <Icon name={style.icon} className="text-xl" />
                </span>
                <p className="flex-1 whitespace-pre-line pt-1 text-sm leading-snug text-foreground">{toast.message}</p>
                <button
                    type="button"
                    onClick={() => onDismiss(toast.id)}
                    className="shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                    aria-label="Dismiss notification"
                >
                    <Icon name="close" className="text-base" />
                </button>
            </div>
            <div className="h-1 w-full bg-muted">
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
        <div className="fixed top-6 left-1/2 -translate-x-1/2 z-60 flex flex-col items-center gap-2 px-4 w-full pointer-events-none">
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
