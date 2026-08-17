"use client";

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

import {
  QUESTION_TYPE_COLORS,
  QUESTION_TYPE_LABELS,
} from "@/constants/question-type-colors";
import { QuestionTypeStats } from "@/types/dashboard";

const SHORT_LABELS: Record<string, string> = {
  essay: "Essay",
  fill_blank: "Fill Blank",
  multiple_choice: "Multiple Choice",
  multiple_response: "Multiple Response",
  short_answer: "Short Answer",
  true_false: "True / False",
};

/* -------------------------------------------------------------------------- */
/* X Axis                                                                     */
/* -------------------------------------------------------------------------- */

function AxisTick({ x, y, payload }: any) {
  const raw = String(payload.value);

  const label =
    SHORT_LABELS[raw] ??
    QUESTION_TYPE_LABELS[raw] ??
    raw;

  const words = label.split(" ");

  let lines = [label];

  if (words.length > 1 && label.length > 11) {
    const splitAt = Math.ceil(words.length / 2);

    lines = [
      words.slice(0, splitAt).join(" "),
      words.slice(splitAt).join(" "),
    ];
  }

  // Khoảng cách từ X-axis xuống label
  const LABEL_GAP = 8;

  return (
    <g transform={`translate(${x}, ${Number(y) + LABEL_GAP})`}>
      <text
        x={0}
        y={0}
        textAnchor="middle"
        dominantBaseline="hanging"
        fill="var(--foreground)"
        fillOpacity={0.78}
        fontSize={11}
        fontWeight={500}
      >
        {lines.map((line, index) => (
          <tspan
            key={`${line}-${index}`}
            x={0}
            dy={index === 0 ? 0 : 15}
          >
            {line}
          </tspan>
        ))}
      </text>
    </g>
  );
}

function AccuracyTooltip({ active, payload }: any) {
  if (!active || payload?.[0]?.value == null) return null;

  const accuracy = Number(payload[0].value).toFixed(1).replace(".0", "");

  return (
    <div
      className="rounded-[10px] border border-border bg-popover px-3 py-2 text-xs font-medium text-popover-foreground shadow-[0_4px_12px_rgb(36_31_22_/_0.08)]"
    >
      Accuracy: {accuracy}%
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Chart                                                                      */
/* -------------------------------------------------------------------------- */

export function QuestionTypeAccuracyChart({
  data,
}: {
  data: QuestionTypeStats[];
}) {
  return (
    <div
      className="h-full min-h-[300px] w-full sm:min-h-[280px]"
      role="img"
      aria-label="Accuracy by question type"
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{
            top: 38,
            right: 8,
            left: -8,
            bottom: 8,
          }}
          barCategoryGap="30%"
        >
          <CartesianGrid
            stroke="var(--border)"
            strokeDasharray="3 3"
            vertical={false}
          />

          <XAxis
            dataKey="question_type"
            interval={0}
            height={68}
            tick={<AxisTick />}
            tickLine={false}
            axisLine={{
              stroke: "var(--border)",
            }}
          />

          <YAxis
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
            tickFormatter={(value) => `${value}%`}
            tick={{
              fill: "var(--muted-foreground)",
              fontSize: 11,
            }}
            tickLine={false}
            axisLine={false}
            width={48}
          />

          <Tooltip
            cursor={{ fill: "var(--muted)", opacity: 0.2 }}
            content={<AccuracyTooltip />}
          />

          <Bar
            dataKey="accuracy"
            name="Accuracy"
            radius={[7, 7, 0, 0]}
            maxBarSize={58}
            animationDuration={700}
            animationEasing="ease-out"
          >
            {data.map((item) => (
              <Cell
                key={item.question_type}
                fill={QUESTION_TYPE_COLORS[item.question_type]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
