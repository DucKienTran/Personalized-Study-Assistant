import type { Metadata } from "next";
import { APP_CONFIG } from "@/constants/app";
import "./globals.css";

// Tiêu đề và Mô tả hiển thị trên thẻ Tab trình duyệt
export const metadata: Metadata = {
  title: `${APP_CONFIG.NAME} - Nền tảng học tập thông minh`,
  description: "Ứng dụng hỗ trợ học tập tích hợp AI.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className="antialiased text-gray-900 bg-gray-50">
        {/* Children ở đây sẽ là trang Login, Register, hoặc Dashboard tùy URL */}
        {children}
      </body>
    </html>
  );
}