import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { AUTH_CONFIG } from "@/constants/auth";

export function middleware(request: NextRequest) {
  // Lấy token từ Cookie gửi lên
  const token = request.cookies.get(AUTH_CONFIG.COOKIE_NAME)?.value;    
  const { pathname } = request.nextUrl;

  // Trường hợp người dùng cố tính vào dashboard và mà chưa đăng nhập
  if (pathname.startsWith("/dashboard") && !token) {
    // Đá ngược người dùng về trang Login
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Trường hợp người dùng đã đăng nhập nhưng bấm vào đăng ký
  if ((pathname === "/login" || pathname === "/register" || pathname === "/register-admin") && token) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*", 
    "/login",
    "/register",
    "/register-admin",
  ],
};