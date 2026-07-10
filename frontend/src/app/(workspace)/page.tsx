"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { userService, UserProfile } from "@/services/user.service";
import { WORKSPACE_FEATURES } from "@/constants/workspace";
import * as Icons from "@/components/shared/icons"; // Gom tất cả icon vào một object để gọi động

// --- SKELETON ---
const WorkspaceSkeleton = () => (
    <div className="max-w-5xl mx-auto space-y-8 pt-4 w-full">
        <div className="space-y-3">
            <div className="h-7 bg-gray-200 rounded-md w-48 animate-pulse"></div>
            <div className="h-4 bg-gray-100 rounded-md w-64 animate-pulse"></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((item) => (
                <div key={item} className="bg-white border border-gray-100 rounded-2xl p-5 h-[200px]">
                    <div className="w-10 h-10 bg-gray-100 rounded-xl mb-4 animate-pulse"></div>
                    <div className="h-5 bg-gray-200 rounded-md w-3/4 mb-3 animate-pulse"></div>
                    <div className="h-3 bg-gray-100 rounded-md w-full animate-pulse mt-2"></div>
                </div>
            ))}
        </div>
    </div>
);

// Hàm tiện ích trả về đúng Icon, màu Icon dựa trên id của hằng số
const renderFeatureIcon = (iconId: string) => {
    switch (iconId) {
        case "summary": return <Icons.DocumentIcon />;
        case "quiz": return <Icons.PenIcon />;
        case "grade": return <Icons.GradeIcon />;
        case "chat": return <Icons.ChatIcon />;
        default: return <Icons.DocumentIcon />;
    }
};

const colorVariants = {
    blue: "bg-blue-50/40 border-blue-100/70 hover:border-blue-300 hover:bg-blue-100/50 text-blue-500",
    purple: "bg-purple-50/40 border-purple-100/70 hover:border-purple-300 hover:bg-purple-100/50 text-purple-500",
    amber: "bg-amber-50/40 border-amber-100/70 hover:border-amber-300 hover:bg-amber-100/50 text-amber-600",
    emerald: "bg-emerald-50/40 border-emerald-100/70 hover:border-emerald-300 hover:bg-emerald-100/50 text-emerald-600",
};


export default function WorkspaceHomePage() {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchUser = async () => {
            try {
                const userData = await userService.getMe();
                setUser(userData);
            } catch (error) {
                console.error("Lỗi thông tin user:", error);
            } finally {
                setLoading(false);
            }
        };
        fetchUser();
    }, []);

    const displayName = user?.full_name || user?.email.split("@")[0] || "bạn";

    if (loading) return <WorkspaceSkeleton />;

    return (
        <div className="max-w-5xl mx-auto space-y-8 pt-4">
            {/* Lời chào đầu trang */}
            <div className="space-y-1.5">
                <h1 className="text-2xl font-bold tracking-tight text-gray-900">Xin chào, {displayName}</h1>
                <p className="text-gray-500 text-xs">Hôm nay bạn muốn xử lý công việc gì?</p>
            </div>

            {/* Grid 4 ô tính năng */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {WORKSPACE_FEATURES.map((feat, index) => {
                    // Lấy chuỗi class tương ứng từ object mapping ở trên
                    const variantClass = colorVariants[feat.color];

                    return (
                        <Link
                            key={index}
                            href={feat.href}
                            className={`group border rounded-2xl p-5 flex flex-col h-[200px] transition-all duration-300 shadow-sm cursor-pointer hover:shadow-md hover:-translate-y-1 overflow-hidden ${variantClass}`}
                        >
                            <div>
                                <span className="p-2.5 bg-white/80 rounded-xl inline-block mb-3 border border-inherit shadow-sm transition-transform duration-300 group-hover:scale-110 text-inherit">
                                    {renderFeatureIcon(feat.iconId)}
                                </span>
                                <h3 className="font-bold text-gray-900 text-base mb-2">{feat.title}</h3>
                                <p className="text-[13px] text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity duration-300 ease-out pointer-events-none line-clamp-3">
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