"use client";

import Link from "next/link";
import * as Icons from "@/components/shared/icons";
import { WORKSPACE_FEATURES } from "@/constants/workspace";
import { useAuth } from "@/hooks/useAuth";

// --- SKELETON ---
const WorkspaceSkeleton = () => (
    <div className="max-w-5xl mx-auto space-y-8 pt-4 w-full">
        <div className="space-y-3">
            <div className="h-7 bg-gray-200 rounded-md w-48 animate-pulse"></div>
            <div className="h-4 bg-gray-100 rounded-md w-64 animate-pulse"></div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((item) => (
                <div
                    key={item}
                    className="bg-white border border-gray-100 rounded-2xl p-5 h-[200px]"
                >
                    <div className="w-10 h-10 bg-gray-100 rounded-xl mb-4 animate-pulse"></div>
                    <div className="h-5 bg-gray-200 rounded-md w-3/4 mb-3 animate-pulse"></div>
                    <div className="h-3 bg-gray-100 rounded-md w-full mt-2 animate-pulse"></div>
                </div>
            ))}
        </div>
    </div>
);

const renderFeatureIcon = (iconId: string) => {
    switch (iconId) {
        case "summary":
            return <Icons.DocumentIcon />;
        case "quiz":
            return <Icons.PenIcon />;
        case "grade":
            return <Icons.GradeIcon />;
        case "chat":
            return <Icons.ChatIcon />;
        default:
            return <Icons.DocumentIcon />;
    }
};

const colorVariants = {
    blue: "bg-blue-50/40 border-blue-100/70 hover:border-blue-300 hover:bg-blue-100/50 text-blue-500",
    purple:
        "bg-purple-50/40 border-purple-100/70 hover:border-purple-300 hover:bg-purple-100/50 text-purple-500",
    amber:
        "bg-amber-50/40 border-amber-100/70 hover:border-amber-300 hover:bg-amber-100/50 text-amber-600",
    emerald:
        "bg-emerald-50/40 border-emerald-100/70 hover:border-emerald-300 hover:bg-emerald-100/50 text-emerald-600",
} as const;

export default function WorkspaceHomePage() {
    const { currentUser, loading } = useAuth();

    const displayName =
        currentUser?.full_name ??
        currentUser?.email?.split("@")[0] ??
        "bạn";

    if (loading) {
        return <WorkspaceSkeleton />;
    }

    return (
        <div className="max-w-5xl mx-auto space-y-8 pt-4">
            <div className="space-y-1.5">
                <h1 className="text-2xl font-bold tracking-tight text-gray-900">
                    Xin chào, {displayName}
                </h1>

                <p className="text-xs text-gray-500">
                    Hôm nay bạn muốn xử lý công việc gì?
                </p>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
                {WORKSPACE_FEATURES.map((feat) => {
                    const variantClass =
                        colorVariants[
                            feat.color as keyof typeof colorVariants
                        ];

                    return (
                        <Link
                            key={feat.href}
                            href={feat.href}
                            className={`group flex h-[200px] flex-col overflow-hidden rounded-2xl border p-5 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-md ${variantClass}`}
                        >
                            <div>
                                <span className="mb-3 inline-block rounded-xl border border-inherit bg-white/80 p-2.5 shadow-sm transition-transform duration-300 group-hover:scale-110">
                                    {renderFeatureIcon(feat.iconId)}
                                </span>

                                <h3 className="mb-2 text-base font-bold text-gray-900">
                                    {feat.title}
                                </h3>

                                <p className="pointer-events-none line-clamp-3 text-[13px] text-gray-500 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
                                    {feat.description}
                                </p>
                            </div>
                        </Link>
                    );
                })}
            </div>
        </div>
    );
}