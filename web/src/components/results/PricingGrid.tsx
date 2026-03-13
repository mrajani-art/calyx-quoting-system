"use client";

import { METHODS } from "@/lib/constants/method-config";
import type { InstantQuoteResponse, TierPrice } from "@/lib/types/quote";

interface Props {
  quote: InstantQuoteResponse;
  tiers: number[];
}

const METHOD_MAP = [
  {
    key: "digital" as const,
    configKey: "digital" as const,
    quoteKey: "digital" as const,
  },
  {
    key: "flexographic",
    configKey: "flexographic" as const,
    quoteKey: "flexographic" as const,
  },
  {
    key: "internationalAir",
    configKey: "internationalAir" as const,
    quoteKey: "international_air" as const,
  },
  {
    key: "internationalOcean",
    configKey: "internationalOcean" as const,
    quoteKey: "international_ocean" as const,
  },
] as const;

const numberFmt = new Intl.NumberFormat("en-US");

const currencyTotal = new Intl.NumberFormat("en-US", {
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

export default function PricingGrid({ quote, tiers }: Props) {
  const sortedTiers = [...tiers].sort((a, b) => a - b);

  // A method column is visible if ANY tier meets its minQtyToShow
  const visibleMethods = METHOD_MAP.filter(({ configKey }) => {
    const config = METHODS[configKey];
    return sortedTiers.some((t) => t >= config.minQtyToShow);
  });

  if (visibleMethods.length === 0) {
    return (
      <div className="rounded-xl border border-gray-10 bg-white px-6 py-10 text-center text-sm text-gray-60">
        Select higher quantities to see pricing for more production methods.
      </div>
    );
  }

  // Build a lookup: for each visible method, map quantity -> TierPrice
  const pricingLookup = new Map<
    string,
    Map<number, TierPrice>
  >();

  for (const method of visibleMethods) {
    const methodPricing = quote[method.quoteKey];
    const tierMap = new Map<number, TierPrice>();
    if (methodPricing) {
      for (const tier of methodPricing.tiers) {
        tierMap.set(tier.quantity, tier);
      }
    }
    pricingLookup.set(method.key, tierMap);
  }

  // Collect all notes across visible methods
  const allNotes: { label: string; note: string }[] = [];
  for (const method of visibleMethods) {
    const config = METHODS[method.configKey];
    for (const note of config.notes) {
      allNotes.push({ label: config.label, note });
    }
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-10">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th className="bg-gray-5 px-4 py-3 text-left text-sm font-semibold text-gray-90">
              Quantity
            </th>
            {visibleMethods.map(({ key, configKey, quoteKey }) => {
              const config = METHODS[configKey];
              const methodPricing = quote[quoteKey];
              return (
                <th
                  key={key}
                  className="bg-gray-5 px-4 py-3 text-left text-sm font-semibold text-gray-90"
                >
                  <div className="font-bold">{config.label}</div>
                  <div className="mt-0.5 text-xs font-normal text-gray-60">
                    {methodPricing?.lead_time ?? config.leadTime}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sortedTiers.map((qty) => {
            // Find the best (lowest) total price for this tier across all methods
            let bestTotal: number | null = null;
            for (const method of visibleMethods) {
              const tierMap = pricingLookup.get(method.key);
              const tier = tierMap?.get(qty);
              if (tier) {
                if (bestTotal === null || tier.total_price < bestTotal) {
                  bestTotal = tier.total_price;
                }
              }
            }

            return (
              <tr key={qty}>
                <td className="border-t border-gray-10 px-4 py-3 font-medium text-gray-90">
                  {numberFmt.format(qty)}
                </td>
                {visibleMethods.map(({ key }) => {
                  const tierMap = pricingLookup.get(key);
                  const tier = tierMap?.get(qty);
                  const isBest =
                    tier !== undefined &&
                    bestTotal !== null &&
                    tier.total_price === bestTotal;

                  if (!tier) {
                    return (
                      <td
                        key={key}
                        className="border-t border-gray-10 px-4 py-3 text-gray-40"
                      >
                        &mdash;
                      </td>
                    );
                  }

                  return (
                    <td
                      key={key}
                      className={`border-t border-gray-10 px-4 py-3${
                        isBest ? " bg-green-50" : ""
                      }`}
                    >
                      <div
                        className={
                          isBest
                            ? "text-lg font-semibold text-green-700"
                            : "text-lg font-bold text-gray-90"
                        }
                      >
                        {currencyTotal.format(tier.total_price)}
                      </div>
                      <div className="mt-0.5 text-xs text-gray-60">
                        {currencyUnit.format(tier.unit_price)} / unit
                      </div>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>

      {allNotes.length > 0 && (
        <div className="border-t border-gray-10 bg-gray-5 px-4 py-3">
          {allNotes.map(({ label, note }, i) => (
            <p key={i} className="text-xs text-gray-60">
              {label}: {note}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
