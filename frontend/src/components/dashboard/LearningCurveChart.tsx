"use client";

import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Icon } from "@/components/shared/icons";
import { LearningCurvePoint } from "@/types/dashboard";

const PAGE_SIZE = 10;

const tooltipStyle = {
  border: "1px solid var(--border)",
  borderRadius: "10px",
  backgroundColor: "var(--popover)",
  color: "var(--popover-foreground)",
  boxShadow: "0 4px 12px rgb(36 31 22 / 0.08)",
};

export function LearningCurveChart({ data }: { data: LearningCurvePoint[] }) {
  const latestPage = Math.max(0, Math.ceil(data.length / PAGE_SIZE) - 1);
  const [page, setPage] = useState(latestPage);

  // If new attempts arrive while the user is already viewing the newest page,
  // keep the chart on the newest group instead of leaving it one page behind.
  const safePage = Math.min(page, latestPage);
  const start = safePage * PAGE_SIZE;

  const visibleData = useMemo(
    () => data.slice(start, start + PAGE_SIZE),
    [data, start]
  );

  const firstAttempt = visibleData[0]?.attempt;
  const lastAttempt = visibleData.at(-1)?.attempt;
  const rangeLabel = firstAttempt
    ? firstAttempt === lastAttempt
      ? `Quiz #${firstAttempt}`
      : `Quiz #${firstAttempt}–#${lastAttempt}`
    : "No quizzes";

  return (
    <div className="flex h-full min-h-0 w-full flex-col">
      <div className="mb-2 flex shrink-0 items-center justify-between gap-3 px-1">
        <p className="text-xs font-medium text-muted-foreground">{rangeLabel}</p>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setPage(Math.max(0, safePage - 1))}
            disabled={safePage === 0}
            aria-label="Show previous 10 quizzes"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-35"
          >
            <Icon name="chevron_left" className="text-lg" />
          </button>
          <button
            type="button"
            onClick={() => setPage(Math.min(latestPage, safePage + 1))}
            disabled={safePage >= latestPage}
            aria-label="Show next 10 quizzes"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-35"
          >
            <Icon name="chevron_right" className="text-lg" />
          </button>
        </div>
      </div>

      <div className="min-h-[250px] flex-1" role="img" aria-label="Accuracy across the selected quiz attempts">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={visibleData}
            margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
          >
            <CartesianGrid
              stroke="var(--border)"
              strokeDasharray="3 3"
              vertical={false}
            />
            <XAxis
              dataKey="attempt"
              tickFormatter={(value) => `#${value}`}
              interval={0}
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "var(--border)" }}
              allowDecimals={false}
            />
            <YAxis
              domain={[0, 100]}
              ticks={[0, 25, 50, 75, 100]}
              tickFormatter={(value) => `${value}%`}
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={48}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              labelFormatter={(label) => `Quiz #${label}`}
              formatter={(value) => [`${value}%`, "Accuracy"]}
            />
            <Line
              type="monotone"
              dataKey="accuracy"
              name="Accuracy"
              stroke="var(--primary)"
              strokeWidth={2.5}
              dot={{ r: 3.5, fill: "var(--card)", stroke: "var(--primary)", strokeWidth: 2 }}
              activeDot={{ r: 5, fill: "var(--primary)", strokeWidth: 0 }}
              animationDuration={700}
              animationEasing="ease-out"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
