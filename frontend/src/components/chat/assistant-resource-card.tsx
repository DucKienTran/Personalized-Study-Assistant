"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/shared/icons";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { flashcardService, type FlashcardDeckDetail } from "@/services/flashcard.service";
import { quizService, type QuizDetail } from "@/services/quiz.service";
import type { AssistantResource } from "@/types/assistant-resource";
import { AssistantThinkingText } from "./assistant-thinking-text";

interface AssistantResourceCardProps {
  resource: AssistantResource;
}

const POLL_INTERVAL_MS = 1750;

export function AssistantResourceCard({ resource }: AssistantResourceCardProps) {
  const router = useRouter();
  const [quiz, setQuiz] = useState<QuizDetail | null>(null);
  const [deck, setDeck] = useState<FlashcardDeckDetail | null>(null);
  const [examDialogOpen, setExamDialogOpen] = useState(false);
  const persistedStatus = resource.metadata?.generationStatus;

  useEffect(() => {
    if (
      persistedStatus !== "processing" ||
      (resource.resourceType !== "quiz" && resource.resourceType !== "flashcards")
    ) {
      return;
    }

    let mounted = true;
    let timer: number | undefined;

    const poll = async () => {
      try {
        if (resource.resourceType === "quiz") {
          const nextQuiz = await quizService.getQuiz(Number(resource.resourceId));
          if (!mounted) return;
          setQuiz(nextQuiz);
          if (nextQuiz.generation_status !== "processing") return;
        } else {
          const nextDeck = await flashcardService.getDeck(Number(resource.resourceId));
          if (!mounted) return;
          setDeck(nextDeck);
          if (nextDeck.generation_status !== "processing") return;
        }
      } catch {
        if (!mounted) return;
      }

      timer = window.setTimeout(poll, POLL_INTERVAL_MS);
    };

    void poll();
    return () => {
      mounted = false;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [persistedStatus, resource.resourceId, resource.resourceType]);

  const runtimeStatus = quiz?.generation_status ?? deck?.generation_status;
  const generationStatus = runtimeStatus ?? persistedStatus;
  const isProcessing = generationStatus === "processing";
  const isFailed = generationStatus === "failed";
  const title = quiz?.title ?? deck?.title ?? resource.title;
  const isActionResource = resource.resourceType === "quiz" || resource.resourceType === "flashcards";

  const openViewResource = () => {
    const params = new URLSearchParams();
    params.set("tab", resource.resourceType);
    params.set(
      resource.resourceType === "summary" ? "summaryId" : "mindmapId",
      resource.resourceId
    );
    router.push(`/notebooks/${resource.notebookId}?${params.toString()}`);
  };

  const handleAction = () => {
    if (resource.resourceType === "quiz") {
      if (quiz?.mode === "exam") {
        setExamDialogOpen(true);
      } else {
        router.push(`/quizzes/${resource.resourceId}`);
      }
      return;
    }

    router.push(
      `/notebooks/${resource.notebookId}?tab=flashcards&deckId=${resource.resourceId}&study=1`
    );
  };

  const iconName = {
    quiz: "quiz",
    flashcards: "style",
    summary: "summarize",
    mindmap: "account_tree",
  }[resource.resourceType];

  const detail = resource.resourceType === "quiz"
    ? quiz
      ? `${quiz.total_questions} questions · ${quiz.mode === "exam" ? "Exam" : "Study"}`
      : "Quiz generated from your active sources."
    : resource.resourceType === "flashcards"
      ? deck ? `${deck.card_count} cards` : "Flashcards generated from your active sources."
      : resource.resourceType === "summary"
        ? "Summary generated from your active sources."
        : "Mindmap generated from your active sources.";
  const generatingText = {
    quiz: "Generating quiz...",
    flashcards: "Generating flashcards...",
    summary: "Generating summary...",
    mindmap: "Generating mindmap...",
  }[resource.resourceType];
  const cardClassName = isFailed
    ? "border-border bg-secondary/40 shadow-2xs"
    : isProcessing
      ? "border-border bg-secondary/30 shadow-2xs"
      : "border-border bg-secondary/50 shadow-xs hover:border-primary/40 hover:bg-secondary/70 hover:shadow-sm";

  return (
    <>
      <div className={`mt-3 w-full max-w-[760px] rounded-[10px] border px-4 py-3 transition-[border-color,background-color,box-shadow] duration-200 ${cardClassName}`}>
        <div className="flex w-fit items-center gap-2 rounded-md border border-border/80 bg-background/70 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground shadow-2xs">
          <Icon
            name={isProcessing && isActionResource ? "progress_activity" : iconName}
            className={isProcessing && isActionResource ? "animate-spin text-base text-primary" : "text-base text-primary"}
          />
          {resource.resourceType}
        </div>

        <p className={`mt-2 text-sm font-normal leading-snug ${isProcessing ? "text-muted-foreground" : "text-foreground"}`}>
          {isFailed
            ? resource.resourceType === "quiz"
              ? "Quiz generation failed"
              : "Flashcard generation failed"
            : title}
        </p>
        {isProcessing ? (
          <p className="mt-1 text-xs italic text-muted-foreground">
            <AssistantThinkingText>{generatingText}</AssistantThinkingText>
          </p>
        ) : (
          <p className="mt-1 text-xs text-muted-foreground">
            {isFailed ? quiz?.error_message ?? deck?.error_message ?? "Please try again later." : detail}
          </p>
        )}

        {!isProcessing && !isFailed && (
          isActionResource ? (
            <Button type="button" variant="link" size="sm" onClick={handleAction} className="mt-2 h-auto p-0 text-xs font-semibold text-primary hover:text-[var(--primary-hover)]">
              {resource.resourceType === "flashcards" ? "Study now →" : quiz?.mode === "exam" ? "Start exam →" : "Start quiz →"}
            </Button>
          ) : (
            <button type="button" onClick={openViewResource} className="mt-2 text-xs font-semibold text-primary transition-colors hover:text-[var(--primary-hover)] hover:underline">
              Click here to view →
            </button>
          )
        )}
      </div>

      <Dialog open={examDialogOpen} onOpenChange={setExamDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Start {quiz?.title ?? "exam"}?</DialogTitle>
            <DialogDescription>
              You&apos;re about to start an exam
              {quiz ? ` with ${quiz.total_questions} questions${quiz.time_limit_minutes ? ` and a ${quiz.time_limit_minutes}-minute time limit` : ""}` : ""}.
              Once you begin, your attempt will start.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setExamDialogOpen(false)}>Cancel</Button>
            <Button type="button" onClick={() => router.push(`/quizzes/${resource.resourceId}/exam`)}>Start exam</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
