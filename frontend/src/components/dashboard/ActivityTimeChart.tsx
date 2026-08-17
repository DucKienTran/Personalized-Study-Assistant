"use client";

import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ActivityPoint } from "@/types/dashboard";

const WINDOW_DAYS = 7;

const tooltipStyle = {
  border: "1px solid var(--border)",
  borderRadius: "10px",
  backgroundColor: "var(--popover)",
  color: "var(--popover-foreground)",
  boxShadow: "0 4px 12px rgb(36 31 22 / 0.08)",
};

function parseDate(date: string) {
  return new Date(`${date}T00:00:00`);
}

function formatDuration(seconds: number) {
  if (seconds < 60) return seconds > 0 ? "<1m" : "0m";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  if (hours === 0) return `${minutes}m`;
  return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
}

function formatAxisDuration(seconds: number) {
  if (seconds === 0) return "0";
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  const hours = seconds / 3600;
  return Number.isInteger(hours) ? `${hours}h` : `${hours.toFixed(1)}h`;
}

function formatRange(data: ActivityPoint[]) {
  if (data.length === 0) return "";
  const start = parseDate(data[0].date);
  const end = parseDate(data[data.length - 1].date);
  const sameMonth = start.getMonth() === end.getMonth();
  const startLabel = start.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
  const endLabel = end.toLocaleDateString(undefined, sameMonth
    ? { day: "numeric" }
    : { month: "short", day: "numeric" });
  return `${startLabel} – ${endLabel}`;
}

function barFill(seconds: number, maxSeconds: number) {
  if (seconds <= 0 || maxSeconds <= 0) return "var(--muted)";
  const ratio = seconds / maxSeconds;
  const strength = Math.round(42 + ratio * 58);
  return `color-mix(in srgb, var(--primary) ${strength}%, var(--primary-tint))`;
}

export function ActivityTimeChart({ data }: { data: ActivityPoint[] }) {
  const [windowOffset, setWindowOffset] = useState(0);

  const windowData = useMemo(() => {
    const end = Math.max(0, data.length - windowOffset * WINDOW_DAYS);
    const start = Math.max(0, end - WINDOW_DAYS);
    const slice = data.slice(start, end);

    // The API normally returns a dense daily series. Padding keeps the visual
    // contract at exactly seven columns even for a brand-new installation.
    if (slice.length >= WINDOW_DAYS || slice.length === 0) return slice;
    const first = parseDate(slice[0].date);
    const padding: ActivityPoint[] = [];
    for (let i = WINDOW_DAYS - slice.length; i > 0; i -= 1) {
      const date = new Date(first);
      date.setDate(first.getDate() - i);
      padding.push({
        date: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`,
        study_seconds: 0,
      });
    }
    return [...padding, ...slice];
  }, [data, windowOffset]);

  const maxOffset = Math.max(0, Math.ceil(data.length / WINDOW_DAYS) - 1);
  const maxSeconds = Math.max(0, ...windowData.map((point) => point.study_seconds));
  const totalSeconds = windowData.reduce((sum, point) => sum + point.study_seconds, 0);

  return (
    <div className="flex h-full min-h-[300px] w-full flex-col">
      <div className="mb-3 flex items-center justify-between gap-3 px-1">
        <div>
          <p className="text-sm font-medium text-foreground">{formatRange(windowData)}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {formatDuration(totalSeconds)} total
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            className="inline-flex size-8 items-center justify-center rounded-md border border-border bg-card text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-35"
            onClick={() => setWindowOffset((value) => Math.min(maxOffset, value + 1))}
            disabled={windowOffset >= maxOffset}
            aria-label="Show previous 7 days"
          >
            ‹
          </button>
          <button
            type="button"
            className="inline-flex size-8 items-center justify-center rounded-md border border-border bg-card text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-35"
            onClick={() => setWindowOffset((value) => Math.max(0, value - 1))}
            disabled={windowOffset === 0}
            aria-label="Show next 7 days"
          >
            ›
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1" role="img" aria-label="Daily study time for seven days">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={windowData} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={(value) => parseDate(value).toLocaleDateString(undefined, { weekday: "short" })}
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "var(--border)" }}
            />
            <YAxis
              tickFormatter={formatAxisDuration}
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={46}
              allowDecimals={false}
              domain={[0, "auto"]}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              cursor={{ fill: "var(--muted)", opacity: 0.35 }}
              labelFormatter={(label) => parseDate(String(label)).toLocaleDateString(undefined, {
                weekday: "long",
                month: "short",
                day: "numeric",
              })}
              formatter={(value) => [formatDuration(Number(value)), "Study time"]}
            />
            <Bar dataKey="study_seconds" name="Study time" radius={[7, 7, 2, 2]} maxBarSize={44}>
              {windowData.map((point) => (
                <Cell key={point.date} fill={barFill(point.study_seconds, maxSeconds)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
