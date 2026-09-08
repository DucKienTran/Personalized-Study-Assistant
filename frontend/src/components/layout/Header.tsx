"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import {
  StatsIcon,
  HomeIcon,
  LibraryIcon,
  AutoStoriesIcon,
  UserIcon,
  KeyIcon,
  LogoutIcon,
  MenuIcon, // TODO: thêm vào icons.tsx nếu chưa có (Material Symbols "menu", weight 300, fill 0)
} from "@/components/shared/icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const NAV_ITEMS = [
  {
    label: "Homepage",
    href: "/",
    icon: HomeIcon,
  },
  {
    label: "Notebooks",
    href: "/notebooks",
    icon: LibraryIcon,
  },
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: StatsIcon,
  },
];

const ADMIN_NAV_ITEM = {
  label: "Admin",
  href: "/admin",
  icon: UserIcon,
};

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { currentUser, logout } = useAuth();

  const visibleNavItems =
    currentUser?.role_name === "admin"
      ? [...NAV_ITEMS, ADMIN_NAV_ITEM]
      : NAV_ITEMS;

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  const isNavItemActive = (href: string) =>
    href === "/"
      ? pathname === "/"
      : pathname === href || pathname.startsWith(`${href}/`);

  const avatarLetter =
    (currentUser?.full_name ?? currentUser?.email)?.charAt(0).toUpperCase() ??
    "U";

  return (
    <header className="sticky top-0 z-40 h-14 w-full shrink-0 border-b border-[#ECE7DE] bg-[#FCFBF8] sm:h-14">
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between gap-2 px-3 sm:px-4">
        {/* Left */}
        <div className="flex min-w-0 items-center gap-2 sm:gap-8">
          {/* Logo */}
          <Link
            href="/"
            className="flex shrink-0 items-center gap-0"
          >
            <div className="flex h-9 w-9 items-center justify-center text-[#6F7A6E] sm:h-11 sm:w-11">
              <AutoStoriesIcon size={22} />
            </div>

            <span className="-ml-1 font-heading text-[18px] font-medium tracking-tight text-[#6F7A6E] sm:text-[20px]">
              LearningAId
            </span>
          </Link>

          {/* Navigation — desktop: hàng ngang đầy đủ label, giữ nguyên như bản gốc */}
          <nav className="hidden items-center gap-1 p-0 sm:flex">
            {visibleNavItems.map((item) => {
              const ItemIcon = item.icon;
              const isActive = isNavItemActive(item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 rounded-[12px] px-7 py-1.5 text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? "bg-[#F1ECE2] text-foreground"
                      : "bg-transparent text-muted-foreground hover:bg-[#F6F2EA] hover:text-foreground"
                  }`}
                >
                  <ItemIcon size={18} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right */}
        <div className="flex shrink-0 items-center gap-1">
          {/* Navigation — mobile: hamburger, chỉ hiện dưới sm */}
          <DropdownMenu>
            <DropdownMenuTrigger className="flex h-9 w-9 items-center justify-center rounded-[10px] text-muted-foreground outline-none hover:bg-[#F6F2EA] hover:text-foreground focus:ring-2 focus:ring-primary/30 sm:hidden">
              <MenuIcon size={20} />
            </DropdownMenuTrigger>

            <DropdownMenuContent
              align="end"
              className="w-56 rounded-[10px] border border-border p-1.5 shadow-lg sm:hidden"
            >
              {visibleNavItems.map((item) => {
                const ItemIcon = item.icon;
                const isActive = isNavItemActive(item.href);

                return (
                  <DropdownMenuItem
                    key={item.href}
                    render={<Link href={item.href} />}
                    className={`cursor-pointer rounded-lg ${
                      isActive
                        ? "bg-[#F1ECE2] text-foreground"
                        : "text-muted-foreground focus:bg-muted focus:text-foreground"
                    }`}
                  >
                    <ItemIcon
                      size={16}
                      className="mr-2"
                    />
                    {item.label}
                  </DropdownMenuItem>
                );
              })}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Avatar dropdown — giữ nguyên như cũ */}
          <DropdownMenu>
            <DropdownMenuTrigger className="rounded-[10px] outline-none focus:ring-2 focus:ring-primary/30">
              <Avatar className="h-9 w-9 border border-border bg-primary/10 text-xs font-semibold text-primary transition-opacity hover:opacity-90">
                <AvatarFallback>{avatarLetter}</AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>

            <DropdownMenuContent
              align="end"
              className="w-52 rounded-[10px] border border-border p-1.5 shadow-lg"
            >
              <div className="px-2 py-1.5 font-normal">
                <p className="text-xs text-muted-foreground">Signed in as</p>
                <p className="truncate text-sm font-semibold text-foreground">
                  {currentUser?.email}
                </p>
              </div>

              <DropdownMenuSeparator />

              <DropdownMenuItem
                render={<Link href="/library" />}
                className="cursor-pointer rounded-lg text-muted-foreground focus:bg-muted focus:text-foreground"
              >
                <LibraryIcon
                  size={16}
                  className="mr-2"
                />
                Library
              </DropdownMenuItem>

              <DropdownMenuItem
                render={<Link href="/profile" />}
                className="cursor-pointer rounded-lg text-muted-foreground focus:bg-muted focus:text-foreground"
              >
                <UserIcon
                  size={16}
                  className="mr-2"
                />
                Profile
              </DropdownMenuItem>

              <DropdownMenuItem
                render={<Link href="/change-password" />}
                className="cursor-pointer rounded-lg text-muted-foreground focus:bg-muted focus:text-foreground"
              >
                <KeyIcon
                  size={16}
                  className="mr-2"
                />
                Change password
              </DropdownMenuItem>

              <DropdownMenuSeparator />

              <DropdownMenuItem
                onClick={handleLogout}
                className="cursor-pointer rounded-lg text-destructive focus:bg-destructive/10 focus:text-destructive"
              >
                <LogoutIcon
                  size={16}
                  className="mr-2"
                />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
