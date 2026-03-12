import { METHODS } from "@/lib/constants/method-config";
import type { InstantQuoteResponse } from "@/lib/types/quote";
import { MethodCard } from "./MethodCard";

interface Props {
  quote: InstantQuoteResponse;
  selectedQuantity: number;
}

const METHOD_MAP = [
  { key: "digital" as const, configKey: "digital" as const },
  { key: "flexographic" as const, configKey: "flexographic" as const },
  { key: "international_air" as const, configKey: "internationalAir" as const },
  {
    key: "international_ocean" as const,
    configKey: "internationalOcean" as const,
  },
] as const;

export function PricingComparison({ quote, selectedQuantity }: Props) {
  const visibleMethods = METHOD_MAP.filter(({ configKey }) => {
    const config = METHODS[configKey];
    return selectedQuantity >= config.minQtyToShow;
  });

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {visibleMethods.map(({ key, configKey }) => (
        <MethodCard
          key={key}
          config={METHODS[configKey]}
          pricing={quote[key]}
          selectedQuantity={selectedQuantity}
        />
      ))}
    </div>
  );
}
