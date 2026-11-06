"use client";

import Link from "next/link";
import { ArrowRight, ShieldAlert } from "lucide-react";

import { useAuth } from "@/context/AuthContext";

const portalByRole = {
  PLAINTIFF: { href: "/plaintiff", label: "Plaintiff portal" },
  ATTORNEY: { href: "/firm", label: "Firm workspace" },
  PARALEGAL: { href: "/firm", label: "Firm workspace" },
  ADMIN: { href: "/admin", label: "Admin oversight" },
};

export function PortalAccess({ allowed }: { allowed: readonly string[] }) {
  const { persona } = useAuth();
  if (allowed.includes(persona.role)) return null;
  const destination = portalByRole[persona.role];
  return (
    <div className="rounded-3xl border border-amber-100 bg-[#fffaf0] p-8 sm:p-12">
      <div className="mx-auto max-w-lg text-center">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[#fff0d9] text-amber">
          <ShieldAlert size={25} />
        </div>
        <p className="mt-5 text-[10px] font-bold uppercase tracking-[.18em] text-amber">
          Persona changed
        </p>
        <h1 className="mt-2 font-serif text-3xl text-ink">
          This space is for another role
        </h1>
        <p className="mt-3 text-sm leading-6 text-muted">
          You are currently signed in as {persona.name}. Continue to the workspace
          for your selected persona.
        </p>
        <Link
          href={destination.href}
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-forest px-5 py-3 text-sm font-semibold text-white hover:bg-[#17463c]"
        >
          Open {destination.label}
          <ArrowRight size={16} />
        </Link>
      </div>
    </div>
  );
}
