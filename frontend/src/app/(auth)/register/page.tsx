"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { authService } from "@/services/auth.service";
import RedirectLoading from "@/components/states/RedirectLoading";
import { APP_CONFIG } from "@/constants/app";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
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

    setLoading(true);

    try {
      await authService.register({
        email: email,
        username: username,
        password: password,
        confirm_password: confirmPassword,
      });

      setShowRedirectLoading(true);

      setTimeout(() => {
        router.push("/login");
      }, 2000);

    } catch (err: any) {
      const errorData = err.response?.data?.detail;
      setError(Array.isArray(errorData) ? errorData[0]?.msg : errorData || "Đăng ký thất bại, vui lòng thử lại.");
      setLoading(false);
    }
  };

  if (showRedirectLoading) {
    return <RedirectLoading message="Đăng ký thành công! Đang chuyển hướng đến trang đăng nhập..." />;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#faf5ff] p-4">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl p-8 border border-[#f3e8ff]">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-[#581c87] mb-2">{APP_CONFIG.NAME}</h1>
          <p className="text-sm text-[#7e22ce]">Tạo tài khoản mới của bạn</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="relative border-b border-[#e9d5ff] focus-within:border-[#7c3aed] transition-colors duration-200 pb-1.5">
            <label className="block text-[13px] font-medium text-[#6b21a8] mb-1">Tên đăng nhập </label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-transparent text-[15px] text-black focus:outline-none placeholder-[#d8b4fe]"
              placeholder="nhan_vien_v1"
            />
          </div>

          <div className="relative border-b border-[#e9d5ff] focus-within:border-[#7c3aed] transition-colors duration-200 pb-1.5">
            <label className="block text-[13px] font-medium text-[#6b21a8] mb-1">Email</label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full bg-transparent text-[15px] text-black focus:outline-none placeholder-[#d8b4fe]" placeholder="name@example.com" />
          </div>

          <div className="relative border-b border-[#e9d5ff] focus-within:border-[#7c3aed] transition-colors duration-200 pb-1.5">
            <label className="block text-[13px] font-medium text-[#6b21a8] mb-1">Mật khẩu</label>
            <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="w-full bg-transparent text-[15px] text-black focus:outline-none placeholder-[#d8b4fe]" placeholder="••••••••" />
          </div>

          <div className="relative border-b border-[#e9d5ff] focus-within:border-[#7c3aed] transition-colors duration-200 pb-1.5">
            <label className="block text-[13px] font-medium text-[#6b21a8] mb-1">Xác nhận mật khẩu</label>
            <input type="password" required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className="w-full bg-transparent text-[15px] text-black focus:outline-none placeholder-[#d8b4fe]" placeholder="••••••••" />
          </div>

          {error && (
            <div className="p-3 text-[13px] font-medium text-[#991b1b] bg-[#fef2f2] border border-[#fca5a5] rounded-lg text-center animate-fade-in">
              {error}
            </div>
          )}

          <div className="pt-2">
            <button type="submit" disabled={loading} className="w-full py-2.5 bg-[#7c3aed] hover:bg-[#6d28d9] text-white text-[14px] font-semibold rounded-full shadow-sm transition-colors duration-150 disabled:bg-[#cbd5e1]">
              {loading ? "Đang xử lý..." : "Đăng Ký"}
            </button>
          </div>
        </form>

        <div className="text-center mt-6 text-[13px] text-[#6b21a8]">
          Đã có tài khoản?{" "}
          <Link href="/login" className="font-semibold text-[#7c3aed] hover:underline">
            Đăng nhập ngay
          </Link>
        </div>
      </div>
    </div>
  );
}