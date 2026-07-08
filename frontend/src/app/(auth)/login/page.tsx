  "use client";

  import React, { useState } from "react";
  import { useRouter } from "next/navigation";
  import Link from "next/link";
  import { authService } from "@/services/auth.service";
  import RedirectLoading from "@/components/states/RedirectLoading";
  import { APP_CONFIG } from "@/constants/app"; 

  export default function LoginPage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const [showRedirectLoading, setShowRedirectLoading] = useState(false);
    const [isAdminMode, setIsAdminMode] = useState(false);
    const [clickCount, setClickCount] = useState(0);

    const handleTitleClick = () => {
      setClickCount((prev) => {
        if (prev + 1 === 5) {
          setIsAdminMode(true); 
          return 0;
        }
        return prev + 1;
      });
    };

    const handleSubmit = async (e: React.SyntheticEvent) => {
      e.preventDefault();
      setError("");
      setLoading(true);

      try {
        const data = await authService.login(email, password);
        localStorage.setItem("access_token", data.access_token);
        setShowRedirectLoading(true);

        setTimeout(() => {
          router.push("/dashboard"); 
        }, 2000);

      } catch (err: any) {
        const errorData = err.response?.data?.detail;
        if (Array.isArray(errorData)) {
          setError(errorData[0]?.msg || "Dữ liệu nhập vào không hợp lệ.");
        } else if (typeof errorData === "string") {
          setError(errorData);
        } else {
          setError("Đăng nhập thất bại. Vui lòng kiểm tra lại email hoặc mật khẩu!");
        }
        setLoading(false);
      }
    };

    if (showRedirectLoading) {
      return <RedirectLoading message="Đăng nhập thành công! Đang vào hệ thống..." />;
    }

    return (
      <div className="w-screen h-screen overflow-hidden flex items-center justify-center bg-[#e6f4ea] font-sans m-0 p-4 select-none">
        <div className="w-full max-w-[400px] bg-white p-8 sm:p-10 rounded-2xl shadow-sm border border-[#d2ebd9]">
          
          <div className="text-center mb-8">
            <h1 
              onClick={handleTitleClick}
              className="text-[26px] font-semibold tracking-[1px] text-[#2e4a38] font-serif cursor-default select-none"
            >
              {APP_CONFIG.NAME} 
            </h1>
          </div>

          {error && (
            <div className="p-3 mb-5 text-[13px] font-medium text-[#991b1b] bg-[#fef2f2] border border-[#fca5a5] rounded-lg text-center">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-[13px] font-medium text-[#4a6351] mb-1.5">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 bg-[#f9fbf9] border border-[#cbdcd0] rounded-lg text-[15px] text-black placeholder-[#a3b8ab] focus:outline-none focus:border-[#428a5d] focus:ring-1 focus:ring-[#428a5d] transition-all"
                placeholder="user@example.com"
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="text-[13px] font-medium text-[#4a6351]">Mật khẩu</label>
                <a href="#" className="text-[12px] font-medium text-[#428a5d] hover:underline">Quên mật khẩu?</a>
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 bg-[#f9fbf9] border border-[#cbdcd0] rounded-lg text-[15px] text-black placeholder-[#a3b8ab] focus:outline-none focus:border-[#428a5d] focus:ring-1 focus:ring-[#428a5d] transition-all"
                placeholder="••••••••"
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 bg-[#3b7a52] hover:bg-[#2e5f3f] text-white text-[14px] font-semibold rounded-lg shadow-sm transition-colors duration-150 disabled:bg-[#cbd5e1] disabled:cursor-not-allowed"
              >
                {loading ? "Đang xử lý..." : "Đăng Nhập"}
              </button>
            </div>
          </form>

          <div className="mt-4 text-center text-[13px] text-[#6b8775]">
            Bạn là người mới?{" "}
            <Link 
              href={isAdminMode ? "/register-admin" : "/register"} 
              className="font-semibold text-[#3b7a52] hover:underline ml-1"
            >
              Tạo tài khoản
            </Link>
          </div>

        </div>
      </div>
    );
  }