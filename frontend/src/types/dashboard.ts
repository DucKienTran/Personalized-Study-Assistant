// src/types/dashboard.ts

export interface DashboardStatsOut {
  notebook_count: number;
  document_count: number;
  quiz_count: number;
  message_count: number;
}

export interface ActivityPoint {
  date: string;
  study_seconds: number;
}

export interface LearningCurvePoint {
  attempt: number;
  accuracy: number;
}

export interface AggregateLearningStats {
  completed_attempts: number;
  overall_accuracy: number | null;
  total_study_seconds: number;
}

export interface QuestionTypeStats {
  question_type: string;
  answered_count: number;
  correct_count: number;
  accuracy: number;
}

export interface TrendStat {
  recent_value: number;
  previous_value: number;
  delta: number;
  sample_size: number;
}

export interface QuestionTypeHighlight {
  question_type: string;
  accuracy: number;
  answered_count: number;
}

export interface DashboardCandidateStats {
  current_streak_days: number;
  accuracy_trend: TrendStat | null;
  time_spent_trend: TrendStat | null;
  best_question_type: QuestionTypeHighlight | null;
  worst_question_type: QuestionTypeHighlight | null;
  weekly_activity_change: {
    current_count: number;
    previous_count: number;
    percent_change: number | null;
  };
}

export interface DashboardAnalyticsOut {
  activity: ActivityPoint[];
  learning_curve: LearningCurvePoint[];
  aggregate: AggregateLearningStats;
  question_types: QuestionTypeStats[];
  candidates: DashboardCandidateStats;
}

export interface DashboardInsightOut {
  text: string;
  selected_stats: Array<{ key: string; label: string; value: string }>;
  has_meaningful_data: boolean;
  cached: boolean;
  generated_at: string | null;
  refresh_available_at: string | null;
}
