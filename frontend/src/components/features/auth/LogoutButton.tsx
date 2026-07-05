"use client";

import { useRouter } from "next/navigation";
import { authService } from "@/services/auth.service"; 
import { AUTH_CONFIG } from "@/constants/auth";

export default function LogoutButton() {
  const router = useRouter();

  const handleLogout = async () => {
      try {
      await authService.logout();
    } catch (err) {
      console.error("Lỗi gọi API logout:", err);
    } finally {
      router.push("/login");
    }
  };

  return (
    <button
      onClick={handleLogout}
      className="px-6 py-2.5 bg-[#991b1b] hover:bg-[#7f1d1d] text-white text-[14px] font-medium rounded-lg shadow-sm transition-colors duration-200"
    >
      Đăng xuất
    </button>
  );
}