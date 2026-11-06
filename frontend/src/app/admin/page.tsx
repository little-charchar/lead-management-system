"use client";

import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  Activity,
  Building2,
  RefreshCw,
  ShieldCheck,
  UsersRound,
} from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { PortalAccess } from "@/components/PortalAccess";
import { GlobalDirectory } from "@/components/admin/GlobalDirectory";
import {
  CaseReassignmentDialog,
  ReassignmentDialog,
} from "@/components/admin/ReassignmentDialog";
import { AuditInspector } from "@/components/admin/AuditInspector";
import { Button, Card, InlineMessage } from "@/components/ui";
import { api, type ApiError, type CaseRecord, type LawFirm, type Lead } from "@/lib/api";

export default function AdminPage() {
  const { persona } = useAuth();
  const [firms, setFirms] = useState<LawFirm[]>([]);
  const [firmError, setFirmError] = useState("");
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [selectedCase, setSelectedCase] = useState<CaseRecord | null>(null);
  const [inspectedLead, setInspectedLead] = useState<Lead | null>(null);
  const [directoryRefresh, setDirectoryRefresh] = useState(0);
  const [auditEntity, setAuditEntity] = useState<{
    type: "LEAD" | "CASE";
    id: number;
  } | null>(null);
  const [auditCount, setAuditCount] = useState(0);

  const loadFirms = useCallback(async () => {
    setFirmError("");
    try {
      setFirms(await api.fetchFirms());
    } catch (reason) {
      setFirmError((reason as ApiError).message ?? "Firm directory unavailable.");
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadFirms();
      api
        .fetchAuditLogs()
        .then((logs) => setAuditCount(logs.length))
        .catch(() => setAuditCount(0));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [persona.email, loadFirms]);

  if (persona.role !== "ADMIN") {
    return <PortalAccess allowed={["ADMIN"]} />;
  }

  return (
    <div className="space-y-8">
      <section className="rounded-[2rem] bg-[#192f34] p-7 text-white sm:p-10">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.18em] text-cyan-200">
              <ShieldCheck size={14} /> System administration
            </p>
            <h1 className="mt-4 font-serif text-4xl sm:text-5xl">
              A clearer view across every firm.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-white/60">
              Coordinate assignments, inspect immutable history, and make sure
              every matter has a responsible next step.
            </p>
          </div>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              void loadFirms();
              api
                .fetchAuditLogs()
                .then((logs) => setAuditCount(logs.length))
                .catch(() => undefined);
            }}
          >
            <RefreshCw size={15} /> Refresh overview
          </Button>
        </div>
      </section>

      {firmError && <InlineMessage tone="error">{firmError}</InlineMessage>}
      <div className="grid gap-4 sm:grid-cols-3">
        <SummaryCard icon={<Building2 size={18} />} label="Participating firms" value={firms.length} />
        <SummaryCard icon={<Activity size={18} />} label="Recent audit events" value={auditCount} />
        <SummaryCard icon={<UsersRound size={18} />} label="Oversight" value="Global" />
      </div>

      <GlobalDirectory
        refreshKey={directoryRefresh}
        onInspect={(entity, lead) => {
          setAuditEntity(entity);
          setInspectedLead(lead ?? null);
        }}
        onReassignLead={(lead, availableFirms) => {
          setFirms(availableFirms);
          setSelectedLead(lead);
        }}
        onReassignCase={(record, availableFirms) => {
          setFirms(availableFirms);
          setSelectedCase(record);
        }}
      />

      <ReassignmentDialog
        key={selectedLead?.id ?? "no-lead"}
        lead={selectedLead}
        firms={firms}
        onClose={() => setSelectedLead(null)}
        onComplete={() => {
          setSelectedLead(null);
          setDirectoryRefresh((value) => value + 1);
        }}
      />
      <CaseReassignmentDialog
        key={selectedCase?.id ?? "no-case"}
        caseRecord={selectedCase}
        firms={firms}
        onClose={() => setSelectedCase(null)}
        onComplete={() => {
          setSelectedCase(null);
          setDirectoryRefresh((value) => value + 1);
        }}
      />
      <AuditInspector
        key={auditEntity ? `${auditEntity.type}-${auditEntity.id}` : "closed"}
        entity={auditEntity}
        leadRecord={inspectedLead}
        onClose={() => {
          setAuditEntity(null);
          setInspectedLead(null);
        }}
      />
    </div>
  );
}

function SummaryCard({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: number | string;
}) {
  return (
    <Card className="flex items-center gap-4 p-5">
      <div className="rounded-xl bg-mint p-3 text-forest">{icon}</div>
      <div>
        <p className="text-2xl font-semibold text-ink">{value}</p>
        <p className="text-xs text-muted">{label}</p>
      </div>
    </Card>
  );
}
