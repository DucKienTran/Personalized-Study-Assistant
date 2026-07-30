"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";

import UploadModal from "@/components/shared/UploadModal";
import { DocumentListItem } from "@/services/document.service";
import { useAuth } from "@/hooks/useAuth";
import { PdfViewerProvider, usePdfViewer } from "@/contexts/pdf-viewer-context";
import { PdfViewerPanel } from "@/components/pdf-viewer/pdf-viewer-panel";
import { UserIcon, KeyIcon, LogoutIcon } from "@/components/shared/icons";

const HomeIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
        <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
    </svg>
);

const LibraryIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
    </svg>
);

const DashboardIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6a7.5 7.5 0 1 0 7.5 7.5h-7.5V6Z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 10.5H21A7.5 7.5 0 0 0 13.5 3v7.5Z" />
    </svg>
);

const HistoryIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
);

function SplitPane({ children }: { children: React.ReactNode }) {
    const { isOpen } = usePdfViewer();
    const [panelWidth, setPanelWidth] = useState(480);
    const isDragging = useRef(false);

    const startDrag = () => {
        isDragging.current = true;

        const onMove = (e: MouseEvent) => {
            if (!isDragging.current) return;

            const newWidth = window.innerWidth - e.clientX;
            setPanelWidth(Math.min(800, Math.max(320, newWidth)));
        };

        const onUp = () => {
            isDragging.current = false;
            window.removeEventListener("mousemove", onMove);
            window.removeEventListener("mouseup", onUp);
        };

        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
    };

    const showPanel = isOpen;

    return (
        <div className="flex h-full w-full">
            <div className="min-w-0 flex-1">
                {children}
            </div>

            {showPanel && (
                <>
                    <div
                        onMouseDown={startDrag}
                        className="w-1 shrink-0 cursor-col-resize bg-border hover:bg-primary/40"
                    />

                    <div style={{ width: panelWidth }} className="shrink-0">
                        <PdfViewerPanel />
                    </div>
                </>
            )}
        </div>
    );
}

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const { currentUser, authenticated, loading, logout } = useAuth();

    const [isHovered, setIsHovered] = useState(false);
    const [isHistoryOpen, setIsHistoryOpen] = useState(false);
    const [isProfileOpen, setIsProfileOpen] = useState(false);
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

    const hoverTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const profileRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!loading && !authenticated) {
            router.replace("/login");
        }
    }, [authenticated, loading, router]);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
                setIsProfileOpen(false);
            }
        }

        document.addEventListener("mousedown", handleClickOutside);

        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    useEffect(() => {
        const handleOpenModal = () => setIsUploadModalOpen(true);

        window.addEventListener("open-upload-modal", handleOpenModal);

        return () => window.removeEventListener("open-upload-modal", handleOpenModal);
    }, []);

    if (loading || !authenticated) {
        return null;
    } const handleMouseEnter = () => {
        if (hoverTimeoutRef.current) {
            clearTimeout(hoverTimeoutRef.current);
        }

        hoverTimeoutRef.current = setTimeout(() => {
            setIsHovered(true);
        }, 300);
    };

    const handleMouseLeave = () => {
        if (hoverTimeoutRef.current) {
            clearTimeout(hoverTimeoutRef.current);
        }

        setIsHovered(false);
    };

    const handleLogout = async () => {
        await logout();
        router.replace("/login");
    };

    const handleUploaded = (doc: DocumentListItem) => {
        setIsUploadModalOpen(false);
        router.push(`/documents/${doc.id}/summary`);
    };

    const menus = [
        {
            name: "Trang chủ",
            href: "/",
            icon: <HomeIcon />,
        },
        {
            name: "Thư viện của tôi",
            href: "/documents",
            icon: <LibraryIcon />,
        },
        {
            name: "Thống kê",
            href: "/dashboard",
            icon: <DashboardIcon />,
        },
    ];

    const avatarLetter =
        (currentUser?.full_name ?? currentUser?.email)
            ?.charAt(0)
            .toUpperCase() ?? "U";

    return (
        <PdfViewerProvider>
            <div className="flex h-screen bg-gray-50 overflow-hidden text-sm">
                <aside
                    onMouseEnter={handleMouseEnter}
                    onMouseLeave={handleMouseLeave}
                    className={`bg-white border-r flex flex-col justify-between hidden md:flex p-4 transition-all duration-300 ease-in-out z-20 ${isHovered ? "w-64 shadow-lg" : "w-20"
                        }`}
                >
                    <div className="space-y-6">
                        <div className="h-8 flex items-center px-2 overflow-hidden">
                            <span
                                className={`text-2xl font-bold text-[#3b7a52] transition-opacity duration-200 ${isHovered
                                        ? "opacity-100"
                                        : "opacity-0 pointer-events-none"
                                    }`}
                            >
                                Learning Aid
                            </span>
                        </div>

                        <button
                            onClick={() =>
                                window.dispatchEvent(
                                    new Event("open-upload-modal")
                                )
                            }
                            className={`bg-[#e6f4ea] hover:bg-[#cbdcd0] text-[#2e5f3f] flex items-center justify-center transition-all duration-300 shadow-xs overflow-hidden ${isHovered
                                    ? "w-full h-11 px-4 py-3 rounded-xl justify-start space-x-3"
                                    : "w-11 h-11 rounded-xl mx-auto"
                                }`}
                        >
                            <span className="font-bold text-3xl">
                                ＋
                            </span>

                            {isHovered && (
                                <span className="font-semibold text-sm whitespace-nowrap uppercase tracking-wider">
                                    Upload
                                </span>
                            )}
                        </button>

                        <nav className="space-y-1">
                            {menus.map((menu) => (
                                <Link
                                    key={menu.href}
                                    href={menu.href}
                                    className={`flex items-center rounded-xl transition-all duration-200 ${isHovered
                                            ? "px-3 py-2.5"
                                            : "w-11 h-11 justify-center mx-auto"
                                        } ${pathname === menu.href
                                            ? "bg-[#e6f4ea] text-[#2e5f3f] font-semibold"
                                            : "text-gray-600 hover:bg-gray-50"
                                        }`}
                                >
                                    {isHovered && (
                                        <div className="w-5" />
                                    )}

                                    <span className="flex items-center justify-center">
                                        {menu.icon}
                                    </span>

                                    {isHovered && (
                                        <span className="ml-3 whitespace-nowrap font-medium text-gray-700">
                                            {menu.name}
                                        </span>
                                    )}
                                </Link>
                            ))}

                            <div className="pt-2 border-t border-gray-100 mt-2">
                                <button
                                    onClick={() =>
                                        isHovered &&
                                        setIsHistoryOpen(!isHistoryOpen)
                                    }
                                    className={`w-full flex items-center rounded-xl text-gray-600 hover:bg-gray-50 transition-all duration-200 ${isHovered
                                            ? "px-3 py-2.5"
                                            : "w-11 h-11 justify-center mx-auto"
                                        }`}
                                >
                                    {isHovered && (
                                        <div className="w-5 flex items-center justify-start">
                                            <span
                                                className={`text-base font-bold text-gray-400 transition-transform duration-200 ${isHistoryOpen
                                                        ? "rotate-90"
                                                        : ""
                                                    }`}
                                            >
                                                ▸
                                            </span>
                                        </div>
                                    )}

                                    <span className="flex items-center justify-center">
                                        <HistoryIcon />
                                    </span>

                                    {isHovered && (
                                        <span className="ml-3 whitespace-nowrap font-medium text-gray-700">
                                            Lịch sử
                                        </span>
                                    )}
                                </button>

                                {isHovered && isHistoryOpen && (
                                    <div className="mt-1 ml-11 pl-3 border-l border-gray-200 space-y-1 py-1">
                                        <Link
                                            href="/history/summary"
                                            className="block px-3 py-1.5 text-xs text-gray-500 hover:text-[#2e5f3f] hover:bg-gray-50 rounded-md"
                                        >
                                            Tóm tắt
                                        </Link>

                                        <Link
                                            href="/history/quizzes"
                                            className="block px-3 py-1.5 text-xs text-gray-500 hover:text-[#2e5f3f] hover:bg-gray-50 rounded-md"
                                        >
                                            Bài kiểm tra
                                        </Link>

                                        <Link
                                            href="/history/chat"
                                            className="block px-3 py-1.5 text-xs text-gray-500 hover:text-[#2e5f3f] hover:bg-gray-50 rounded-md"
                                        >
                                            Hỏi đáp
                                        </Link>
                                    </div>
                                )}
                            </div>
                        </nav>
                    </div>

                    <div
                        className={`group relative flex items-center justify-between px-2 transition-opacity duration-200 cursor-pointer hover:bg-gray-50 rounded-lg py-2 ${isHovered
                                ? "opacity-100"
                                : "opacity-0 pointer-events-none"
                            }`}
                        onClick={handleLogout}
                    >
                        <div className="text-xs text-gray-400 truncate max-w-[140px]">
                            {currentUser?.email}
                        </div>

                        <span className="text-[11px] text-red-500 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                            Rời đi
                        </span>
                    </div>
                </aside>
                <div className="flex-1 relative flex flex-col overflow-hidden">
                    <div ref={profileRef} className="absolute top-6 right-8 z-30">
                        <button
                            onClick={() => setIsProfileOpen(!isProfileOpen)}
                            className="w-10 h-10 rounded-full bg-[#e6f4ea] text-[#2e5f3f] flex items-center justify-center font-bold text-base shadow-xs border-4 border-white cursor-pointer hover:bg-[#cbdcd0] transition-all duration-200 focus:outline-hidden"
                            title={`Tài khoản: ${currentUser?.email}`}
                        >
                            {avatarLetter}
                        </button>

                        {isProfileOpen && (
                            <div className="absolute right-0 mt-2 w-48 bg-white border border-gray-100 rounded-xl shadow-lg py-1 z-50 text-xs animate-fadeIn">
                                <div className="px-4 py-2 border-b border-gray-50">
                                    <p className="font-semibold text-gray-800 truncate">
                                        {currentUser?.full_name || "Người dùng"}
                                    </p>

                                    <p className="text-[10px] text-gray-400 truncate">
                                        {currentUser?.email}
                                    </p>
                                </div>

                                <Link
                                    href="/profile"
                                    onClick={() => setIsProfileOpen(false)}
                                    className="flex items-center px-4 py-2 text-gray-600 hover:bg-gray-50 transition-colors"
                                >
                                    <UserIcon className="w-4 h-4 mr-2.5 text-gray-400" />
                                    Hồ sơ cá nhân
                                </Link>

                                <Link
                                    href="/change-password"
                                    onClick={() => setIsProfileOpen(false)}
                                    className="flex items-center px-4 py-2 text-gray-600 hover:bg-gray-50 transition-colors"
                                >
                                    <KeyIcon className="w-4 h-4 mr-2.5 text-gray-400" />
                                    Đổi mật khẩu
                                </Link>

                                <div className="border-t border-gray-100 my-1" />

                                <button
                                    onClick={() => {
                                        setIsProfileOpen(false);
                                        handleLogout();
                                    }}
                                    className="w-full flex items-center text-left px-4 py-2 text-red-500 hover:bg-red-50/40 transition-colors font-medium"
                                >
                                    <LogoutIcon className="w-4 h-4 mr-2.5 text-red-400" />
                                    Đăng xuất
                                </button>
                            </div>
                        )}
                    </div>

                    <main className="flex-1 overflow-hidden bg-gray-50">
                        <SplitPane>
                            <div className="h-full overflow-y-auto p-8 pt-20">
                                {children}
                            </div>
                        </SplitPane>
                    </main>
                </div>

                <UploadModal
                    isOpen={isUploadModalOpen}
                    onClose={() => setIsUploadModalOpen(false)}
                    onUploaded={handleUploaded}
                />
            </div>
        </PdfViewerProvider>
    );
}