"use client";

import { METHODS } from "@/lib/constants/method-config";
import type { InstantQuoteResponse, TierPrice } from "@/lib/types/quote";

interface Props {
  quote: InstantQuoteResponse;
  tiers: number[];
  activeTier: number;
}

const METHOD_MAP = [
  {
    key: "digital" as const,
    configKey: "digital" as const,
    quoteKey: "digital" as const,
    minQtyForCell: 0,
  },
  {
    key: "flexographic",
    configKey: "flexographic" as const,
    quoteKey: "flexographic" as const,
    minQtyForCell: 50_000,
  },
  {
    key: "internationalAir",
    configKey: "internationalAir" as const,
    quoteKey: "international_air" as const,
    minQtyForCell: 25_000,
  },
  {
    key: "internationalOcean",
    configKey: "internationalOcean" as const,
    quoteKey: "international_ocean" as const,
    minQtyForCell: 25_000,
  },
] as const;

const numberFmt = new Intl.NumberFormat("en-US");

const currencyUnit = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});

const currencyTotal = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

export default function PricingGrid({ quote, tiers, activeTier }: Props) {
  const sortedTiers = [...tiers].sort((a, b) => a - b);

  // A method column is visible if ANY tier meets its cell threshold
  const visibleMethods = METHOD_MAP.filter(({ minQtyForCell }) => {
    return sortedTiers.some((t) => t >= minQtyForCell);
  });

  if (visibleMethods.length === 0) {
    return (
      <div className="rounded-xl border border-gray-10 bg-white px-6 py-10 text-center text-sm text-gray-60">
        Select higher quantities to see pricing for more production methods.
      </div>
    );
  }

  // Build a lookup: for each visible method, map quantity -> TierPrice
  const pricingLookup = new Map<string, Map<number, TierPrice>>();

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

  // Determine which visible method has the lowest unit price for the active tier
  let bestValueMethodKey: string | null = null;
  let bestValuePrice: number | null = null;
  for (const method of visibleMethods) {
    if (activeTier < method.minQtyForCell) continue;
    const tierMap = pricingLookup.get(method.key);
    const tier = tierMap?.get(activeTier);
    if (tier) {
      if (bestValuePrice === null || tier.unit_price < bestValuePrice) {
        bestValuePrice = tier.unit_price;
        bestValueMethodKey = method.key;
      }
    }
  }

  // Collect all notes across visible methods
  const allNotes: { label: string; note: string }[] = [];
  for (const method of visibleMethods) {
    const config = METHODS[method.configKey];
    for (const note of config.notes) {
      allNotes.push({ label: config.label, note });
    }
  }

  // Quantity column gets a small fixed width, methods split the rest evenly
  const methodColWidth = `${((100 - 12) / visibleMethods.length).toFixed(2)}%`;

  // Minimum width ensures columns aren't crushed on mobile — enables horizontal scroll
  const minTableWidth = 80 + visibleMethods.length * 160;

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-10 -mx-4 sm:mx-0">
      <table
        className="w-full border-collapse table-fixed"
        style={{ minWidth: `${minTableWidth}px` }}
      >
        <colgroup>
          <col style={{ width: "12%" }} />
          {visibleMethods.map(({ key }) => (
            <col key={key} style={{ width: methodColWidth }} />
          ))}
        </colgroup>
        <thead>
          <tr>
            <th className="bg-gray-5 px-4 py-3 text-left text-sm font-semibold text-gray-90">
              Quantity
            </th>
            {visibleMethods.map(({ key, configKey, quoteKey }) => {
              const config = METHODS[configKey];
              const methodPricing = quote[quoteKey];
              const hasBadge = bestValueMethodKey === key || configKey === "digital";
              return (
                <th
                  key={key}
                  className="bg-gray-5 px-3 py-3 text-center text-sm font-semibold text-gray-90 align-top"
                >
                  <div className="font-bold">{config.label}</div>
                  <div className="mt-0.5 text-xs font-normal text-gray-60">{config.tagline}</div>
                  <div className="mt-1 text-xs font-normal text-gray-60">
                    {config.leadTime}
                  </div>
                  <div className="mt-1 flex justify-center gap-1 flex-wrap" style={{ minHeight: "1.25rem" }}>
                    {bestValueMethodKey === key && (
                      <span className="inline-block bg-green-100 text-green-700 text-[10px] font-semibold px-2 py-0.5 rounded-full">Best Value</span>
                    )}
                    {configKey === "digital" && (
                      <span className="inline-block bg-blue-100 text-blue-700 text-[10px] font-semibold px-2 py-0.5 rounded-full">Fastest</span>
                    )}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sortedTiers.map((qty) => {
            // Find the best (lowest) unit price for this tier across visible methods
            let bestUnitPrice: number | null = null;
            for (const method of visibleMethods) {
              if (qty < method.minQtyForCell) continue;
              const tierMap = pricingLookup.get(method.key);
              const tier = tierMap?.get(qty);
              if (tier) {
                if (bestUnitPrice === null || tier.unit_price < bestUnitPrice) {
                  bestUnitPrice = tier.unit_price;
                }
              }
            }

            return (
              <tr key={qty}>
                <td className="border-t border-gray-10 px-4 py-3 font-medium text-gray-90">
                  {numberFmt.format(qty)}
                </td>
                {visibleMethods.map(({ key, minQtyForCell }) => {
                  // Blank if below this method's threshold
                  if (qty < minQtyForCell) {
                    return (
                      <td
                        key={key}
                        className="border-t border-gray-10 px-3 py-3 text-center text-gray-30"
                      >
                        &mdash;
                      </td>
                    );
                  }

                  const tierMap = pricingLookup.get(key);
                  const tier = tierMap?.get(qty);

                  if (!tier) {
                    return (
                      <td
                        key={key}
                        className="border-t border-gray-10 px-3 py-3 text-center text-gray-30"
                      >
                        &mdash;
                      </td>
                    );
                  }

                  const isBest =
                    bestUnitPrice !== null &&
                    tier.unit_price === bestUnitPrice;

                  return (
                    <td
                      key={key}
                      className={`border-t border-gray-10 px-3 py-3 text-center${
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
                        {currencyUnit.format(tier.unit_price)}
                      </div>
                      <div className="mt-0.5 text-xs text-gray-60">
                        /unit
                      </div>
                      <div className="mt-0.5 text-xs text-gray-60">
                        {currencyTotal.format(tier.total_price)} total
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
