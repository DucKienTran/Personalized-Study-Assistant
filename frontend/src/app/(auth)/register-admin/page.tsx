"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { authService } from "@/services/auth.service";
import RedirectLoading from "@/components/states/RedirectLoading";
import { APP_CONFIG } from "@/constants/app";

export default function RegisterAdminPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [adminKey, setAdminKey] = useState("");
  const [error, setError] = useState("");
  const [showRedirectLoading, setShowRedirectLoading] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.SyntheticEvent) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Mật khẩu xác nhận không trùng khớp!");
      return;
    }
    if (!adminKey.trim()) {
      setError("Vui lòng nhập Mã xác thực Admin!");
      return;
    }

    setLoading(true);

    try {
      // Dùng hàm registerAdmin từ service
      await authService.registerAdmin({
        email: email,
        password: password,
        confirm_password: confirmPassword,
      }, adminKey);

      setShowRedirectLoading(true);
      
      setTimeout(() => {
        router.push("/login");
      }, 2000);

    } catch (err: any) {
      const errorData = err.response?.data?.detail;
      setError(Array.isArray(errorData) ? (errorData[0]?.msg || "Dữ liệu không hợp lệ.") : errorData || "Đăng ký Admin thất bại!");
      setLoading(false);
    }
  };

  if (showRedirectLoading) {
    return <RedirectLoading message="Đăng ký Admin thành công! Đang chuyển hướng..." />;
  }

  return (
    <div className="w-screen h-screen overflow-hidden flex items-center justify-center bg-[#f3e8ff] font-sans m-0 p-4 select-none">
      <div className="w-full max-w-[400px] bg-white p-8 sm:p-10 rounded-2xl shadow-sm border border-[#e9d5ff]">
        
        <div className="text-center mb-6">
          <h1 className="text-[26px] font-semibold tracking-[1px] text-[#581c87] font-serif">
            {APP_CONFIG.NAME}
          </h1>
          <p className="text-[13px] text-[#7e22ce] mt-1 font-medium">Quản trị viên</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative border-b border-[#e9d5ff] focus-within:border-[#7c3aed] transition-colors duration-200 pb-1">
            <label className="block text-[12px] font-medium text-[#6b21a8] mb-0.5">Email</label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full bg-transparent text-[15px] text-black focus:outline-none placeholder-[#d8b4fe]" placeholder="admin@example.com" />
          </div>

          <div className="relative border-b border-[#e9d5ff] focus-within:border-[#7c3aed] transition-colors duration-200 pb-1">
            <label className="block text-[12px] font-medium text-[#6b21a8] mb-0.5">Mật khẩu</label>
            <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="w-full bg-transparent text-[15px] text-black focus:outline-none placeholder-[#d8b4fe]" placeholder="••••••••" />
          </div>

          <div className="relative border-b border-[#e9d5ff] focus-within:border-[#7c3aed] transition-colors duration-200 pb-1">
            <label className="block text-[12px] font-medium text-[#6b21a8] mb-0.5">Xác nhận mật khẩu</label>
            <input type="password" required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className="w-full bg-transparent text-[15px] text-black focus:outline-none placeholder-[#d8b4fe]" placeholder="••••••••" />
          </div>

          <div className="relative border-b border-[#c084fc] focus-within:border-[#7c3aed] transition-colors duration-200 pb-1">
            <label className="block text-[12px] font-semibold text-[#7c3aed] mb-0.5">Mã xác thực Admin (Admin Key)</label>
            <input type="text" required value={adminKey} onChange={(e) => setAdminKey(e.target.value)} className="w-full bg-transparent text-[15px] text-black focus:outline-none placeholder-[#e9d5ff] font-mono tracking-wider" placeholder="Nhập mã cấp quyền..." />
          </div>

          {error && (
            <div className="p-2.5 text-[12px] font-medium text-[#991b1b] bg-[#fef2f2] border border-[#fca5a5] rounded-lg text-center">
              {error}
            </div>
          )}

          <div className="pt-1">
            <button type="submit" disabled={loading} className="w-full py-2.5 bg-[#7c3aed] hover:bg-[#6d28d9] text-white text-[14px] font-semibold rounded-full shadow-sm transition-colors duration-150 disabled:bg-[#cbd5e1]">
              {loading ? "Đang xử lý..." : "Kích Hoạt Tài Khoản Admin"}
            </button>
          </div>
        </form>

        <div className="mt-4 text-center text-[13px] text-[#7e22ce]">
          Quay lại trang chính?{" "}
          <Link href="/login" className="font-semibold text-[#7c3aed] hover:underline ml-1">Đăng nhập</Link>
        </div>

      </div>
    </div>
  );
}