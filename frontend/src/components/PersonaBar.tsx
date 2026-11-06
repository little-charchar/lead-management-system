"use client";

import { Check, Shield, Sparkles } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";

import { PERSONAS, useAuth } from "@/context/AuthContext";

const workspaceByRole = {
  PLAINTIFF: "/plaintiff",
  ATTORNEY: "/firm",
  PARALEGAL: "/firm",
  ADMIN: "/admin",
} as const;

const roleLabel = {
  PLAINTIFF: "Plaintiff portal",
  ATTORNEY: "Firm workspace",
  PARALEGAL: "Firm workspace",
  ADMIN: "System oversight",
};

export function PersonaBar() {
  const { persona, setPersonaEmail } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  function switchPersona(email: string) {
    const selected = PERSONAS.find((item) => item.email === email);
    if (!selected || selected.email === persona.email) return;

    setPersonaEmail(selected.email);
    const workspace = workspaceByRole[selected.role];
    if (pathname !== workspace) {
      router.replace(workspace);
    }
  }

  return (
    <header className="sticky top-0 z-50 border-b border-[#295c50] bg-[#153f36] text-white shadow-[0_8px_24px_rgba(12,40,33,.18)]">
      <div className="mx-auto flex max-w-[1500px] flex-col gap-3 px-4 py-3 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-10">
        <div className="flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-white/10">
            <Shield size={18} />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[.2em] text-white/55">
              Demonstration identity
            </p>
            <p className="text-sm font-semibold">
              Switch persona <span className="text-white/40">·</span>{" "}
              <span className="text-emerald-200">{roleLabel[persona.role]}</span>
            </p>
          </div>
        </div>

        <nav
          aria-label="Choose demo persona"
          className="flex gap-2 overflow-x-auto pb-1 lg:pb-0"
        >
          {PERSONAS.map((item) => {
            const active = item.email === persona.email;
            return (
              <button
                key={item.email}
                type="button"
                onClick={() => switchPersona(item.email)}
                aria-pressed={active}
                className={`flex shrink-0 items-center gap-2 rounded-xl border px-3 py-2 text-left transition ${
                  active
                    ? "border-emerald-200/50 bg-emerald-100 text-[#173c33]"
                    : "border-white/10 bg-white/5 text-white/75 hover:bg-white/10 hover:text-white"
                }`}
              >
                <span
                  className={`grid h-7 w-7 place-items-center rounded-lg text-[10px] font-bold ${active ? "bg-[#c6e5d7] text-forest" : "bg-white/10 text-white"}`}
                >
                  {active ? <Check size={14} /> : item.initials}
                </span>
                <span className="pr-1">
                  <span className="block text-xs font-semibold">{item.name}</span>
                  <span
                    className={`hidden text-[10px] sm:block ${active ? "text-forest/70" : "text-white/45"}`}
                  >
                    {item.organization}
                  </span>
                </span>
              </button>
            );
          })}
        </nav>

        <div className="hidden items-center gap-2 text-[11px] text-white/45 xl:flex">
          <Sparkles size={13} />
          Demo mode
        </div>
      </div>
    </header>
  );
}
