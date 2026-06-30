"use client";

// Sửa lại đường dẫn import chuẩn theo Alias (@/) của Next.js
// Lát nữa chúng ta sẽ bê file LogoutButton vào thư mục này
import LogoutButton from "@/components/features/auth/LogoutButton"; 
import { APP_CONFIG } from "@/constants/app";

export default function DashboardPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#e6f4ea] text-black">
      <div className="text-center p-10 bg-white shadow-sm border border-[#d2ebd9] rounded-2xl max-w-md w-full">
        <h1 className="text-2xl font-bold mb-3 text-[#2e4a38]">
          Chào mừng đến với {APP_CONFIG.NAME}!
        </h1>
        <p className="text-[#5c7a65] mb-8 text-sm">
          Bạn đã đăng nhập thành công vào hệ thống.
        </p>
        
        {/* Nút Logout */}
        <LogoutButton />
      </div>
    </div>
  );
}