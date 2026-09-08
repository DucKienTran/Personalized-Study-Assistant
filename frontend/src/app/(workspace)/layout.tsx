// src/app/(workspace)/layout.tsx
"use client";

import React, { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import UploadModal from "@/components/shared/UploadModal";
import { useAuth } from "@/hooks/useAuth";
import {
  PdfViewerProvider,
  usePdfViewer,
} from "@/contexts/pdf-viewer-context";
import { DocumentViewerPanel } from "@/components/document-viewer/document-viewer-panel";
import { Header } from "@/components/layout/Header";
import { StudyHeartbeat } from "@/components/shared/StudyHeartbeat";

function SplitPane({ children }: { children: React.ReactNode }) {
  const { isOpen } = usePdfViewer();
  const pathname = usePathname();
  const [panelWidth, setPanelWidth] = useState(480);
  const isDragging = useRef(false);
  const showSplitViewer = isOpen && !/^\/library\/[^/]+$/.test(pathname);

  const startDrag = () => {
    isDragging.current = true;

    const onMove = (e: MouseEvent) => {
      if (!isDragging.current) return;

      const newWidth = window.innerWidth - e.clientX;

      // Desktop only: keep the panel reasonable relative to viewport.
      const maxWidth = Math.min(800, window.innerWidth * 0.55);

      setPanelWidth(
        Math.min(maxWidth, Math.max(320, newWidth)),
      );
    };

    const onUp = () => {
      isDragging.current = false;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  return (
    <div className="relative flex h-full min-h-0 w-full min-w-0 overflow-hidden">
      {/* Main page */}
      <div className="min-h-0 min-w-0 flex-1 overflow-hidden">
        {children}
      </div>

      {/* Desktop resize handle */}
      <div
        onMouseDown={showSplitViewer ? startDrag : undefined}
        className={`hidden shrink-0 bg-border transition-[width,opacity] duration-[360ms] ease-[cubic-bezier(0.32,0.72,0,1)] hover:bg-primary/40 lg:block ${
          showSplitViewer
            ? "w-1 cursor-col-resize opacity-100"
            : "pointer-events-none w-0 opacity-0"
        }`}
      />

      {/* Desktop split panel */}
      <div
        aria-hidden={!showSplitViewer}
        style={{ width: showSplitViewer ? panelWidth : 0 }}
        className="hidden shrink-0 overflow-hidden transition-[width] duration-[360ms] ease-[cubic-bezier(0.32,0.72,0,1)] lg:block"
      >
        <div
          style={{ width: panelWidth }}
          className="h-full min-h-0 overflow-hidden"
        >
          <DocumentViewerPanel />
        </div>
      </div>

      {/* Mobile/tablet document viewer overlay */}
      <div
        aria-hidden={!showSplitViewer}
        className={`absolute inset-0 z-40 bg-background transition-[opacity,transform] duration-300 lg:hidden ${
          showSplitViewer
            ? "pointer-events-auto translate-x-0 opacity-100"
            : "pointer-events-none translate-x-full opacity-0"
        }`}
      >
        <div className="h-full min-h-0 w-full overflow-hidden">
          <DocumentViewerPanel />
        </div>
      </div>
    </div>
  );
}

export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { authenticated, loading } = useAuth();

  const isExamRoom = /^\/quizzes\/[^/]+\/exam$/.test(pathname);

  // These pages manage their own internal scrolling.
  const ownsPageScroll = ["/notebooks", "/dashboard", "/admin"].includes(pathname);

  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  // Auth Guard
  useEffect(() => {
    if (loading) return;

    if (!authenticated) {
      router.replace("/login");
      return;
    }

  }, [authenticated, loading, router]);

  // Global Upload Event Listener
  useEffect(() => {
    const handleOpenModal = () => setIsUploadModalOpen(true);

    window.addEventListener("open-upload-modal", handleOpenModal);

    return () => {
      window.removeEventListener("open-upload-modal", handleOpenModal);
    };
  }, []);

  if (loading || !authenticated) {
    return null;
  }

  const handleUploaded = () => {
    setIsUploadModalOpen(false);
    if (pathname === "/library") {
      window.dispatchEvent(new Event("document-uploaded"));
      return;
    }
    router.push("/notebooks?tab=summary");
  };

  return (
    <PdfViewerProvider>
      <StudyHeartbeat />

      <div className="flex h-dvh w-full min-w-0 flex-col overflow-hidden bg-background text-sm">
        {!isExamRoom && <Header />}

        <main className="min-h-0 min-w-0 flex-1 overflow-hidden">
          {isExamRoom ? (
            <div className="h-full min-h-0 overflow-x-hidden overflow-y-auto">
              {children}
            </div>
          ) : (
            <SplitPane>
              <div
                className={`h-full min-h-0 min-w-0 overflow-x-hidden ${
                  ownsPageScroll
                    ? "overflow-y-hidden"
                    : "overflow-y-auto"
                }`}
              >
                {children}
              </div>
            </SplitPane>
          )}
        </main>

        <UploadModal
          isOpen={isUploadModalOpen}
          onClose={() => setIsUploadModalOpen(false)}
          onUploaded={handleUploaded}
        />
      </div>
    </PdfViewerProvider>
  );
}
