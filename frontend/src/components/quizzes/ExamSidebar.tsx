"use client";

import { Icon } from "@/components/shared/icons";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface Option {
  id: string | number;
  option_text: string;
}

interface QuizQuestion {
  id: number;
  question_text: string;
  options: Option[] | null;
  correct_answer: unknown;
  explanations: unknown;
  user_answer?: unknown;
  is_correct?: boolean | null;
}

interface ExamSidebarProps {
  questions: QuizQuestion[];
  answers: Record<number, unknown>;
  markedReview: Record<number, boolean>;
  markedCritical: Record<number, boolean>;
  currentIndex: number;
  onSelectQuestion: (index: number) => void;
  isSubmitted: boolean;
  onSubmit: () => void;
  submitting: boolean;
  timeLeft: number;
  violationsCount: number;
}

function formatTime(seconds: number) {
  if (seconds <= 0) return "00:00";
  const minutes = Math.floor(seconds / 60).toString().padStart(2, "0");
  const remainingSeconds = (seconds % 60).toString().padStart(2, "0");
  return `${minutes}:${remainingSeconds}`;
}

export default function ExamSidebar({
  questions,
  answers,
  markedReview,
  markedCritical,
  currentIndex,
  onSelectQuestion,
  isSubmitted,
  onSubmit,
  submitting,
  timeLeft,
  violationsCount,
}: ExamSidebarProps) {
  const answeredCount = Object.keys(answers).length;
  const totalCount = questions.length;
  const progressPercentage =
    totalCount > 0 ? Math.round((answeredCount / totalCount) * 100) : 0;
  const timeIsLow = timeLeft < 180 && !isSubmitted;

  return (
    <Card className="gap-0 border border-border/80 py-0 shadow-sm ring-0">
      <div className="border-b border-border/70 bg-secondary/35 p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              <Icon name="schedule" className="text-sm" />
              Time remaining
            </p>
            <p
              className={`mt-1 font-heading text-3xl font-semibold tabular-nums ${
                timeIsLow ? "text-destructive" : "text-foreground"
              }`}
              aria-live="polite"
            >
              {isSubmitted ? "Submitted" : formatTime(timeLeft)}
            </p>
          </div>

          {!isSubmitted && (
            <div className="text-right">
              <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Violations
              </p>
              <span
                className={`mt-2 inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-medium ${
                  violationsCount > 0
                    ? "border-destructive/25 bg-destructive/10 text-destructive"
                    : "border-primary/20 bg-primary/10 text-primary"
                }`}
              >
                {violationsCount} / 3
              </span>
            </div>
          )}
        </div>

        <div className="mt-5">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-medium text-muted-foreground">Answer progress</span>
            <span className="font-medium text-foreground">
              {answeredCount}/{totalCount}
            </span>
          </div>
          <div
            className="mt-2 h-2 overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-label="Exam completion"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progressPercentage}
          >
            <div
              className="h-full rounded-full bg-primary transition-[width] duration-300"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
        </div>
      </div>

      <div className="p-5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-heading text-sm font-semibold text-foreground">
            Questions
          </h2>
          <span className="text-[10px] text-muted-foreground">Select to navigate</span>
        </div>

        <div className="mt-1.5 grid max-h-[286px] grid-cols-5 gap-2 overflow-y-auto p-1.5 lg:grid-cols-4 xl:grid-cols-5">
          {questions.map((question, index) => {
            const isCurrent = index === currentIndex;
            const isAnswered =
              answers[question.id] !== undefined && answers[question.id] !== null;
            const needsReview = markedReview[question.id];
            const isCritical = markedCritical[question.id];

            let cellStyles =
              "border-border bg-background text-muted-foreground hover:border-primary/40 hover:text-foreground";

            if (isSubmitted) {
              cellStyles = question.is_correct
                ? "border-chart-2 bg-chart-2 text-white"
                : "border-destructive bg-destructive text-white";
            } else if (isAnswered) {
              cellStyles = "border-primary bg-primary text-primary-foreground";
            }

            if (isCurrent) {
              cellStyles +=
                " ring-2 ring-accent/50 ring-offset-2 ring-offset-background";
            }

            return (
              <button
                key={`nav-${question.id}`}
                type="button"
                onClick={() => onSelectQuestion(index)}
                className={`relative flex h-9 items-center justify-center rounded-[8px] border text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 ${cellStyles}`}
                aria-label={`Go to question ${index + 1}`}
                aria-current={isCurrent ? "step" : undefined}
              >
                {index + 1}
                {!isSubmitted && (needsReview || isCritical) && (
                  <span className="absolute -right-1 -top-1 flex gap-0.5">
                    {isCritical && (
                      <span
                        className="h-2.5 w-2.5 rounded-full border-2 border-card bg-destructive"
                        title="Marked critical"
                      />
                    )}
                    {needsReview && (
                      <span
                        className="h-2.5 w-2.5 rounded-full border-2 border-card bg-chart-1"
                        title="Marked for review"
                      />
                    )}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        <div className="mt-4 grid grid-cols-2 gap-x-3 gap-y-2 border-t border-border/70 pt-4 text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-[3px] bg-primary" /> Answered
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-[3px] border border-border bg-background" /> Unanswered
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-chart-1" /> Review
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-destructive" /> Critical
          </span>
        </div>

        {!isSubmitted && (
          <Button className="mt-5 w-full" size="lg" onClick={onSubmit} disabled={submitting}>
            <Icon
              name={submitting ? "progress_activity" : "assignment_turned_in"}
              className={submitting ? "animate-spin text-base" : "text-base"}
            />
            {submitting ? "Submitting..." : "Submit exam"}
          </Button>
        )}
      </div>
    </Card>
  );
}
