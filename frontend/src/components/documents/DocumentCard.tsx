"use client";

import * as Icons from "@/components/shared/icons";
import { DocumentListItem } from "@/services/document.service";

interface Props {
    document: DocumentListItem;
    selected?: boolean;
    onClick: () => void;
}

const STATUS = {
    pending: {
        text: "Pending",
        className: "bg-gray-100 text-gray-600",
    },
    completed: {
        text: "Completed",
        className: "bg-blue-50 text-blue-600",
    },
    failed: {
        text: "Failed",
        className: "bg-red-50 text-red-600",
    },
};

export default function DocumentCard({
    document,
    selected = false,
    onClick,
}: Props) {
    const status =
        STATUS[document.status as keyof typeof STATUS] ??
        STATUS.pending;

    return (
        <button
            type="button"
            onClick={onClick}
            className={[
                "w-full rounded-2xl border p-4 transition text-left",
                selected
                    ? "border-purple-500 bg-purple-50"
                    : "border-gray-100 bg-white hover:border-purple-300 hover:bg-purple-50/40",
            ].join(" ")}
        >
            <div className="flex items-center justify-between">

                <div className="flex gap-3 min-w-0">

                    <span className="rounded-xl bg-blue-50 p-2 text-blue-600 shrink-0">
                        <Icons.DocumentIcon className="w-5 h-5" />
                    </span>

                    <div className="min-w-0">

                        <h3 className="truncate font-medium text-sm text-gray-900">
                            {document.title}
                        </h3>

                        {document.created_at && (
                            <p className="mt-1 text-xs text-gray-400">
                                {new Date(
                                    document.created_at
                                ).toLocaleDateString("vi-VN")}
                            </p>
                        )}

                    </div>

                </div>

                <span
                    className={[
                        "rounded-full px-2.5 py-1 text-[11px] font-medium shrink-0",
                        status.className,
                    ].join(" ")}
                >
                    {status.text}
                </span>

            </div>
        </button>
    );
}