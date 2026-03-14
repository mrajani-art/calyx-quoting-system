export const SUBSTRATES = [
  { label: "Metallic (High Barrier)", value: "Metallic" },
  { label: "White Metallic (High Barrier)", value: "White Metallic" },
  { label: "Clear (High Barrier)", value: "High Barrier" },
  { label: "Standard Clear", value: "Clear" },
] as const;

export const FINISHES = [
  { label: "Matte", value: "Matte" },
  { label: "Soft Touch", value: "Soft Touch" },
  { label: "Gloss", value: "Gloss" },
] as const;

export const SEAL_TYPES = [
  { label: "Stand Up Pouch", value: "Stand Up Pouch" },
  { label: "3 Side Seal", value: "3 Side Seal" },
  { label: "2 Side Seal", value: "2 Side Seal" },
] as const;

export const FILL_STYLES = [
  { label: "Top Fill", value: "Top" },
  { label: "Bottom Fill", value: "Bottom" },
] as const;

export const GUSSET_TYPES = [
  { label: "Plow Bottom – Flat base", value: "Plow Bottom" },
  { label: "K-Style – Skirt seal base", value: "K Seal" },
  { label: "None", value: "None" },
] as const;

export const ZIPPERS = [
  { label: "Child-Resistant", value: "Child-Resistant" },
  { label: "Standard", value: "Standard" },
] as const;

export const TEAR_NOTCHES = [
  { label: "Standard", value: "Standard" },
  { label: "None", value: "None" },
] as const;

export const HOLE_PUNCHES = [
  { label: "Round", value: "Round" },
  { label: "Sombrero", value: "Euro Slot" },
  { label: "None", value: "None" },
] as const;

export const CORNERS = [
  { label: "Rounded", value: "Rounded" },
  { label: "Straight", value: "Straight" },
] as const;

export const ANNUAL_SPEND_OPTIONS = [
  "<$10K",
  "$10-50K",
  "$50-100K",
  "$100-250K",
  "$250K+",
] as const;

export const OPTION_DESCRIPTIONS: Record<string, string> = {
  substrate: "High Barrier protects flower & edibles. Standard Clear is for vapes & non-perishables.",
  finish: "Surface coating that changes look and feel",
  sealType: "Determines bag shape and structure",
  fillStyle: "Whether product loads from top or bottom",
  gussetType: "Bottom fold style — determines how the bag stands upright",
  zipper: "Resealable closure type",
  tearNotch: "Small cut on the side for easy opening",
  holePunch: "Hole at top for hanging on retail displays",
  corners: "Shape of the bag corners",
};

// Default selections
export const DEFAULTS = {
  substrate: "Metallic",
  finish: "Matte",
  sealType: "Stand Up Pouch",
  fillStyle: "Top",
  gussetType: "K Seal",
  zipper: "Child-Resistant",
  tearNotch: "Standard",
  holePunch: "None",
  corners: "Straight",
} as const;
