"use client";

import {
  User,
  Building2,
  Mail,
  Phone,
  DollarSign,
  Calendar,
  FileText,
  Download,
  Package,
  AlertCircle,
} from "lucide-react";
import type {
  LeadDetailResponse,
  QuoteDetail,
  MethodPricingData,
  FileDetail,
} from "@/lib/types/lead-detail";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 4,
    maximumFractionDigits: 4,
  }).format(value);
}

function formatQty(qty: number): string {
  return qty >= 1000 ? `${(qty / 1000).toFixed(0)}K` : qty.toLocaleString();
}

function specSummary(q: QuoteDetail): string {
  const s = q.specifications;
  const dims = s.gusset > 0
    ? `${s.width}" x ${s.height}" x ${s.gusset}"`
    : `${s.width}" x ${s.height}"`;
  const parts = [dims, s.seal_type, s.substrate];
  if (s.finish !== "None" && s.finish !== "Matte") parts.push(s.finish);
  if (s.zipper !== "None") parts.push(`${s.zipper} Zipper`);
  if (s.tear_notch !== "None") parts.push("Tear Notch");
  if (s.hole_punch !== "None") parts.push(s.hole_punch);
  if (s.corners === "Rounded") parts.push("Rounded Corners");
  return parts.join("  ·  ");
}

function fileIcon(type: string): string {
  if (type.startsWith("image/")) return "image";
  if (type === "application/pdf") return "pdf";
  return "file";
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <Icon size={16} className="mt-0.5 shrink-0 text-calyx-blue" />
      <div>
        <p className="text-xs text-gray-60">{label}</p>
        <p className="text-sm font-medium text-gray-90">{value || "—"}</p>
      </div>
    </div>
  );
}

function MethodPricingTable({
  label,
  data,
}: {
  label: string;
  data: MethodPricingData;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h5 className="text-sm font-semibold text-gray-90">{label}</h5>
        <span className="text-xs text-gray-60">{data.lead_time}</span>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-10 text-left text-xs text-gray-60">
            <th className="pb-2 font-medium">Qty</th>
            <th className="pb-2 font-medium text-right">Unit Price</th>
            <th className="pb-2 font-medium text-right">Total</th>
          </tr>
        </thead>
        <tbody>
          {data.tiers.map((t) => (
            <tr key={t.quantity} className="border-b border-gray-5">
              <td className="py-1.5">{formatQty(t.quantity)}</td>
              <td className="py-1.5 text-right font-medium">
                {formatCurrency(t.unit_price)}
              </td>
              <td className="py-1.5 text-right text-gray-60">
                ${t.total_price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.notes.length > 0 && (
        <ul className="mt-1.5 space-y-0.5">
          {data.notes.map((n, i) => (
            <li key={i} className="text-xs text-gray-60">
              {n}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function QuoteCard({ quote }: { quote: QuoteDetail }) {
  const methods: { key: string; label: string; data: MethodPricingData | null }[] = [
    { key: "digital", label: "Digital", data: quote.pricing_digital },
    { key: "flexo", label: "Flexographic", data: quote.pricing_flexo },
    { key: "intl_air", label: "Intl (Air)", data: quote.pricing_intl_air },
    { key: "intl_ocean", label: "Intl (Ocean)", data: quote.pricing_intl_ocean },
  ];

  const activeMethods = methods.filter((m) => m.data);

  return (
    <div className="rounded-xl border border-gray-10 bg-white overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-10 bg-gray-5 px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Package size={16} className="text-calyx-blue" />
          <span className="text-sm font-semibold text-gray-90">
            {specSummary(quote)}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {quote.requested_manager && (
            <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-[10px] font-semibold text-amber-700">
              Manager Requested
            </span>
          )}
          {quote.margin_applied != null && (
            <span className="text-xs text-gray-60">
              Margin: {(quote.margin_applied * 100).toFixed(0)}%
            </span>
          )}
          <span className="text-xs text-gray-60">{formatDate(quote.created_at)}</span>
        </div>
      </div>

      {/* Pricing methods grid */}
      {activeMethods.length > 0 ? (
        <div className={`grid gap-6 p-5 ${activeMethods.length >= 3 ? "md:grid-cols-2 xl:grid-cols-4" : activeMethods.length === 2 ? "md:grid-cols-2" : ""}`}>
          {activeMethods.map((m) => (
            <MethodPricingTable key={m.key} label={m.label} data={m.data!} />
          ))}
        </div>
      ) : (
        <div className="flex items-center gap-2 p-5 text-sm text-gray-60">
          <AlertCircle size={14} />
          <span>No pricing data available for this configuration.</span>
        </div>
      )}
    </div>
  );
}

function FileCard({ file }: { file: FileDetail }) {
  const icon = fileIcon(file.file_type);

  return (
    <a
      href={file.public_url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-3 rounded-lg border border-gray-10 bg-white px-4 py-3 hover:border-calyx-blue hover:shadow-sm transition-all"
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-powder-blue">
        {icon === "image" ? (
          <FileText size={18} className="text-calyx-blue" />
        ) : icon === "pdf" ? (
          <FileText size={18} className="text-red-500" />
        ) : (
          <FileText size={18} className="text-gray-60" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-gray-90">
          {file.file_name}
        </p>
        <p className="text-xs text-gray-60">
          {formatFileSize(file.file_size)} · {formatDate(file.created_at)}
        </p>
      </div>
      <Download size={16} className="shrink-0 text-gray-40" />
    </a>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function LeadDetailView({ data }: { data: LeadDetailResponse }) {
  const { lead, quotes, files } = data;

  return (
    <div className="min-h-[100dvh] bg-gray-5">
      {/* Top bar */}
      <header className="border-b border-gray-10 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-4">
          <div className="h-8 w-8 rounded-lg bg-calyx-blue flex items-center justify-center">
            <span className="text-sm font-bold text-white">C</span>
          </div>
          <span className="text-sm font-semibold text-gray-90">
            Calyx Containers — Lead Detail
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 space-y-8">
        {/* Customer Info */}
        <section className="rounded-xl border border-gray-10 bg-white p-6">
          <h2 className="text-lg font-semibold text-gray-90 mb-4">
            Customer Information
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <InfoRow icon={User} label="Full Name" value={lead.full_name} />
            <InfoRow icon={Building2} label="Business" value={lead.business_name} />
            <InfoRow icon={Mail} label="Email" value={lead.email} />
            <InfoRow icon={Phone} label="Phone" value={lead.phone} />
            <InfoRow icon={DollarSign} label="Annual Spend" value={lead.annual_spend} />
            <InfoRow icon={Calendar} label="Submitted" value={formatDate(lead.created_at)} />
          </div>
        </section>

        {/* Uploaded Files */}
        {files.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-gray-90 mb-3">
              Uploaded Files ({files.length})
            </h2>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {files.map((f) => (
                <FileCard key={f.id} file={f} />
              ))}
            </div>
          </section>
        )}

        {/* Quotes */}
        <section>
          <h2 className="text-lg font-semibold text-gray-90 mb-3">
            Bag Configurations & Pricing ({quotes.length})
          </h2>
          {quotes.length === 0 ? (
            <p className="text-sm text-gray-60">
              No quotes generated yet.
            </p>
          ) : (
            <div className="space-y-4">
              {quotes.map((q) => (
                <QuoteCard key={q.id} quote={q} />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
