"use client";

import { useState } from "react";
import { BriefcaseBusiness } from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { PortalAccess } from "@/components/PortalAccess";
import { PendingLeadCards } from "@/components/firm/PendingLeadCards";
import { CaseWorkspace } from "@/components/firm/CaseWorkspace";
import type { CaseRecord } from "@/lib/api";

export default function FirmPage() {
  const { persona } = useAuth();
  const [acceptedCase, setAcceptedCase] = useState<CaseRecord | null>(null);
  const [caseKey, setCaseKey] = useState(0);

  if (!["ATTORNEY", "PARALEGAL"].includes(persona.role)) {
    return <PortalAccess allowed={["ATTORNEY", "PARALEGAL"]} />;
  }

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-[2rem] bg-[#173f36] p-7 text-white sm:p-10">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.18em] text-emerald-200">
              <BriefcaseBusiness size={14} /> {persona.organization}
            </p>
            <h1 className="mt-4 font-serif text-4xl sm:text-5xl">
              Your work, in good order.
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-white/65">
              Review new matters, make informed decisions, and keep every active
              case moving forward.
            </p>
          </div>
        </div>
      </section>

      <PendingLeadCards
        onAccepted={(record) => {
          setAcceptedCase(record);
          setCaseKey((value) => value + 1);
        }}
      />

      <section id="case-workspace" className="scroll-mt-28">
        <div className="mb-5">
          <p className="text-[10px] font-bold uppercase tracking-[.18em] text-forest">Matter management</p>
          <h2 className="mt-2 font-serif text-3xl text-ink">Case workspace</h2>
        </div>
        <CaseWorkspace
          key={`${persona.email}-${caseKey}`}
          initialCase={acceptedCase}
        />
      </section>
    </div>
  );
}
