"use client";

import { useState } from "react";
import { ArrowDownRight, HeartHandshake } from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { PortalAccess } from "@/components/PortalAccess";
import { IntakeForm } from "@/components/plaintiff/IntakeForm";
import { MyMatters } from "@/components/plaintiff/MyMatters";
import type { LeadStatus } from "@/lib/api";

export default function PlaintiffPage() {
  const { persona } = useAuth();
  const [refreshKey, setRefreshKey] = useState(0);
  const [lastLeadStatus, setLastLeadStatus] = useState<LeadStatus | null>(null);
  const [activeTab, setActiveTab] = useState<"dashboard" | "submit">("dashboard");

  if (persona.role !== "PLAINTIFF") {
    return <PortalAccess allowed={["PLAINTIFF"]} />;
  }

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-[2rem] bg-[#e7f0e9] p-7 sm:p-10">
        <div className="absolute -right-10 -top-14 h-56 w-56 rounded-full border-[34px] border-white/40" />
        <div className="relative max-w-2xl">
          <p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.18em] text-forest">
            <HeartHandshake size={14} /> A more considered legal journey
          </p>
          <h1 className="mt-4 font-serif text-4xl leading-tight text-ink sm:text-5xl">
            Good morning, {persona.name.split(" ")[0]}.
          </h1>
          <p className="mt-4 max-w-xl text-sm leading-6 text-muted">
            Share what you&apos;re going through. Your lead will be matched using
            its category and region, and you can follow any accepted case here.
          </p>
          <button
            type="button"
            onClick={() => setActiveTab("submit")}
            className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-forest"
          >
            Start a new intake <ArrowDownRight size={15} />
          </button>
        </div>
      </section>

      <nav
        aria-label="Plaintiff portal"
        className="flex border-b border-line"
      >
        {([
          ["dashboard", "Dashboard"],
          ["submit", "Submit a lead"],
        ] as const).map(([tab, label]) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            aria-current={activeTab === tab ? "page" : undefined}
            className={`-mb-px border-b-2 px-5 py-3 text-sm font-semibold transition ${
              activeTab === tab
                ? "border-forest text-forest"
                : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </nav>

      {activeTab === "dashboard" ? (
        <section>
          {lastLeadStatus && (
            <div className="mb-5 rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              Lead submitted · {lastLeadStatus.replaceAll("_", " ")}
            </div>
          )}
          <div className="mb-5">
            <p className="text-[10px] font-bold uppercase tracking-[.18em] text-forest">
              Your dashboard
            </p>
            <h2 className="mt-2 font-serif text-3xl text-ink">My leads &amp; cases</h2>
          </div>
          <MyMatters key={persona.email} refreshKey={refreshKey} />
        </section>
      ) : (
        <section>
          <div className="mb-5">
            <p className="text-[10px] font-bold uppercase tracking-[.18em] text-forest">
              A first step
            </p>
            <h2 className="mt-2 font-serif text-3xl text-ink">Submit a new lead</h2>
          </div>
          <IntakeForm
            key={persona.email}
            onCreated={(lead) => {
              setLastLeadStatus(lead.status);
              setRefreshKey((value) => value + 1);
              setActiveTab("dashboard");
            }}
          />
        </section>
      )}
    </div>
  );
}
