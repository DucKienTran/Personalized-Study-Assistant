    import api from "./api";
    import { DashboardAnalyticsOut, DashboardInsightOut, DashboardStatsOut } from "@/types/dashboard";

    interface BaseResponse<T> {
    message?: string;
    data: T;
    }

    class DashboardService {
    /**
     * Get aggregate counts (notebooks, documents, quizzes, messages) for the current user.
     */
    async getStats(): Promise<DashboardStatsOut> {
        const response = await api.get<BaseResponse<DashboardStatsOut>>(
        "/dashboard/stats"
        );
        return response.data.data;
    }

    async getAnalytics(): Promise<DashboardAnalyticsOut> {
        const response = await api.get<BaseResponse<DashboardAnalyticsOut>>(
        "/dashboard/analytics"
        );
        return response.data.data;
    }

    async getInsight(): Promise<DashboardInsightOut> {
        const response = await api.get<BaseResponse<DashboardInsightOut>>(
        "/dashboard/insight"
        );
        return response.data.data;
    }

    async refreshInsight(): Promise<DashboardInsightOut> {
        const response = await api.post<BaseResponse<DashboardInsightOut>>(
        "/dashboard/insight/refresh"
        );
        return response.data.data;
    }
    }

    export const dashboardService = new DashboardService();
