export const STANDARD_SIZES = [
  { label: "Sample Edibles (2 pack), Vape Cartridge, Vape Pod", w: 3.5, h: 4.5, g: 0 },
  { label: "100mg Edibles, Flower, 1/8th, Edibles 200mg", w: 3.5, h: 6, g: 0 },
  { label: "Vape Cartridge, Vape Disposable, Vape Pen", w: 2.5, h: 5, g: 2 },
  { label: "1/8th Ounce, 100mg Edibles", w: 4.5, h: 5, g: 2 },
  { label: "1/4 Ounce, 1/2 Ounce Small Nugs", w: 6.5, h: 5, g: 2 },
  { label: "Medium Edibles, 1/8th of Flower (large bud)", w: 4.5, h: 6, g: 2 },
  { label: "Large Edibles, 1 Ounce, Half Ounce (large nugs)", w: 8, h: 6, g: 2 },
  { label: "1/2 Ounce, 100mg, 200mg Edibles", w: 4.5, h: 8, g: 2 },
  { label: "1 Ounce, Large Format Edibles, Small Exit Bag", w: 6, h: 8, g: 2 },
  { label: "Exit Bag, Swag, Giveaway Bags", w: 12, h: 10, g: 4 },
] as const;

export type StandardSize = (typeof STANDARD_SIZES)[number];
