"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useState,
} from "react";

import { CitationSource } from "@/types/chat";

interface ViewerState {
  isOpen: boolean;

  isThumbnailOpen: boolean;

  documentId: number | null;

  documentTitle: string | null;

  currentPage: number;

  targetSnippet: string | null;

  targetHeaderPath: string[];

  chunkId: string | null;

  highlightRequestId: number;
}

interface PdfViewerContextValue extends ViewerState {
  openCitation: (source: CitationSource) => void;

  openDocument: (document: { id: number; title: string }) => void;

  closeViewer: () => void;

  toggleViewer: () => void;

  toggleThumbnail: () => void;

  setCurrentPage: (page: number) => void;
}


const PdfViewerContext =
  createContext<PdfViewerContextValue | null>(null);


const DEFAULT_STATE: ViewerState = {
  isOpen: false,

  isThumbnailOpen: true,

  documentId: null,

  documentTitle: null,

  currentPage: 1,

  targetSnippet: null,

  targetHeaderPath: [],

  chunkId: null,

  highlightRequestId: 0,
};


export function PdfViewerProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [state, setState] =
    useState<ViewerState>(DEFAULT_STATE);


  const openCitation = useCallback(
    (source: CitationSource) => {
      setState((prev) => ({
        ...prev,

        isOpen: true,

        documentId: source.documentId,

        documentTitle: source.documentTitle,

        currentPage: source.pageStart,

        targetSnippet: source.snippet ?? null,

        targetHeaderPath: source.headerPath,

        chunkId: source.chunkId,

        // force viewer react even when same page
        highlightRequestId:
          prev.highlightRequestId + 1,
      }));
    },
    []
  );

  const openDocument = useCallback(
    (document: { id: number; title: string }) => {
      setState((prev) => ({
        ...prev,
        isOpen: true,
        documentId: document.id,
        documentTitle: document.title,
        currentPage: prev.documentId === document.id ? prev.currentPage : 1,
        targetSnippet: null,

        targetHeaderPath: [],
        chunkId: null,
        highlightRequestId: prev.highlightRequestId + 1,
      }));
    },
    []
  );


  const closeViewer = useCallback(() => {
    setState((prev) => ({
      ...prev,

      isOpen: false,
    }));
  }, []);


  const toggleViewer = useCallback(() => {
    setState((prev) => {
      if (prev.documentId === null) {
        return prev;
      }

      return {
        ...prev,

        isOpen: !prev.isOpen,
      };
    });
  }, []);


  const toggleThumbnail = useCallback(() => {
    setState((prev) => ({
      ...prev,

      isThumbnailOpen:
        !prev.isThumbnailOpen,
    }));
  }, []);


  const setCurrentPage = useCallback(
    (page: number) => {
      setState((prev) => ({
        ...prev,

        currentPage: page,
      }));
    },
    []
  );


  return (
    <PdfViewerContext.Provider
      value={{
        ...state,

        openCitation,

        openDocument,

        closeViewer,

        toggleViewer,

        toggleThumbnail,

        setCurrentPage,
      }}
    >
      {children}
    </PdfViewerContext.Provider>
  );
}


export function usePdfViewer() {
  const context =
    useContext(PdfViewerContext);


  if (!context) {
    throw new Error(
      "usePdfViewer must be used within PdfViewerProvider"
    );
  }


  return context;
}
