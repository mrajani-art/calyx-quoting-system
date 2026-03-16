export interface TierPrice {
  quantity: number;
  unit_price: number;
  total_price: number;
}

export interface MethodPricing {
  tiers: TierPrice[];
  lead_time: string;
  notes: string[];
}

export interface InstantQuoteResponse {
  quote_id: number;
  specifications: Record<string, string | number>;
  digital: MethodPricing | null;
  flexographic: MethodPricing | null;
  international_air: MethodPricing | null;
  international_ocean: MethodPricing | null;
}

export interface LeadData {
  lead_id: number;
  full_name: string;
  business_name: string;
  email: string;
  phone: string;
  annual_spend: string;
}

export interface BagConfig {
  width: number;
  height: number;
  gusset: number;
  substrate: string;
  finish: string;
  seal_type: string;
  fill_style: string;
  gusset_type: string;
  zipper: string;
  tear_notch: string;
  hole_punch: string;
  corners: string;
  embellishment: string;
  quantities: number[];
}
