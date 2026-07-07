import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { AUTH_CONFIG } from "@/constants/auth";

export function middleware(request: NextRequest) {
  const token = request.cookies.get(AUTH_CONFIG.COOKIE_NAME)?.value;
  const { pathname } = request.nextUrl;

  const authRoutes = ["/login", "/register", "/register-admin"];
  const isAuthRoute = authRoutes.includes(pathname);

  if (pathname === "/") {
    if (token) {
      // Trường hợp đã đăng nhập, cho phép vào workspace
      return NextResponse.next();
    }
    // Trường hợp chưa đăng nhập, cho phép vào landing page
    return NextResponse.next();
  }

  // Trường hợp chưa đăng nhập mà truy cập vào các route nội bộ của hệ thống (workspace)
  const internalRoutes = ["/documents", "/quizzes", "/chat"];
  const isInternalRoute = internalRoutes.some(route => pathname === route || pathname.startsWith(route + "/"));

  if (!token && isInternalRoute) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Trường hợp đã đăng nhập mà quay lại các trang Authentication 
  if (token && isAuthRoute) {
    return NextResponse.redirect(new URL("/", request.url)); // Sẽ nhảy về "/" và điều hướng tiếp vào Workspace
  }

  return NextResponse.next();
}

export const config = {
  // Đăng ký toàn bộ các route kiểm soát để tối ưu performance cho Next.js
  matcher: [
    "/",
    "/login",
    "/register",
    "/register-admin",
    "/documents/:path*",
    "/quizzes/:path*",
    "/chat/:path*",
    "/dashboard/:path*",
    "/history/:path*",
  ],
};