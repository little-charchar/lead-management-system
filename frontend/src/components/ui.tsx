import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

export function Button({
  children,
  className = "",
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
}) {
  const variants = {
    primary: "bg-forest text-white hover:bg-[#17463c]",
    secondary: "border border-line bg-white text-ink hover:bg-canvas",
    danger: "bg-rose text-white hover:bg-[#913e3e]",
    ghost: "text-muted hover:bg-canvas hover:text-ink",
  };
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Card({
  children,
  className = "",
  ...props
}: HTMLAttributes<HTMLElement> & {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-2xl border border-line bg-white shadow-soft ${className}`}
      {...props}
    >
      {children}
    </section>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && (
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[.18em] text-forest">
            {eyebrow}
          </p>
        )}
        <h2 className="font-serif text-3xl tracking-tight text-ink">{title}</h2>
        {description && <p className="mt-2 text-sm text-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    UNASSIGNED: "bg-amber-50 text-amber-700",
    PENDING_REVIEW: "bg-blue-50 text-blue-700",
    ACCEPTED: "bg-mint text-forest",
    DECLINED: "bg-rose-50 text-rose",
    INTAKE: "bg-blue-50 text-blue-700",
    INVESTIGATION: "bg-amber-50 text-amber-700",
    DISCOVERY: "bg-violet-50 text-violet-700",
    SETTLED: "bg-mint text-forest",
    CLOSED: "bg-slate-100 text-slate-600",
  };
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[.08em] ${styles[status] ?? "bg-slate-100 text-slate-600"}`}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}

export function InlineMessage({
  children,
  tone = "info",
}: {
  children: ReactNode;
  tone?: "info" | "success" | "error";
}) {
  const tones = {
    info: "border-blue-100 bg-blue-50 text-blue-800",
    success: "border-emerald-100 bg-emerald-50 text-emerald-800",
    error: "border-rose-100 bg-rose-50 text-rose-800",
  };
  return (
    <div className={`rounded-xl border px-4 py-3 text-sm ${tones[tone]}`}>
      {children}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
}: {
  icon: ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      <div className="mb-4 rounded-2xl bg-canvas p-4 text-forest">{icon}</div>
      <h3 className="font-semibold text-ink">{title}</h3>
      <p className="mt-2 max-w-md text-sm leading-6 text-muted">{description}</p>
    </div>
  );
}
