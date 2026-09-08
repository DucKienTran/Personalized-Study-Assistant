"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";

import { Button } from "@/components/ui/button";
import { Icon } from "@/components/shared/icons";
import {
  FlashcardRating,
  FlashcardStudySession,
  flashcardService,
} from "@/services/flashcard.service";

interface FlashcardStudyViewProps {
  session: FlashcardStudySession;
  onSessionChange: (session: FlashcardStudySession) => void;
  onBack: () => void;
  onExplainCard?: (content: string, sourceDocumentIds: number[]) => void | Promise<void>;
}

const RATINGS: Array<{
  value: FlashcardRating;
  label: string;
}> = [
  { value: "again", label: "Again" },
  { value: "hard", label: "Hard" },
  { value: "good", label: "Good" },
  { value: "easy", label: "Easy" },
];

function isVietnamese(value: string): boolean {
  return /[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]/i.test(value) ||
    /\b(cái|các|cho|của|được|không|là|một|này|những|phương pháp|quá trình|thuật toán|và)\b/i.test(value);
}

function buildExplainPrompt(front: string, back: string): string {
  if (isVietnamese(`${front}\n${back}`)) {
    return `Tôi đang học flashcard này từ tài liệu trong notebook.

Mặt trước: "${front}"

Mặt sau: "${back}"

Hãy giải thích rõ khái niệm này bằng tiếng Việt, dựa trên các tài liệu nguồn của notebook.`;
  }

  return `I am studying this flashcard from the notebook materials.

Front: "${front}"

Back: "${back}"

Please explain this concept clearly in English, using the notebook source materials.`;
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (
      error.response?.data?.detail ||
      error.response?.data?.message ||
      "Unable to save your review."
    );
  }
  return "Unable to save your review.";
}

function remainingCount(session: FlashcardStudySession): number {
  return (
    session.remaining_new +
    session.remaining_learning +
    session.remaining_review +
    session.remaining_relearning
  );
}

export function FlashcardStudyView({
  session,
  onSessionChange,
  onBack,
  onExplainCard,
}: FlashcardStudyViewProps) {
  const [showAnswer, setShowAnswer] = useState(false);
  const [submitting, setSubmitting] = useState<FlashcardRating | null>(null);
  const [isExplaining, setIsExplaining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const revealStartedAtRef = useRef(Date.now());

  const card = session.current_card?.card ?? null;

  useEffect(() => {
    setShowAnswer(false);
    setIsExplaining(false);
    setError(null);
    revealStartedAtRef.current = Date.now();
  }, [session.current_card?.card_id]);

  useEffect(() => {
    if (session.current_card || !session.next_available_at || session.status !== "active") {
      return;
    }

    const interval = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, [session.current_card, session.next_available_at, session.status]);

  useEffect(() => {
    if (session.current_card || !session.next_available_at || session.status !== "active") {
      return;
    }

    const delay = new Date(session.next_available_at).getTime() - Date.now();
    if (delay <= 0) {
      flashcardService
        .getSession(session.id)
        .then(onSessionChange)
        .catch(() => undefined);
      return;
    }

    const timer = window.setTimeout(() => {
      flashcardService
        .getSession(session.id)
        .then(onSessionChange)
        .catch(() => undefined);
    }, Math.min(delay + 100, 2_147_000_000));

    return () => window.clearTimeout(timer);
  }, [session.current_card, session.next_available_at, session.id, session.status, onSessionChange]);

  const waitSeconds = useMemo(() => {
    if (!session.next_available_at) return 0;
    return Math.max(
      0,
      Math.ceil((new Date(session.next_available_at).getTime() - now) / 1000)
    );
  }, [session.next_available_at, now]);

  const handleRating = async (rating: FlashcardRating) => {
    if (!session.current_card || submitting) return;

    setSubmitting(rating);
    setError(null);

    try {
      await flashcardService.review(session.id, {
        card_id: session.current_card.card_id,
        rating,
        response_time_ms: Math.max(0, Date.now() - revealStartedAtRef.current),
      });

      const refreshed = await flashcardService.getSession(session.id);
      onSessionChange(refreshed);
      setShowAnswer(false);
      revealStartedAtRef.current = Date.now();
    } catch (reviewError) {
      setError(getErrorMessage(reviewError));
    } finally {
      setSubmitting(null);
    }
  };

  const totalInitial = session.new_cards_count + session.review_cards_count;
  const left = remainingCount(session);

  if (session.status === "completed") {
    return (
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center p-6 text-center">
        <span className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Icon name="check_circle" className="text-4xl" />
        </span>
        <h2 className="mt-4 font-heading text-xl font-semibold">Session complete</h2>
        <p className="mt-2 max-w-sm text-sm text-muted-foreground">
          You reviewed {session.reviewed_count} time
          {session.reviewed_count === 1 ? "" : "s"} in this session.
        </p>
        <Button className="mt-6" onClick={onBack}>
          Back to deck
        </Button>
      </div>
    );
  }

  if (!card) {
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex items-center gap-3 border-b border-border px-5 py-3">
          <Button variant="ghost" size="icon-sm" onClick={onBack} aria-label="Back to deck">
            <Icon name="arrow_back" className="text-base" />
          </Button>
          <div>
            <h2 className="font-heading text-sm font-semibold">Study session</h2>
            <p className="text-[11px] text-muted-foreground">
              {left} card{left === 1 ? "" : "s"} remaining
            </p>
          </div>
        </div>

        <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
          {session.next_available_at ? (
            <>
              <Icon name="schedule" className="text-3xl text-muted-foreground" />
              <h3 className="mt-3 font-heading text-lg font-semibold">
                Next card is waiting
              </h3>
              <p className="mt-2 text-sm text-muted-foreground">
                This learning card will return in about {waitSeconds}s.
              </p>
              <Button
                variant="outline"
                className="mt-5"
                onClick={async () => {
                  const refreshed = await flashcardService.getSession(session.id);
                  onSessionChange(refreshed);
                }}
              >
                Refresh
              </Button>
            </>
          ) : (
            <>
              <Icon name="inbox" className="text-3xl text-muted-foreground" />
              <h3 className="mt-3 font-heading text-lg font-semibold">
                No card available
              </h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Return to the deck and start again when more cards are due.
              </p>
              <Button className="mt-5" onClick={onBack}>
                Back to deck
              </Button>
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-background">
      <div className="flex items-center justify-between gap-4 border-b border-border px-5 py-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon-sm" onClick={onBack} aria-label="Back to deck">
            <Icon name="arrow_back" className="text-base" />
          </Button>
          <div>
            <h2 className="font-heading text-sm font-semibold">Study session</h2>
            <p className="text-[11px] text-muted-foreground">
              {left} remaining
            </p>
          </div>
        </div>

        <div className="text-right text-[11px] text-muted-foreground">
          <span>{session.reviewed_count} reviews</span>
          {totalInitial > 0 && <span> · {totalInitial} initial cards</span>}
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center overflow-y-auto p-5 sm:p-8">
        <div className="w-full max-w-3xl">
          <div
            className={`flex flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-sm transition-[min-height] duration-300 ease-out ${
              showAnswer ? "min-h-[420px]" : "min-h-[180px]"
            }`}
          >
            <div className="flex min-h-[180px] flex-1 items-center justify-center px-7 py-8 text-center">
              <p className="text-lg font-medium leading-8 text-foreground sm:text-xl">
                {card.front}
              </p>
            </div>

            <div
              className={`grid transition-[grid-template-rows,opacity] duration-300 ease-out ${
                showAnswer ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
              }`}
              aria-hidden={!showAnswer}
            >
              <div className="overflow-hidden">
                <div className="border-t border-border/80 px-7 py-7">
                  <p className="whitespace-pre-wrap text-sm leading-7 text-foreground">
                    {card.back}
                  </p>
                  {onExplainCard && (
                    <div className="mt-6 flex justify-end">
                      <button
                        type="button"
                        disabled={isExplaining || !showAnswer}
                        onClick={async () => {
                          setIsExplaining(true);
                          try {
                            await onExplainCard(
                              buildExplainPrompt(card.front, card.back),
                              card.source_document_id ? [card.source_document_id] : []
                            );
                          } finally {
                            setIsExplaining(false);
                          }
                        }}
                        className="inline-flex items-center gap-1.5 rounded-[8px] border border-border px-3 py-2 text-xs font-medium text-muted-foreground transition-[color,background-color,border-color,transform] hover:border-primary/40 hover:bg-primary/5 hover:text-primary active:scale-95 disabled:cursor-wait disabled:opacity-70 disabled:active:scale-100"
                      >
                        <Icon name="forum" className="text-base" />
                        {isExplaining && (
                          <Icon name="progress_activity" className="animate-spin text-sm" />
                        )}
                        Explain
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {error && (
            <div className="mt-4 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive">
              {error}
            </div>
          )}

          {!showAnswer ? (
            <div className="mt-5 flex justify-center">
              <Button
                size="lg"
                className="min-w-40"
                onClick={() => {
                  setShowAnswer(true);
                  revealStartedAtRef.current = Date.now();
                }}
              >
                Flip
              </Button>
            </div>
          ) : (
            <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {RATINGS.map((rating) => (
                <button
                  key={rating.value}
                  type="button"
                  disabled={submitting !== null}
                  onClick={() => void handleRating(rating.value)}
                  className={`min-h-12 rounded-xl border px-3 py-3 text-center text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${
                    rating.value === "again"
                      ? "border-red-500 bg-card text-red-700 hover:bg-red-500/10 dark:text-red-400"
                      : rating.value === "hard"
                        ? "border-amber-500 bg-card text-amber-700 hover:bg-amber-500/10 dark:text-amber-400"
                        : rating.value === "good"
                          ? "border-green-500 bg-card text-green-700 hover:bg-green-500/10 dark:text-green-400"
                          : "border-blue-500 bg-card text-blue-700 hover:bg-blue-500/10 dark:text-blue-400"
                  }`}
                >
                  {submitting === rating.value ? "Saving..." : rating.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
