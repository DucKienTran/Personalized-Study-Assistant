// src/constants/workspace.ts

export interface FeatureItem {
    title: string;
    description: string;
    iconId: "summary" | "quiz" | "grade" | "chat";
    href: string;
    color: "blue" | "purple" | "amber" | "emerald"; // Đổi thành các key màu cố định
}

export const WORKSPACE_FEATURES: FeatureItem[] = [
    {
        title: "Tóm tắt tài liệu",
        description: "Trích xuất nội dung cốt lõi, sơ đồ tư duy từ các file tài liệu dài nhanh chóng.",
        iconId: "summary",
        href: "/documents",
        color: "blue"
    },
    {
        title: "Tạo bài kiểm tra",
        description: "Tự động thiết kế bộ câu hỏi trắc nghiệm, tự luận bám sát nội dung bài học.",
        iconId: "quiz",
        href: "/quizzes",
        color: "purple"
    },
    {
        title: "Chấm bài kiểm tra",
        description: "Tải lên đáp án hoặc bài làm để AI phân tích lỗi sai và chấm điểm chi tiết.",
        iconId: "grade",
        href: "/quizzes/grade",
        color: "amber"
    },
    {
        title: "Hỏi đáp",
        description: "Trò chuyện trực tiếp với trợ lý thông minh giải đáp mọi thắc mắc học tập.",
        iconId: "chat",
        href: "/chat",
        color: "emerald"
    }
];