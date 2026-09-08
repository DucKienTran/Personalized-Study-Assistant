"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";

import { Icon } from "@/components/shared/icons";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  FlashcardDeckDetail,
  FlashcardDeckItem,
  FlashcardItem,
  FlashcardNotebookAnalytics,
  FlashcardStudyOverview,
  FlashcardStudySession,
  flashcardService,
} from "@/services/flashcard.service";
import { FlashcardStudyView } from "@/components/flashcards/FlashcardStudyView";

interface FlashcardsTabProps {
  notebookId: number;
  activeDocumentCount: number;
  onExplainCard?: (content: string, sourceDocumentIds: number[]) => void | Promise<void>;
  selectedDeckId?: number | null;
  startSelectedDeckStudy?: boolean;
  onSelectDeck?: (deckId: number) => void;
  onCloseDeck?: () => void;
}

type DeckDialogMode = "manual" | "ai";
type CardDraft = {
  id?: number;
  front: string;
  back: string;
};

function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.response?.data?.message || fallback;
  }
  return fallback;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function formatReviewTime(milliseconds: number): string {
  const seconds = Math.round(milliseconds / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

function successRateColor(rate: number): string {
  const value = Math.max(0, Math.min(100, rate));
  const stops = [
    { at: 0, rgb: [220, 38, 38] },
    { at: 30, rgb: [217, 119, 6] },
    { at: 50, rgb: [161, 98, 7] },
    { at: 70, rgb: [8, 145, 178] },
    { at: 100, rgb: [22, 163, 74] },
  ];
  const upperIndex = stops.findIndex((stop) => value <= stop.at);
  const upper = stops[upperIndex === -1 ? stops.length - 1 : upperIndex];
  const lower = stops[Math.max(0, (upperIndex === -1 ? stops.length - 1 : upperIndex) - 1)];
  const progress = upper.at === lower.at ? 0 : (value - lower.at) / (upper.at - lower.at);
  const rgb = lower.rgb.map((channel, index) =>
    Math.round(channel + (upper.rgb[index] - channel) * progress)
  );
  return `rgb(${rgb.join(", ")})`;
}

export function FlashcardsTab({
  notebookId,
  activeDocumentCount,
  onExplainCard,
  selectedDeckId,
  startSelectedDeckStudy = false,
  onSelectDeck,
  onCloseDeck,
}: FlashcardsTabProps) {
  const [decks, setDecks] = useState<FlashcardDeckItem[]>([]);
  const [analytics, setAnalytics] = useState<FlashcardNotebookAnalytics | null>(null);
  const [showAverageReviewTime, setShowAverageReviewTime] = useState(false);
  const [selectedDeck, setSelectedDeck] = useState<FlashcardDeckDetail | null>(null);
  const [overview, setOverview] = useState<FlashcardStudyOverview | null>(null);
  const [session, setSession] = useState<FlashcardStudySession | null>(null);
  const autoStartedDeckIdRef = useRef<number | null>(null);

  const [loading, setLoading] = useState(true);
  const [loadingDeck, setLoadingDeck] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [deckDialog, setDeckDialog] = useState<DeckDialogMode | null>(null);
  const [deckTitle, setDeckTitle] = useState("");
  const [deckDescription, setDeckDescription] = useState("");
  const [totalCards, setTotalCards] = useState("20");
  const [customInstruction, setCustomInstruction] = useState("");
  const [submittingDeck, setSubmittingDeck] = useState(false);

  const [cardDialogOpen, setCardDialogOpen] = useState(false);
  const [cardDraft, setCardDraft] = useState<CardDraft>({
    front: "",
    back: "",
  });
  const [savingCard, setSavingCard] = useState(false);
  const [deletingDeckId, setDeletingDeckId] = useState<number | null>(null);

  const loadDecks = useCallback(async () => {
    try {
      const [items, notebookAnalytics] = await Promise.all([
        flashcardService.listDecks(notebookId),
        flashcardService.getNotebookAnalytics(notebookId),
      ]);
      setDecks(items);
      setAnalytics(notebookAnalytics);
      return items;
    } catch (loadError) {
      setError(getErrorMessage(loadError, "Unable to load flashcard decks."));
      return [];
    } finally {
      setLoading(false);
    }
  }, [notebookId]);

  const loadDeckDetail = useCallback(async (deckId: number) => {
    setLoadingDeck(true);
    setError(null);
    try {
      const [detail, studyOverview] = await Promise.all([
        flashcardService.getDeck(deckId),
        flashcardService.getStudyOverview(deckId),
      ]);
      setSelectedDeck(detail);
      setOverview(studyOverview);
    } catch (loadError) {
      setError(getErrorMessage(loadError, "Unable to load this flashcard deck."));
    } finally {
      setLoadingDeck(false);
    }
  }, []);

  useEffect(() => {
    void loadDecks();
  }, [loadDecks]);

  useEffect(() => {
    if (selectedDeckId) {
      void loadDeckDetail(selectedDeckId);
    } else {
      setSelectedDeck(null);
      setOverview(null);
      setSession(null);
    }
  }, [loadDeckDetail, selectedDeckId]);

  const hasProcessingDeck = decks.some(
    (deck) => deck.generation_status === "processing"
  );

  useEffect(() => {
    if (!hasProcessingDeck) return;

    const timer = window.setInterval(async () => {
      const result = await Promise.all([
        flashcardService.listDecks(notebookId),
        flashcardService.getNotebookAnalytics(notebookId),
      ]).catch(() => null);
      if (!result) return;
      const [items, notebookAnalytics] = result;

      setDecks(items);
      setAnalytics(notebookAnalytics);

      if (selectedDeck) {
        const updated = items.find((item) => item.id === selectedDeck.id);
        if (updated?.generation_status === "completed") {
          void loadDeckDetail(selectedDeck.id);
        }
      }
    }, 3000);

    return () => window.clearInterval(timer);
  }, [hasProcessingDeck, notebookId, selectedDeck, loadDeckDetail]);

  const resetDeckDialog = () => {
    setDeckTitle("");
    setDeckDescription("");
    setTotalCards("20");
    setCustomInstruction("");
    setError(null);
  };

  const openDeckDialog = (mode: DeckDialogMode) => {
    resetDeckDialog();
    setDeckDialog(mode);
  };

  const handleCreateDeck = async () => {
    const title = deckTitle.trim();
    if (!title) {
      setError("Deck title is required.");
      return;
    }

    setSubmittingDeck(true);
    setError(null);

    try {
      if (deckDialog === "manual") {
        const deck = await flashcardService.createDeck({
          notebook_id: notebookId,
          title,
          description: deckDescription.trim() || null,
        });
        setDeckDialog(null);
        await loadDecks();
        await loadDeckDetail(deck.id);
      } else {
        const count = Number(totalCards);
        if (!Number.isInteger(count) || count < 1 || count > 100) {
          setError("Number of cards must be between 1 and 100.");
          return;
        }

        await flashcardService.generate({
          notebook_id: notebookId,
          title,
          description: deckDescription.trim() || null,
          total_cards: count,
          custom_instruction: customInstruction.trim() || null,
        });

        setDeckDialog(null);
        await loadDecks();
      }
    } catch (createError) {
      setError(
        getErrorMessage(
          createError,
          deckDialog === "manual"
            ? "Unable to create the deck."
            : "Unable to start flashcard generation."
        )
      );
    } finally {
      setSubmittingDeck(false);
    }
  };

  const handleDeleteDeck = async (deck: FlashcardDeckItem) => {
    if (!window.confirm(`Delete "${deck.title}" and all of its cards?`)) return;

    setDeletingDeckId(deck.id);
    setError(null);
    try {
      await flashcardService.deleteDeck(deck.id);
      if (selectedDeck?.id === deck.id) {
        setSelectedDeck(null);
        setOverview(null);
        setSession(null);
        onCloseDeck?.();
      }
      await loadDecks();
    } catch (deleteError) {
      setError(getErrorMessage(deleteError, "Unable to delete this deck."));
    } finally {
      setDeletingDeckId(null);
    }
  };

  const openNewCard = () => {
    setCardDraft({ front: "", back: "" });
    setCardDialogOpen(true);
  };

  const openEditCard = (card: FlashcardItem) => {
    setCardDraft({
      id: card.id,
      front: card.front,
      back: card.back,
    });
    setCardDialogOpen(true);
  };

  const saveCard = async () => {
    if (!selectedDeck) return;
    if (!cardDraft.front.trim() || !cardDraft.back.trim()) {
      setError("Front and back are required.");
      return;
    }

    setSavingCard(true);
    setError(null);
    try {
      const payload = {
        front: cardDraft.front.trim(),
        back: cardDraft.back.trim(),
      };

      if (cardDraft.id) {
        await flashcardService.updateCard(cardDraft.id, payload);
      } else {
        await flashcardService.createCard(selectedDeck.id, payload);
      }

      setCardDialogOpen(false);
      await loadDeckDetail(selectedDeck.id);
      await loadDecks();
    } catch (saveError) {
      setError(getErrorMessage(saveError, "Unable to save this flashcard."));
    } finally {
      setSavingCard(false);
    }
  };

  const handleDeleteCard = async (card: FlashcardItem) => {
    if (!selectedDeck) return;
    if (!window.confirm("Delete this flashcard?")) return;

    try {
      await flashcardService.deleteCard(card.id);
      await loadDeckDetail(selectedDeck.id);
      await loadDecks();
    } catch (deleteError) {
      setError(getErrorMessage(deleteError, "Unable to delete this flashcard."));
    }
  };

  const handleToggleSuspend = async (card: FlashcardItem) => {
    if (!selectedDeck) return;
    try {
      if (card.is_suspended) {
        await flashcardService.unsuspendCard(card.id);
      } else {
        await flashcardService.suspendCard(card.id);
      }
      await loadDeckDetail(selectedDeck.id);
    } catch (suspendError) {
      setError(getErrorMessage(suspendError, "Unable to update this flashcard."));
    }
  };

  const handleStartStudy = async () => {
    if (!selectedDeck) return;
    setError(null);
    try {
      const nextSession = await flashcardService.startSession(selectedDeck.id);
      setSession(nextSession);
    } catch (studyError) {
      setError(getErrorMessage(studyError, "Unable to start a study session."));
    }
  };

  useEffect(() => {
    if (
      !startSelectedDeckStudy ||
      !selectedDeck ||
      selectedDeck.generation_status !== "completed" ||
      autoStartedDeckIdRef.current === selectedDeck.id
    ) {
      return;
    }

    autoStartedDeckIdRef.current = selectedDeck.id;
    void handleStartStudy();
  }, [selectedDeck, startSelectedDeckStudy]);

  const sortedCards = useMemo(
    () =>
      selectedDeck
        ? [...selectedDeck.cards].sort(
            (a, b) => a.position - b.position || a.id - b.id
          )
        : [],
    [selectedDeck]
  );

  const sortedDecks = useMemo(
    () =>
      [...decks].sort((a, b) => {
        const updatedDifference =
          new Date(b.updated_at ?? b.created_at).getTime() -
          new Date(a.updated_at ?? a.created_at).getTime();
        return updatedDifference || b.id - a.id;
      }),
    [decks]
  );

  const ratingData = useMemo(
    () => [
      { rating: "Again", count: analytics?.rating_counts.again ?? 0, color: "#ef4444" },
      { rating: "Hard", count: analytics?.rating_counts.hard ?? 0, color: "#f59e0b" },
      { rating: "Good", count: analytics?.rating_counts.good ?? 0, color: "#22c55e" },
      { rating: "Easy", count: analytics?.rating_counts.easy ?? 0, color: "#3b82f6" },
    ],
    [analytics]
  );

  if (session) {
    return (
      <FlashcardStudyView
        session={session}
        onSessionChange={setSession}
        onExplainCard={onExplainCard}
        onBack={async () => {
          const deckId = session.deck_id;
          setSession(null);
          await Promise.all([loadDeckDetail(deckId), loadDecks()]);
        }}
      />
    );
  }

  if (selectedDeck) {
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => {
                setSelectedDeck(null);
                setOverview(null);
                setSession(null);
                onCloseDeck?.();
              }}
              aria-label="Back to decks"
            >
              <Icon name="arrow_back" className="text-base" />
            </Button>
            <div className="min-w-0">
              <h2 className="truncate font-heading text-base font-semibold">
                {selectedDeck.title}
              </h2>
              <p className="mt-0.5 text-[11px] text-muted-foreground">
                {selectedDeck.card_count} cards
                {selectedDeck.suspended_card_count > 0
                  ? ` · ${selectedDeck.suspended_card_count} suspended`
                  : ""}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={openNewCard}>
              <Icon name="add" className="text-base" />
              Add card
            </Button>
            <Button
              size="sm"
              onClick={() => void handleStartStudy()}
              disabled={!overview || overview.due_now_count === 0}
              title={
                overview?.due_now_count === 0
                  ? "No cards are due right now"
                  : undefined
              }
            >
              <Icon name="play_arrow" className="text-base" />
              Study {overview ? `(${overview.due_now_count})` : ""}
            </Button>
          </div>
        </div>

        {error && (
          <div className="mx-5 mt-4 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive">
            {error}
          </div>
        )}

        {overview && (
          <div className="grid grid-cols-2 gap-2 px-5 pt-5 sm:grid-cols-4">
            {[
              ["New", overview.new_count],
              ["Learning", overview.learning_count + overview.relearning_count],
              ["Due", overview.review_due_count],
              ["Suspended", overview.suspended_count],
            ].map(([label, value]) => (
              <div
                key={String(label)}
                className="rounded-xl border border-border bg-card px-4 py-3"
              >
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  {label}
                </p>
                <p className="mt-1 font-heading text-xl font-semibold">{value}</p>
              </div>
            ))}
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-5">
          {loadingDeck ? (
            <div className="flex min-h-60 items-center justify-center gap-2 text-xs text-muted-foreground">
              <Icon name="progress_activity" className="animate-spin text-lg" />
              Loading cards...
            </div>
          ) : sortedCards.length === 0 ? (
            <div className="flex min-h-72 flex-col items-center justify-center text-center">
              <Icon name="style" className="text-4xl text-muted-foreground" />
              <h3 className="mt-3 font-heading text-lg font-semibold">
                This deck is empty
              </h3>
              <p className="mt-2 text-xs text-muted-foreground">
                Add your first card to start studying.
              </p>
              <Button className="mt-5" size="sm" onClick={openNewCard}>
                <Icon name="add" className="text-base" />
                Add card
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {sortedCards.map((card, index) => (
                <div
                  key={card.id}
                  className={`group rounded-xl border border-border bg-card p-4 ${
                    card.is_suspended ? "opacity-55" : ""
                  }`}
                >
                  <div className="flex gap-3">
                    <span className="mt-0.5 text-[11px] tabular-nums text-muted-foreground">
                      {index + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium leading-6">{card.front}</p>
                      <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted-foreground">
                        {card.back}
                      </p>
                    </div>

                    <DropdownMenu>
                      <DropdownMenuTrigger
                        className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground opacity-0 outline-none transition hover:bg-secondary group-hover:opacity-100 data-popup-open:opacity-100"
                        aria-label="Card actions"
                      >
                        <Icon name="more_vert" className="text-base" />
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="min-w-36">
                        <DropdownMenuItem onClick={() => openEditCard(card)}>
                          <Icon name="edit" className="text-sm" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => void handleToggleSuspend(card)}>
                          <Icon
                            name={card.is_suspended ? "play_circle" : "pause_circle"}
                            className="text-sm"
                          />
                          {card.is_suspended ? "Unsuspend" : "Suspend"}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          variant="destructive"
                          onClick={() => void handleDeleteCard(card)}
                        >
                          <Icon name="delete" className="text-sm" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <Dialog open={cardDialogOpen} onOpenChange={setCardDialogOpen}>
          <DialogContent className="gap-0 p-0 sm:max-w-xl">
            <DialogHeader className="border-b border-border px-6 py-5">
              <DialogTitle className="text-base">
                {cardDraft.id ? "Edit flashcard" : "Add flashcard"}
              </DialogTitle>
            </DialogHeader>
            <div className="max-h-[70vh] space-y-4 overflow-y-auto px-6 py-5">
              <div className="space-y-2">
                <label className="text-xs font-medium">Front</label>
                <Textarea
                  value={cardDraft.front}
                  onChange={(event) =>
                    setCardDraft((current) => ({
                      ...current,
                      front: event.target.value,
                    }))
                  }
                  className="min-h-24 resize-none text-sm"
                  placeholder="Term or concept"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium">Back</label>
                <Textarea
                  value={cardDraft.back}
                  onChange={(event) =>
                    setCardDraft((current) => ({
                      ...current,
                      back: event.target.value,
                    }))
                  }
                  className="min-h-28 resize-none text-sm"
                  placeholder="Definition or explanation"
                />
              </div>
            </div>
            <DialogFooter className="border-t border-border bg-secondary/20 px-6 py-4">
              <Button
                variant="outline"
                onClick={() => setCardDialogOpen(false)}
                disabled={savingCard}
              >
                Cancel
              </Button>
              <Button onClick={() => void saveCard()} disabled={savingCard}>
                {savingCard && (
                  <Icon name="progress_activity" className="animate-spin text-base" />
                )}
                Save card
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-3">
        <div>
          <h2 className="font-heading text-base font-semibold">Flashcards</h2>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            Create decks manually or generate them from active notebook sources.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => openDeckDialog("manual")}>
            <Icon name="add" className="text-base" />
            New deck
          </Button>
          <Button
            size="sm"
            onClick={() => openDeckDialog("ai")}
            disabled={activeDocumentCount === 0}
            title={
              activeDocumentCount === 0
                ? "Activate at least one document to generate flashcards"
                : undefined
            }
          >
            <Icon name="auto_awesome" className="text-base" />
            Generate
          </Button>
        </div>
      </div>

      {error && (
        <div className="mx-5 mt-4 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive">
          {error}
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col p-5">
        {loading ? (
          <div className="flex min-h-72 items-center justify-center gap-2 text-xs text-muted-foreground">
            <Icon name="progress_activity" className="animate-spin text-lg" />
            Loading flashcards...
          </div>
        ) : (
          <>
            <div className="grid shrink-0 gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(320px,1fr)]">
              <div className="grid grid-cols-2 gap-3">
                {[
                  ["Decks", String(analytics?.deck_count ?? 0)],
                  ["Cards", String(analytics?.card_count ?? 0)],
                  ["Success rate", `${(analytics?.success_rate ?? 0).toFixed(1)}%`],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-xl border border-border bg-card px-4 py-3">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                      {label}
                    </p>
                    <p
                      className="mt-2 font-heading text-xl font-semibold tabular-nums"
                      style={
                        label === "Success rate"
                          ? { color: successRateColor(analytics?.success_rate ?? 0) }
                          : undefined
                      }
                    >
                      {value}
                    </p>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => setShowAverageReviewTime((current) => !current)}
                  className="relative rounded-xl border border-border bg-card px-4 py-3 text-left transition-[border-color,background-color,transform] hover:border-primary/40 hover:bg-secondary/20 active:scale-[0.99]"
                  aria-label="Toggle total and average review time"
                >
                  <Icon
                    name="sync"
                    className={`absolute right-3 top-3 text-sm text-muted-foreground transition-transform duration-200 ${
                      showAverageReviewTime ? "rotate-180" : "rotate-0"
                    }`}
                  />
                  <span className="relative block h-[48px] pr-5">
                    <span
                      className={`absolute inset-0 block transition-[opacity,transform] duration-200 ${
                        showAverageReviewTime
                          ? "pointer-events-none -translate-y-1 opacity-0"
                          : "translate-y-0 opacity-100"
                      }`}
                    >
                      <span className="block text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                        Total review time
                      </span>
                      <span className="mt-2 block font-heading text-xl font-semibold tabular-nums">
                        {formatReviewTime(analytics?.total_review_time_ms ?? 0)}
                      </span>
                    </span>
                    <span
                      className={`absolute inset-0 block transition-[opacity,transform] duration-200 ${
                        showAverageReviewTime
                          ? "translate-y-0 opacity-100"
                          : "pointer-events-none translate-y-1 opacity-0"
                      }`}
                    >
                      <span className="block text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                        Average review time
                      </span>
                      <span className="mt-2 block font-heading text-xl font-semibold tabular-nums">
                        {formatReviewTime(analytics?.average_review_time_ms ?? 0)}
                      </span>
                    </span>
                  </span>
                </button>
              </div>

              <div className="rounded-xl border border-border bg-card px-4 pb-3 pt-4">
                <h3 className="font-heading text-sm font-semibold">Rating Distribution</h3>
                <div className="mt-1 h-[150px]" role="img" aria-label="Flashcard rating distribution">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={ratingData}
                      margin={{ top: 22, right: 10, left: 10, bottom: 0 }}
                      barCategoryGap="14%"
                    >
                      <XAxis
                        dataKey="rating"
                        tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                        tickLine={false}
                        axisLine={{ stroke: "var(--border)" }}
                      />
                      <YAxis hide domain={[0, "auto"]} allowDecimals={false} />
                      <Bar dataKey="count" radius={[6, 6, 2, 2]} barSize={52}>
                        <LabelList
                          dataKey="count"
                          position="top"
                          fill="var(--foreground)"
                          fontSize={11}
                        />
                        {ratingData.map((item) => (
                          <Cell key={item.rating} fill={item.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <h3 className="mt-5 shrink-0 font-heading text-sm font-semibold">Your decks</h3>
            <div className="mt-3 min-h-0 flex-1 overflow-y-auto pr-1">
              {decks.length === 0 ? (
                <div className="flex min-h-60 flex-col items-center justify-center text-center">
                  <span className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <Icon name="style" className="text-3xl" />
                  </span>
                  <h3 className="mt-4 font-heading text-lg font-semibold">
                    No flashcard decks yet
                  </h3>
                  <p className="mt-2 max-w-sm text-xs leading-5 text-muted-foreground">
                    Create cards yourself or generate a deck from your active documents.
                  </p>
                  <div className="mt-5 flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openDeckDialog("manual")}
                    >
                      New deck
                    </Button>
                    <Button
                      size="sm"
                      disabled={activeDocumentCount === 0}
                      onClick={() => openDeckDialog("ai")}
                    >
                      <Icon name="auto_awesome" className="text-base" />
                      Generate
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-3">
                  {sortedDecks.map((deck) => {
              const processing = deck.generation_status === "processing";
              const failed = deck.generation_status === "failed";
              return (
                <div
                  key={deck.id}
                  className={`group rounded-xl border border-border bg-card p-4 transition ${
                    !processing && !failed
                      ? "hover:border-primary/40 hover:shadow-xs"
                      : "opacity-70"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      disabled={processing || failed || deletingDeckId === deck.id}
                      onClick={() => {
                        onSelectDeck?.(deck.id);
                        if (!onSelectDeck) void loadDeckDetail(deck.id);
                      }}
                      className="flex min-w-0 flex-1 items-center gap-4 text-left disabled:cursor-default"
                    >
                      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Icon
                          name={processing ? "progress_activity" : "style"}
                          className={processing ? "animate-spin text-lg" : "text-xl"}
                        />
                      </span>
                      <div className="min-w-0 flex-1">
                        <h3 className="truncate text-sm font-semibold">{deck.title}</h3>
                        <div className="mt-1.5 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                          <span>{deck.card_count} cards</span>
                          <span>·</span>
                          <span>{formatDate(deck.created_at)}</span>
                          {deck.suspended_card_count > 0 && (
                            <>
                              <span>·</span>
                              <span>{deck.suspended_card_count} suspended</span>
                            </>
                          )}
                        </div>
                      </div>
                    </button>

                    <DropdownMenu>
                      <DropdownMenuTrigger
                        disabled={deletingDeckId === deck.id}
                        className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground opacity-0 outline-none transition hover:bg-secondary group-hover:opacity-100 data-popup-open:opacity-100"
                        aria-label="Deck actions"
                      >
                        <Icon
                          name={
                            deletingDeckId === deck.id
                              ? "progress_activity"
                              : "more_vert"
                          }
                          className={
                            deletingDeckId === deck.id ? "animate-spin text-base" : "text-base"
                          }
                        />
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          variant="destructive"
                          onClick={() => void handleDeleteDeck(deck)}
                        >
                          <Icon name="delete" className="text-sm" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>

                    <span
                      className={`rounded-full border px-2.5 py-1 text-[10px] font-medium ${
                        processing
                          ? "border-amber-500/25 bg-amber-500/5 text-amber-700"
                          : failed
                            ? "border-destructive/25 bg-destructive/5 text-destructive"
                            : "border-primary/20 bg-primary/5 text-primary"
                      }`}
                    >
                      {processing
                        ? "Generating"
                        : failed
                          ? "Failed"
                          : deck.generation_status === "manual"
                            ? "Manual"
                            : "Ready"}
                    </span>
                  </div>
                </div>
              );
                  })}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      <Dialog
        open={deckDialog !== null}
        onOpenChange={(open) => {
          if (!open) setDeckDialog(null);
        }}
      >
        <DialogContent className="gap-0 p-0 sm:max-w-lg">
          <DialogHeader className="border-b border-border px-6 py-5">
            <DialogTitle className="text-base">
              {deckDialog === "ai" ? "Generate flashcards" : "Create flashcard deck"}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 px-6 py-5">
            <div className="space-y-2">
              <label className="text-xs font-medium">Deck title</label>
              <Input
                value={deckTitle}
                onChange={(event) => setDeckTitle(event.target.value)}
                placeholder="e.g., Linear Algebra — Definitions"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium">Description</label>
              <Textarea
                value={deckDescription}
                onChange={(event) => setDeckDescription(event.target.value)}
                className="min-h-16 resize-none text-xs"
                placeholder="Optional"
              />
            </div>

            {deckDialog === "ai" && (
              <>
                <div className="space-y-2">
                  <label className="text-xs font-medium">Number of cards</label>
                  <Input
                    type="text"
                    inputMode="numeric"
                    value={totalCards}
                    onChange={(event) => setTotalCards(event.target.value)}
                  />
                  <p className="text-[11px] text-muted-foreground">
                    Choose between 1 and 100 cards.
                  </p>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-medium">Personal instructions</label>
                  <Textarea
                    value={customInstruction}
                    onChange={(event) => setCustomInstruction(event.target.value)}
                    className="min-h-20 resize-none text-xs"
                    placeholder="e.g., Focus on definitions and theorems from Chapter 3..."
                  />
                </div>
              </>
            )}

            {error && (
              <div className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive">
                {error}
              </div>
            )}
          </div>

          <DialogFooter className="border-t border-border bg-secondary/20 px-6 py-4">
            <Button
              variant="outline"
              disabled={submittingDeck}
              onClick={() => setDeckDialog(null)}
            >
              Cancel
            </Button>
            <Button onClick={() => void handleCreateDeck()} disabled={submittingDeck}>
              {submittingDeck && (
                <Icon name="progress_activity" className="animate-spin text-base" />
              )}
              {deckDialog === "ai" ? "Generate" : "Create deck"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
