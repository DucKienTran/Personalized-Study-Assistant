"use client";

import { useMemo } from "react";

import {
  QUESTION_TYPE_COLORS,
  QUESTION_TYPE_LABELS,
} from "@/constants/question-type-colors";
import { QuestionTypeStats } from "@/types/dashboard";

function buildDisplayPercentages(data: QuestionTypeStats[], total: number) {
  if (!total) return new Map<string, number>();

  const rounded = new Map<string, number>();
  let sumWithoutTrueFalse = 0;
  let trueFalseKey: string | null = null;

  for (const item of data) {
    if (item.question_type === "true_false") {
      trueFalseKey = item.question_type;
      continue;
    }

    const value = Math.round((item.answered_count / total) * 100);
    rounded.set(item.question_type, value);
    sumWithoutTrueFalse += value;
  }

  if (trueFalseKey) {
    rounded.set(trueFalseKey, Math.max(0, Math.min(100, 100 - sumWithoutTrueFalse)));
  } else if (data.length > 0) {
    const last = data[data.length - 1];
    const previousTotal = data
      .slice(0, -1)
      .reduce((sum, item) => sum + (rounded.get(item.question_type) ?? 0), 0);
    rounded.set(last.question_type, Math.max(0, Math.min(100, 100 - previousTotal)));
  }

  return rounded;
}

export function QuestionTypeDistribution({ data }: { data: QuestionTypeStats[] }) {
  const total = useMemo(
    () => data.reduce((sum, item) => sum + item.answered_count, 0),
    [data]
  );
  const maxAnsweredCount = useMemo(
    () => Math.max(0, ...data.map((item) => item.answered_count)),
    [data]
  );

  const displayPercentages = useMemo(
    () => buildDisplayPercentages(data, total),
    [data, total]
  );

  const rows = useMemo(
    () =>
      data.map((item) => ({
        ...item,
        label: QUESTION_TYPE_LABELS[item.question_type] ?? item.question_type,
        exactPercentage: total ? (item.answered_count / total) * 100 : 0,
        displayPercentage: displayPercentages.get(item.question_type) ?? 0,
      })),
    [data, total, displayPercentages]
  );

  return (
    <div
      className="flex h-full min-h-0 w-full flex-col gap-3 px-1 py-1"
      role="img"
      aria-label="Distribution of practiced questions by question type"
    >
      <div className="flex min-h-0 flex-1 flex-col">
        <div
          className="flex h-3.5 w-full overflow-hidden rounded-full bg-muted"
          aria-hidden="true"
        >
          {rows.map((item) => (
            <div
              key={item.question_type}
              className="h-full min-w-[2px] first:rounded-l-full last:rounded-r-full"
              style={{
                width: `${item.exactPercentage}%`,
                backgroundColor: QUESTION_TYPE_COLORS[item.question_type],
              }}
            />
          ))}
        </div>

        <div className="mt-1.5 flex items-center justify-between text-[11px] text-muted-foreground">
          <span>{total.toLocaleString()} questions practiced</span>
          <span>{rows.length} types</span>
        </div>
      </div>

      <div className="shrink-0">
        <div className="grid grid-cols-[minmax(72px,1fr)_minmax(56px,0.9fr)_48px_52px] items-center gap-2 rounded-lg bg-muted/45 px-3 py-1.5 text-[10px] font-semibold text-muted-foreground sm:grid-cols-[minmax(0,1fr)_minmax(104px,0.9fr)_64px_76px] sm:gap-3 sm:text-[11px]">
          <span className="col-span-2">Question type</span>
          <span className="text-right">Questions</span>
          <span className="text-right leading-tight">Share of total</span>
        </div>

        <div
          className="mt-0.5 grid min-h-0 flex-1"
          style={{ gridTemplateRows: `repeat(${rows.length}, minmax(36px, 1fr))` }}
        >
          {rows.map((item) => (
            <div
              key={item.question_type}
              className="grid grid-cols-[minmax(72px,1fr)_minmax(56px,0.9fr)_48px_52px] items-center gap-2 rounded-lg px-3 py-2 transition-colors hover:bg-muted/35 sm:grid-cols-[minmax(0,1fr)_minmax(104px,0.9fr)_64px_76px] sm:gap-3"
            >
              <div className="flex min-w-0 items-center gap-2.5">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: QUESTION_TYPE_COLORS[item.question_type] }}
                />
                <span
                  className="truncate text-[11px] font-medium text-foreground sm:text-xs"
                  title={item.label}
                >
                  {item.label}
                </span>
              </div>

              <div className="h-2.5 min-w-0 overflow-hidden">
                <div
                  className="h-full"
                  style={{
                    width: `${maxAnsweredCount > 0 ? (item.answered_count / maxAnsweredCount) * 100 : 0}%`,
                    backgroundColor: QUESTION_TYPE_COLORS[item.question_type],
                  }}
                />
              </div>

              <span className="text-right tabular-nums text-[11px] text-muted-foreground sm:text-xs">
                {item.answered_count.toLocaleString()}
              </span>

              <span className="text-right tabular-nums text-[11px] font-semibold text-foreground sm:text-xs">
                {item.displayPercentage}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
