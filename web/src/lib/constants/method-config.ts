export type MethodKey =
  | "digital"
  | "flexographic"
  | "internationalAir"
  | "internationalOcean";

export interface MethodConfig {
  label: string;
  tagline: string;
  leadTime: string;
  notes: string[];
  defaultTiers: number[];
  moq: number;
  minQtyToShow: number;
}

export const METHODS: Record<MethodKey, MethodConfig> = {
  digital: {
    label: "Digital",
    tagline: "Fast turn, great for new items or rush orders",
    leadTime: "As little as 2 weeks",
    notes: [],
    defaultTiers: [5_000, 10_000, 25_000, 50_000, 75_000, 100_000],
    moq: 5_000,
    minQtyToShow: 0,
  },
  flexographic: {
    label: "Flexographic",
    tagline: "Best for large consistent runs with inventory storage options",
    leadTime: "6-8 weeks",
    notes: ["Plate fee: $400/color"],
    defaultTiers: [50_000, 100_000, 150_000, 250_000, 500_000, 1_000_000],
    moq: 50_000,
    minQtyToShow: 50_000,
  },
  internationalAir: {
    label: "International Air",
    tagline: "Quality-inspected, air shipped for faster delivery",
    leadTime: "4-6 weeks",
    notes: ["Plate fee: $150/color"],
    defaultTiers: [25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000],
    moq: 10_000,
    minQtyToShow: 10_000,
  },
  internationalOcean: {
    label: "International Ocean",
    tagline: "Lowest cost, quality-inspected, ocean shipped",
    leadTime: "8-10 weeks",
    notes: ["Plate fee: $150/color"],
    defaultTiers: [25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000],
    moq: 10_000,
    minQtyToShow: 10_000,
  },
} as const;

export const DEFAULT_ACTIVE_QTY = 100_000;
