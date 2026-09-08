"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import axios from "axios";
import { AccessNotFound } from "@/components/shared/AccessNotFound";
import { Icon } from "@/components/shared/icons";
import { Button } from "@/components/ui/button";
import { notebookService } from "@/services/notebook.service";
import { NotebookDetailOut } from "@/types/notebook";
import { NotebookSidebar } from "@/components/notebooks/NotebookSidebar";
import { AddDocumentModal } from "@/components/notebooks/AddDocumentModal";
import { CreateNotebookModal } from "@/components/notebooks/CreateNotebookModal";
import { AssistantTab } from "@/components/notebooks/AssistantTab";
import { SummaryTab } from "@/components/notebooks/SummaryTab";
import { QuizzesTab } from "@/components/notebooks/QuizzesTab";
import { MindmapTab } from "@/components/notebooks/MindmapTab";
import { FlashcardsTab } from "@/components/flashcards/FlashcardsTab";
import { usePdfViewer } from "@/contexts/pdf-viewer-context";
import { AssistantSendRequest } from "@/types/chat";


export default function NotebookDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const notebookId = Number(params.id);
  const { isOpen: isPdfViewerOpen, openDocument } = usePdfViewer();
  const previousPdfViewerOpenRef = useRef(isPdfViewerOpen);

  const [notebook, setNotebook] = useState<NotebookDetailOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accessNotFound, setAccessNotFound] = useState(false);

  // Tab State
  const requestedTab = searchParams.get("tab");
  const activeTab = [
    "assistant",
    "summary",
    "quizzes",
    "flashcards",
    "mindmap",
  ].includes(requestedTab ?? "")
    ? (requestedTab as
        | "assistant"
        | "summary"
        | "quizzes"
        | "flashcards"
        | "mindmap")
    : "assistant";
  const requestedQuizId = Number(searchParams.get("quizId"));
  const selectedQuizId =
    Number.isInteger(requestedQuizId) &&
    requestedQuizId > 0
      ? requestedQuizId
      : null;
  const requestedSummaryId = Number(searchParams.get("summaryId"));
  const selectedSummaryId = Number.isInteger(requestedSummaryId) && requestedSummaryId > 0
    ? requestedSummaryId
    : null;
  const requestedMindmapId = Number(searchParams.get("mindmapId"));
  const selectedMindmapId = Number.isInteger(requestedMindmapId) && requestedMindmapId > 0
    ? requestedMindmapId
    : null;
  const requestedDeckId = Number(searchParams.get("deckId"));
  const selectedDeckId = Number.isInteger(requestedDeckId) && requestedDeckId > 0
    ? requestedDeckId
    : null;
  const startSelectedDeckStudy = searchParams.get("study") === "1";
  const [isAddDocModalOpen, setIsAddDocModalOpen] = useState(false);
  const [isEditNotebookModalOpen, setIsEditNotebookModalOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [assistantSendRequest, setAssistantSendRequest] =
    useState<AssistantSendRequest | null>(null);

  useLayoutEffect(() => {
    const wasOpen = previousPdfViewerOpenRef.current;
    if (isPdfViewerOpen) {
      setIsSidebarOpen(false);
    } else if (wasOpen) {
      setIsSidebarOpen(true);
    }
    previousPdfViewerOpenRef.current = isPdfViewerOpen;
  }, [isPdfViewerOpen]);

  const replaceWorkspaceQuery = (nextParams: URLSearchParams) => {
    const queryString = nextParams.toString();
    router.replace(
      `/notebooks/${notebookId}${queryString ? `?${queryString}` : ""}`,
      { scroll: false }
    );
  };

  const handleTabChange = (
    tab: "assistant" | "summary" | "quizzes" | "flashcards" | "mindmap"
  ) => {
    const nextParams = new URLSearchParams(searchParams.toString());
    nextParams.set("tab", tab);
    replaceWorkspaceQuery(nextParams);
  };

  const handleSelectQuiz = (quizId: number) => {
    const nextParams = new URLSearchParams(searchParams.toString());
    nextParams.set("tab", "quizzes");
    nextParams.set("quizId", String(quizId));
    replaceWorkspaceQuery(nextParams);
  };

  const handleCloseQuiz = () => {
    const nextParams = new URLSearchParams(searchParams.toString());
    nextParams.set("tab", "quizzes");
    nextParams.delete("quizId");
    replaceWorkspaceQuery(nextParams);
  };

  const handleCloseResource = (
    parameter: "summaryId" | "mindmapId" | "deckId"
  ) => {
    const nextParams = new URLSearchParams(searchParams.toString());
    nextParams.delete(parameter);
    replaceWorkspaceQuery(nextParams);
  };

  const handleExplainQuestion = async (
    content: string,
    sourceDocumentIds: number[]
  ) => {
    if (!notebook) return;

    const sourceIdSet = new Set(sourceDocumentIds);
    const inactiveSourceIds = notebook.documents
      .filter(
        (item) => sourceIdSet.has(item.document.id) && !item.is_active
      )
      .map((item) => item.document.id);

    try {
      await Promise.all(
        inactiveSourceIds.map((documentId) =>
          notebookService.toggleDocumentActive(notebookId, documentId, {
            is_active: true,
          })
        )
      );

      if (inactiveSourceIds.length > 0) {
        const activatedIds = new Set(inactiveSourceIds);
        setNotebook((current) => {
          if (!current) return current;
          const documents = current.documents.map((item) =>
            activatedIds.has(item.document.id)
              ? { ...item, is_active: true }
              : item
          );
          return {
            ...current,
            documents,
            active_document_count: documents.filter((item) => item.is_active).length,
          };
        });
      }
    } catch (activationError) {
      console.error("Failed to activate source documents:", activationError);
      await fetchDetail();
      alert("The source documents could not be activated. Please try again.");
      return;
    }

    setAssistantSendRequest({ id: crypto.randomUUID(), content });
    const nextParams = new URLSearchParams(searchParams.toString());
    nextParams.set("tab", "assistant");
    replaceWorkspaceQuery(nextParams);
  };

  const fetchDetail = async () => {
    if (!Number.isInteger(notebookId) || notebookId <= 0) {
      setAccessNotFound(true);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setAccessNotFound(false);
      const data = await notebookService.getNotebookDetail(notebookId);
      if (!data) {
        setAccessNotFound(true);
        return;
      }
      setNotebook(data);
    } catch (err: unknown) {
      console.error("Failed to load notebook detail:", err);
      if (axios.isAxiosError(err) && (err.response?.status === 403 || err.response?.status === 404)) {
        setAccessNotFound(true);
      } else {
        setError("Failed to load notebook detail. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchDetail();
  }, [notebookId]);

  const hasProcessingDocument = notebook?.documents.some(({ document }) =>
    document.status === "pending" || document.status === "processing"
  ) ?? false;

  useEffect(() => {
    if (!hasProcessingDocument) return;
    let cancelled = false;

    const timer = window.setInterval(() => {
      notebookService
        .getNotebookDetail(notebookId)
        .then((data) => {
          if (!cancelled) setNotebook(data);
        })
        .catch(() => undefined);
    }, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [hasProcessingDocument, notebookId]);

  const handleToggleDoc = async (docId: number, currentActive: boolean) => {
    if (!notebook) return;
    const nextActiveState = !currentActive;

    setNotebook((prev) => {
      if (!prev) return prev;
      const updatedDocs = prev.documents.map((item) => {
        if (item.document.id === docId) {
          return { ...item, is_active: nextActiveState };
        }
        return item;
      });
      const activeCount = updatedDocs.filter((d) => d.is_active).length;
      return {
        ...prev,
        documents: updatedDocs,
        active_document_count: activeCount,
      };
    });

    try {
      await notebookService.toggleDocumentActive(notebookId, docId, {
        is_active: nextActiveState,
      });
    } catch (err) {
      console.error("Failed to toggle document active:", err);
      fetchDetail();
    }
  };

  const handleDeleteDoc = async (docId: number) => {
    if (!confirm("Remove this document from the notebook? The original file will remain in your library.")) {
      return;
    }

    try {
      await notebookService.removeDocument(notebookId, docId);
      setNotebook((current) => {
        if (!current) return current;
        const removed = current.documents.find((item) => item.document.id === docId);
        return {
          ...current,
          documents: current.documents.filter((item) => item.document.id !== docId),
          active_document_count:
            current.active_document_count - (removed?.is_active ? 1 : 0),
        };
      });
    } catch (err) {
      console.error("Failed to remove document:", err);
      alert("Could not remove this document. Please try again.");
    }
  };

  if (loading) {
    return (
      <div className="h-full w-full flex items-center justify-center">
        <div className="flex items-center gap-2 text-muted-foreground text-xs font-medium">
          <Icon name="progress_activity" className="animate-spin text-lg" />
          Loading notebook workspace...
        </div>
      </div>
    );
  }

  if (accessNotFound) {
    return <AccessNotFound />;
  }

  if (error || !notebook) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-6 text-center">
        <Icon name="error_outline" className="text-3xl text-destructive mb-2" />
        <h3 className="text-sm font-bold text-foreground">Error Loading Notebook</h3>
        <p className="text-xs text-muted-foreground mt-1 mb-4">{error}</p>
        <Button onClick={fetchDetail} variant="outline" className="rounded-[8px] text-xs">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="h-full w-full text-foreground flex flex-col overflow-hidden bg-background">
      <div className="relative flex flex-1 overflow-hidden">
        {/* SIDEBAR TÀI LIỆU */}
        <div
          className={`absolute inset-y-0 left-0 z-30 shrink-0 overflow-hidden transition-[width] duration-[360ms] ease-[cubic-bezier(0.32,0.72,0,1)] md:relative md:z-auto ${
            isSidebarOpen
              ? "w-[min(320px,calc(100vw-3rem))] md:w-[320px]"
              : "w-14"
          }`}
        >
          <NotebookSidebar
            notebook={notebook}
            activeTab={activeTab}
            onTabChange={handleTabChange}
            onOpenAddModal={() => setIsAddDocModalOpen(true)}
            onEditNotebook={() => setIsEditNotebookModalOpen(true)}
            onClose={() => setIsSidebarOpen(false)}
            onExpand={() => setIsSidebarOpen(true)}
            isCollapsed={!isSidebarOpen}
            onViewDoc={(documentId, title) => {
              openDocument({ id: documentId, title });
            }}
            onToggleDoc={handleToggleDoc}
            onDeleteDoc={handleDeleteDoc}
          />
        </div>

        {/* KHUNG CHÍNH WORKSPACE */}
        <main className="relative flex min-w-0 flex-1 flex-col overflow-hidden bg-background">
          {activeTab === "assistant" && (
            <div className="flex min-h-0 flex-1">
              <AssistantTab
                notebookId={notebookId}
                activeDocumentCount={notebook.active_document_count}
                autoSendRequest={assistantSendRequest}
                onAutoSendConsumed={(requestId) =>
                  setAssistantSendRequest((current) =>
                    current?.id === requestId ? null : current
                  )
                }
              />
            </div>
          )}

          {/* TAB 2: SUMMARY COMPONENT */}
          {activeTab === "summary" && (
            <SummaryTab
              notebookId={notebookId}
              activeDocumentCount={notebook.active_document_count}
              selectedSummaryId={selectedSummaryId}
            />
          )}

          {/* TAB 3: QUIZZES */}
          {(activeTab === "quizzes" || selectedQuizId !== null) && (
            <div
              className={
                activeTab === "quizzes"
                  ? "flex min-h-0 flex-1"
                  : "hidden"
              }
            >
              <QuizzesTab
                notebookId={notebookId}
                activeDocumentCount={notebook.active_document_count}
                selectedQuizId={selectedQuizId}
                onSelectQuiz={handleSelectQuiz}
                onCloseQuiz={handleCloseQuiz}
                onExplainQuestion={handleExplainQuestion}
                onQuizCreated={() =>
                  setNotebook((current) =>
                    current
                      ? { ...current, quiz_count: current.quiz_count + 1 }
                      : current
                  )
                }
              />
            </div>
          )}

          {/* TAB 4: FLASHCARDS */}
          {activeTab === "flashcards" && (
            <FlashcardsTab
              notebookId={notebookId}
              activeDocumentCount={notebook.active_document_count}
              onExplainCard={handleExplainQuestion}
              selectedDeckId={selectedDeckId}
              startSelectedDeckStudy={startSelectedDeckStudy}
              onSelectDeck={(deckId) => {
                const nextParams = new URLSearchParams(searchParams.toString());
                nextParams.set("tab", "flashcards");
                nextParams.set("deckId", String(deckId));
                replaceWorkspaceQuery(nextParams);
              }}
              onCloseDeck={() => handleCloseResource("deckId")}
            />
          )}

          {/* TAB 5: MINDMAP */}
          {activeTab === "mindmap" && (
            <MindmapTab
              notebookId={notebookId}
              eligibleDocumentCount={notebook.documents.filter(
                ({ document, is_active }) => is_active && document.status === "completed"
              ).length}
              selectedMindmapId={selectedMindmapId}
            />
          )}

        </main>
      </div>

      <CreateNotebookModal
        isOpen={isEditNotebookModalOpen}
        initialNotebook={notebook}
        onClose={() => setIsEditNotebookModalOpen(false)}
        onSuccess={(updated) =>
          setNotebook((current) =>
            current
              ? {
                  ...current,
                  title: updated.title,
                  description: updated.description,
                  color: updated.color,
                  updated_at: updated.updated_at,
                }
              : current
          )
        }
      />

      {/* MODAL ADD DOCUMENT */}
      <AddDocumentModal
        isOpen={isAddDocModalOpen}
        notebookId={notebookId}
        existingDocIdsInNotebook={notebook.documents.map((d) => d.document.id)}
        onClose={() => setIsAddDocModalOpen(false)}
        onSuccess={fetchDetail}
      />
    </div>
  );
}
