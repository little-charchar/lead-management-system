"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, BriefcaseBusiness, FileText, ShieldCheck } from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { Card } from "@/components/ui";

const destinationByRole = {
  PLAINTIFF: "/plaintiff",
  ATTORNEY: "/firm",
  PARALEGAL: "/firm",
  ADMIN: "/admin",
} as const;

export default function HomePage() {
  const { persona } = useAuth();
  const router = useRouter();

  useEffect(() => {
    router.replace(destinationByRole[persona.role]);
  }, [persona.role, router]);

  return (
    <div className="space-y-7">
      <div className="rounded-[2rem] bg-[#173f36] px-7 py-10 text-white sm:px-10 sm:py-14">
        <p className="text-[10px] font-bold uppercase tracking-[.2em] text-emerald-200">
          A clearer path forward
        </p>
        <h1 className="mt-3 max-w-2xl font-serif text-4xl leading-tight sm:text-5xl">
          Every matter deserves thoughtful attention.
        </h1>
        <p className="mt-4 max-w-xl text-sm leading-6 text-white/65">
          Connect people with the legal support they need, and keep every next
          step in view.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {[
          { title: "Plaintiff portal", href: "/plaintiff", icon: FileText, text: "Share your story and follow your matter." },
          { title: "Firm workspace", href: "/firm", icon: BriefcaseBusiness, text: "Review incoming leads and manage cases." },
          { title: "Admin oversight", href: "/admin", icon: ShieldCheck, text: "Coordinate firms and inspect history." },
        ].map(({ title, href, icon: Icon, text }) => (
          <Link href={href} key={href}>
            <Card className="h-full p-5 transition hover:-translate-y-0.5 hover:shadow-md">
              <div className="flex items-center justify-between">
                <span className="rounded-xl bg-mint p-2.5 text-forest"><Icon size={18} /></span>
                <ArrowRight size={16} className="text-muted" />
              </div>
              <h2 className="mt-5 font-serif text-xl text-ink">{title}</h2>
              <p className="mt-2 text-sm text-muted">{text}</p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
