"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ActivityTimeChart } from "@/components/dashboard/ActivityTimeChart";
import { QuestionTypeDistribution } from "@/components/dashboard/QuestionTypeDistribution";
import { LearningCurveChart } from "@/components/dashboard/LearningCurveChart";
import { QuestionTypeAccuracyChart } from "@/components/dashboard/QuestionTypeAccuracyChart";
import { StatCards } from "@/components/dashboard/StatCards";
import { Icon } from "@/components/shared/icons";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { QUESTION_TYPE_COLORS, QUESTION_TYPE_LABELS } from "@/constants/question-type-colors";
import { useDashboardInertialScroll } from "@/hooks/useDashboardInertialScroll";
import { dashboardService } from "@/services/dashboard.service";
import {
  DashboardAnalyticsOut,
  DashboardInsightOut,
  DashboardStatsOut,
} from "@/types/dashboard";

const tooltipStyle = {
  border: "1px solid var(--border)",
  borderRadius: "10px",
  backgroundColor: "var(--popover)",
  color: "var(--popover-foreground)",
  boxShadow: "0 4px 12px rgb(36 31 22 / 0.08)",
};

const formatDuration = (seconds: number) => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  if (hours === 0) return `${minutes}m`;
  return `${hours}h ${minutes}m`;
};

function EmptyChart({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full min-h-48 items-center justify-center rounded-lg border border-dashed border-border bg-muted/20 px-6 text-center text-sm text-muted-foreground">
      {children}
    </div>
  );
}

function ChartCard({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Card className="min-h-[360px] gap-3 py-4 sm:min-h-[400px] lg:min-h-0 lg:py-5">
      <CardHeader className="shrink-0 px-4 lg:px-5">
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="min-h-0 flex-1 px-3 lg:px-4">{children}</CardContent>
    </Card>
  );
}

export function DashboardCharts() {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [stats, setStats] = useState<DashboardStatsOut | null>(null);
  const [analytics, setAnalytics] = useState<DashboardAnalyticsOut | null>(null);
  const [insight, setInsight] = useState<DashboardInsightOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [refreshingInsight, setRefreshingInsight] = useState(false);
  const [clock, setClock] = useState(() => Date.now());
  useDashboardInertialScroll(
    scrollContainerRef,
    !loading && !error && Boolean(stats && analytics)
  );

  useEffect(() => {
    let cancelled = false;

    Promise.all([dashboardService.getStats(), dashboardService.getAnalytics()])
      .then(([statsResult, analyticsResult]) => {
        if (cancelled) return;
        setStats(statsResult);
        setAnalytics(analyticsResult);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    dashboardService
      .getInsight()
      .then((result) => {
        if (!cancelled) setInsight(result);
      })
      .catch(() => {
        if (!cancelled) {
          setInsight({
            text: "Keep showing up. Each completed quiz gives you a clearer view of your progress.",
            selected_stats: [],
            has_meaningful_data: false,
            cached: false,
            generated_at: null,
            refresh_available_at: null,
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!insight?.refresh_available_at) return;
    setClock(Date.now());
    const timer = window.setInterval(() => setClock(Date.now()), 15_000);
    return () => window.clearInterval(timer);
  }, [insight?.refresh_available_at]);

  const refreshAvailableAt = insight?.refresh_available_at
    ? new Date(insight.refresh_available_at).getTime()
    : 0;
  const refreshMinutesRemaining = refreshAvailableAt
    ? Math.max(0, Math.ceil((refreshAvailableAt - clock) / 60_000))
    : 0;
  const canRefreshInsight = Boolean(
    insight?.has_meaningful_data &&
    refreshMinutesRemaining === 0 &&
    !refreshingInsight
  );

  const handleRefreshInsight = async () => {
    if (!canRefreshInsight) return;
    setRefreshingInsight(true);
    try {
      const result = await dashboardService.refreshInsight();
      setInsight(result);
      setClock(Date.now());
    } catch {
      // Keep the current cached insight when regeneration is unavailable.
    } finally {
      setRefreshingInsight(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full p-6 lg:p-8">
        <div className="mx-auto grid h-full max-w-6xl grid-rows-[auto_auto_1fr] gap-5">
          <Skeleton className="h-14 w-72" />
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {[1, 2, 3, 4].map((item) => <Skeleton key={item} className="h-32" />)}
          </div>
          <Skeleton className="min-h-0" />
        </div>
      </div>
    );
  }

  if (error || !stats || !analytics) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="rounded-xl border border-dashed border-border bg-card p-10 text-center text-sm text-muted-foreground">
          Dashboard analytics could not be loaded.
        </div>
      </div>
    );
  }

  const hasActivity = analytics.activity.some(
    (point) => point.study_seconds > 0
  );
  const aggregateItems = [
    { label: "Completed attempts", value: analytics.aggregate.completed_attempts },
    {
      label: "Overall accuracy",
      value: analytics.aggregate.overall_accuracy === null
        ? "--"
        : `${analytics.aggregate.overall_accuracy}%`,
    },
    { label: "Total study time", value: formatDuration(analytics.aggregate.total_study_seconds) },
  ];

  return (
    <div ref={scrollContainerRef} data-dashboard-scroll className="dashboard-scroll scrollbar-hidden h-full overflow-y-auto overscroll-y-contain">
      <section className="dashboard-snap-section p-4 sm:p-5 lg:h-full lg:min-h-full lg:p-7">
        <div className="dashboard-section-content mx-auto grid max-w-6xl grid-rows-[auto_auto_auto] gap-4 lg:h-full lg:grid-rows-[auto_auto_minmax(0,1fr)]">
          <div>
            <h1 className="font-heading text-2xl font-semibold tracking-tight text-foreground">Dashboard</h1>
            <p className="mt-1 text-sm text-muted-foreground">See your study rhythm and progress over time.</p>
          </div>

          <StatCards stats={stats} />

          <div className="grid min-h-0 grid-cols-1 gap-3 lg:grid-cols-[1.1fr_0.9fr] lg:gap-4">
            <Card className="min-h-0 gap-3 py-4">
              <CardHeader className="px-4">
                <CardTitle>Learning summary</CardTitle>
                <CardDescription>Your all-time completed quiz activity.</CardDescription>
              </CardHeader>
              <CardContent className="flex min-h-0 flex-1 flex-col gap-3 px-4">
                <div className="grid grid-cols-3 gap-2">
                  {aggregateItems.map((item) => (
                    <div key={item.label} className="rounded-xl bg-muted/60 p-3">
                      <p className="font-heading text-base font-semibold text-foreground lg:text-xl">{item.value}</p>
                      <p className="mt-1 text-[11px] leading-4 text-muted-foreground">{item.label}</p>
                    </div>
                  ))}
                </div>
                {insight?.selected_stats.length ? (
                  <div className="grid grid-cols-1 gap-1 border-t border-border pt-2 lg:grid-cols-3 lg:gap-2 lg:pt-3">
                    {insight.selected_stats.map((item) => (
                      <div key={item.key}>
                        <p className="text-sm font-semibold text-primary">{item.value}</p>
                        <p className="text-[11px] text-muted-foreground">{item.label}</p>
                      </div>
                    ))}
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <Card className="min-h-0 gap-3 border-primary/15 bg-[var(--primary-tint)] py-4">
              <CardHeader className="px-4">
                <div className="flex items-center gap-2">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
                    <Icon name="auto_awesome" className="text-base" />
                  </span>
                  <div>
                    <CardTitle>Study Reflection</CardTitle>
                    <CardDescription className="hidden lg:block">A short reflection on your learning progress.</CardDescription>
                  </div>
                </div>
                <CardAction>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger
                        render={<span className="inline-flex" />}
                      >
                        <button
                          type="button"
                          onClick={handleRefreshInsight}
                          disabled={!canRefreshInsight}
                          aria-label="Refresh study reflection"
                          className="flex h-8 w-8 items-center justify-center rounded-full border border-primary/20 bg-card/70 text-primary transition-all duration-500 hover:bg-card disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          <Icon
                            name="refresh"
                            className={`text-base ${refreshingInsight ? "animate-spin" : ""}`}
                          />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent>
                        {refreshMinutesRemaining > 0
                          ? `Can refresh again in ${refreshMinutesRemaining} min`
                          : "Refresh study reflection"}
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </CardAction>
              </CardHeader>
              <CardContent className="flex min-h-0 flex-1 flex-col justify-center gap-2 px-4">
                {insight ? (
                  <>
                    <p className="font-heading text-sm leading-6 text-foreground lg:text-base lg:leading-7">{insight.text}</p>
                  </>
                ) : (
                  <div className="w-full space-y-3">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-4/5" />
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      <section className="dashboard-snap-section p-4 sm:p-5 lg:h-full lg:min-h-full lg:p-7">
        <div className="dashboard-section-content mx-auto flex max-w-6xl min-h-0 flex-col gap-4 lg:h-full">
          <div className="shrink-0">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Trends</p>
            <h2 className="mt-1 font-heading text-xl font-semibold text-foreground">Learning over time</h2>
          </div>
          <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-2 lg:grid-rows-1">
            <ChartCard
              title="Study time"
              description="Time spent actively using LearningAid each day."
            >
              {!hasActivity ? (
                <EmptyChart>Your activity will appear here after you take a quiz or send a message.</EmptyChart>
              ) : (
                <ActivityTimeChart data={analytics.activity} />
              )}
            </ChartCard>

            <ChartCard
              title="Learning curve"
              description="Accuracy across your 10 most recent quiz attempts."
            >
              {analytics.learning_curve.length === 0 ? (
                <EmptyChart>
                  Complete your first quiz to start tracking your learning curve.
                </EmptyChart>
              ) : (
                <LearningCurveChart data={analytics.learning_curve} />
              )}
            </ChartCard>
          </div>
        </div>
      </section>

      <section className="dashboard-snap-section p-4 sm:p-5 lg:h-full lg:min-h-full lg:p-7">
        <div className="dashboard-section-content mx-auto flex max-w-6xl min-h-0 flex-col gap-4 lg:h-full">
          <div className="shrink-0">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Question types</p>
            <h2 className="mt-1 font-heading text-xl font-semibold text-foreground">Practice mix and accuracy</h2>
          </div>
          <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-2 lg:grid-rows-1">
            <ChartCard title="Questions practiced" description="Answered questions grouped by type.">
              {analytics.question_types.length === 0 ? (
                <EmptyChart>Question type distribution will appear after your first completed quiz.</EmptyChart>
              ) : (
                <QuestionTypeDistribution data={analytics.question_types} />
              )}
            </ChartCard>

            <ChartCard
              title="Accuracy by type"
              description="Correct answers as a percentage of answered questions."
            >
              {analytics.question_types.length === 0 ? (
                <EmptyChart>
                  Accuracy by question type will appear after your first completed quiz.
                </EmptyChart>
              ) : (
                <QuestionTypeAccuracyChart data={analytics.question_types} />
              )}
            </ChartCard>
          </div>
        </div>
      </section>
    </div>
  );
}
