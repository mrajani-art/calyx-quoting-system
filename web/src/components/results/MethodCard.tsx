import { Clock } from "lucide-react";
import type { MethodPricing } from "@/lib/types/quote";
import type { MethodConfig } from "@/lib/constants/method-config";

interface Props {
  config: MethodConfig;
  pricing: MethodPricing | null;
  selectedQuantity: number;
}

const currencyFull = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const currencyUnit = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 4,
  maximumFractionDigits: 4,
});

const numberFmt = new Intl.NumberFormat("en-US");

export function MethodCard({ config, pricing, selectedQuantity }: Props) {
  const matchedTier = pricing?.tiers.find(
    (t) => t.quantity === selectedQuantity,
  );

  return (
    <div className="flex flex-col rounded-xl border border-gray-10 bg-white p-5 shadow-sm">
      {/* Header */}
      <h3 className="text-lg font-bold text-calyx-blue">{config.label}</h3>
      <p className="mt-1 text-sm italic text-gray-60">{config.tagline}</p>

      {/* Lead time */}
      <div className="mt-3 flex items-center gap-1.5 text-sm text-gray-60">
        <Clock size={14} className="shrink-0" />
        <span>{config.leadTime}</span>
      </div>

      {/* Price section */}
      <div className="mt-5 flex-1">
        {pricing && matchedTier ? (
          <div>
            <p className="text-2xl font-bold text-gray-90">
              {currencyFull.format(matchedTier.total_price)}
            </p>
            <p className="mt-1 text-sm text-gray-60">
              {currencyUnit.format(matchedTier.unit_price)} / unit at{" "}
              {numberFmt.format(matchedTier.quantity)}
            </p>
          </div>
        ) : (
          <p className="text-sm text-gray-60">
            Not available at this quantity
          </p>
        )}
      </div>

      {/* Notes */}
      {config.notes.length > 0 && (
        <ul className="mt-4 space-y-1 border-t border-gray-10 pt-3">
          {config.notes.map((note) => (
            <li key={note} className="text-xs text-gray-60">
              {note}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
