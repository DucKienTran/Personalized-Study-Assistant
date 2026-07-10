import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { AUTH_CONFIG } from "@/constants/auth";

export function middleware(request: NextRequest) {
  const token = request.cookies.get(AUTH_CONFIG.COOKIE_NAME)?.value;
  const { pathname } = request.nextUrl;

  const authRoutes = ["/login", "/register", "/register-admin"];
  const isAuthRoute = authRoutes.includes(pathname);

  // Phân luồng giữa Landing Page Marketing và Workspace
  if (pathname === "/") {
    // Cho phép Next.js đi tiếp để tự động nhận diện Route Group (marketing) hoặc (workspace)
    return NextResponse.next();
  }

  const internalRoutes = ["/documents", "/quizzes", "/chat", "/dashboard", "/history"];
  const isInternalRoute = internalRoutes.some(
    (route) => pathname === route || pathname.startsWith(route + "/")
  );

  // Nếu chưa đăng nhập mà vào trang nội bộ -> Đẩy về /login
  if (!token && isInternalRoute) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Nếu đã đăng nhập mà quay lại các trang đăng nhập/đăng ký -> Đẩy về trang chủ "/"
  if (token && isAuthRoute) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  // Đăng ký toàn bộ danh sách các trang để Next.js chạy qua trạm kiểm soát middleware
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