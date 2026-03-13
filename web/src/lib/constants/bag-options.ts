export const SUBSTRATES = [
  { label: "Metallic", value: "Metallic" },
  { label: "Clear", value: "Clear" },
  { label: "White Metallic", value: "White Metallic" },
  { label: "High Barrier", value: "High Barrier" },
] as const;

export const FINISHES = [
  { label: "Matte", value: "Matte" },
  { label: "Soft Touch", value: "Soft Touch" },
  { label: "Gloss", value: "Gloss" },
  { label: "None", value: "None" },
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
  { label: "Plow Bottom", value: "Plow Bottom" },
  { label: "K Seal", value: "K Seal" },
  { label: "None", value: "None" },
] as const;

export const ZIPPERS = [
  { label: "Child-Resistant", value: "Child-Resistant" },
  { label: "Standard", value: "Standard" },
  { label: "None", value: "None" },
] as const;

export const TEAR_NOTCHES = [
  { label: "Standard", value: "Standard" },
  { label: "None", value: "None" },
] as const;

export const HOLE_PUNCHES = [
  { label: "Round", value: "Round" },
  { label: "Euro Slot", value: "Euro Slot" },
  { label: "None", value: "None" },
] as const;

export const CORNERS = [
  { label: "Rounded", value: "Rounded" },
  { label: "Straight", value: "Straight" },
] as const;

export const EMBELLISHMENTS = [
  { label: "None", value: "None" },
  { label: "Foil", value: "Foil" },
  { label: "Spot UV", value: "Spot UV" },
] as const;

export const ANNUAL_SPEND_OPTIONS = [
  "<$10K",
  "$10-50K",
  "$50-100K",
  "$100-250K",
  "$250K+",
] as const;

// Default selections
export const DEFAULTS = {
  substrate: "Metallic",
  finish: "Matte",
  sealType: "Stand Up Pouch",
  fillStyle: "Top",
  gussetType: "Plow Bottom",
  zipper: "None",
  tearNotch: "Standard",
  holePunch: "None",
  corners: "Straight",
  embellishment: "None",
} as const;
