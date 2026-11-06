"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ArrowUpRight,
  Compass,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { useAuth } from "@/context/AuthContext";
import type { UserRole } from "@/lib/api";

const navByRole: Record<UserRole, { href: string; label: string; icon: typeof Compass }[]> = {
  PLAINTIFF: [],
  ATTORNEY: [],
  PARALEGAL: [],
  ADMIN: [],
};

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { persona } = useAuth();
  const nav = navByRole[persona.role];
  const [hash, setHash] = useState("");

  useEffect(() => {
    const updateHash = () => setHash(window.location.hash);
    updateHash();
    window.addEventListener("hashchange", updateHash);
    return () => window.removeEventListener("hashchange", updateHash);
  }, [pathname]);

  return (
    <div className="min-h-screen">
      <div className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between px-4 py-4 sm:px-6 lg:px-10">
          <Link href="/" className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-2xl bg-forest text-white">
              <span className="font-serif text-lg">L</span>
            </div>
            <div>
              <p className="font-serif text-lg font-bold tracking-tight text-ink">
                Lexwell
              </p>
              <p className="text-[10px] font-semibold uppercase tracking-[.16em] text-muted">
                Legal matters, thoughtfully managed
              </p>
            </div>
          </Link>
          <div className="hidden items-center gap-2 rounded-full bg-canvas px-3 py-2 text-xs text-muted md:flex">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            API connected at localhost:8000
          </div>
        </div>
      </div>

      <div className="mx-auto grid max-w-[1500px] gap-8 px-4 py-7 sm:px-6 lg:grid-cols-[210px_minmax(0,1fr)] lg:px-10 lg:py-10">
        <aside className="lg:sticky lg:top-32 lg:h-fit">
          <div className="mb-5 rounded-2xl border border-line bg-white p-4">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-full bg-mint text-sm font-bold text-forest">
                {persona.initials}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-ink">{persona.name}</p>
                <p className="truncate text-[11px] text-muted">{persona.organization}</p>
              </div>
            </div>
          </div>
          {nav.length > 0 && (
            <nav className="flex gap-2 overflow-x-auto lg:flex-col">
              {nav.map(({ href, label, icon: Icon }) => {
                const isRoute = pathname === href.split("#")[0];
                const hasHash = href.includes("#");
                const active = hasHash
                  ? isRoute && hash === `#${href.split("#")[1]}`
                  : isRoute &&
                    !nav.some(
                      (item) =>
                        item.href.includes("#") &&
                        item.href.split("#")[0] === pathname &&
                        hash === `#${item.href.split("#")[1]}`,
                    );
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`flex shrink-0 items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition ${
                      active
                        ? "bg-forest text-white shadow-sm"
                        : "text-muted hover:bg-white hover:text-ink"
                    }`}
                  >
                    <Icon size={17} />
                    {label}
                    {active && <ArrowUpRight className="ml-auto" size={14} />}
                  </Link>
                );
              })}
            </nav>
          )}
        </aside>
        <main key={persona.email} className="min-w-0">{children}</main>
      </div>
      <footer className="border-t border-line bg-white/70">
        <div className="mx-auto flex max-w-[1500px] justify-between px-4 py-5 text-[11px] text-muted sm:px-6 lg:px-10">
          <span>Lexwell · Secure matter management</span>
          <span>Demo environment</span>
        </div>
      </footer>
    </div>
  );
}
