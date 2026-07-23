"use client";

import React, { useEffect, useRef, useState } from "react";

/**
 * Nút "bấm 2 lần để xác nhận" — thay window.confirm() native.
 * Lý do: confirm() gây window.blur giả trong lúc Exam Mode đang theo dõi chống gian lận.
 *
 * Lần bấm 1: đổi label + màu cảnh báo, khởi động đếm ngược armWindowMs.
 * Lần bấm 2 (trong lúc đang "armed"): mới thực sự gọi onConfirm.
 * Hết armWindowMs mà không bấm tiếp: tự revert về trạng thái ban đầu.
 */
interface ConfirmButtonProps {
    idleLabel: string;
    armedLabel: string; // vd: "Bấm lần nữa để xác nhận nộp bài"
    onConfirm: () => void;
    className?: string; // style riêng ở trạng thái idle, ví dụ màu theo ngữ cảnh (xanh cho nộp bài, đỏ cho thoát)
    armedClassName?: string; // style riêng ở trạng thái armed
    armWindowMs?: number;
    disabled?: boolean;
}

export default function ConfirmButton({
    idleLabel,
    armedLabel,
    onConfirm,
    className = "bg-emerald-600 hover:bg-emerald-700 text-white",
    armedClassName = "bg-amber-500 hover:bg-amber-600 text-white",
    armWindowMs = 4000,
    disabled = false,
}: ConfirmButtonProps) {
    const [armed, setArmed] = useState(false);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        return () => {
            if (timerRef.current) clearTimeout(timerRef.current);
        };
    }, []);

    const handleClick = () => {
        if (disabled) return;

        if (!armed) {
            setArmed(true);
            timerRef.current = setTimeout(() => setArmed(false), armWindowMs);
            return;
        }

        if (timerRef.current) clearTimeout(timerRef.current);
        setArmed(false);
        onConfirm();
    };

    return (
        <button
            type="button"
            disabled={disabled}
            onClick={handleClick}
            className={`px-4 py-2 rounded-xl text-xs font-bold shadow-sm transition-all duration-150 transform active:scale-95 disabled:opacity-50 disabled:pointer-events-none cursor-pointer ${
                armed ? `${armedClassName} animate-pulse` : className
            }`}
        >
            {armed ? armedLabel : idleLabel}
        </button>
    );
}
