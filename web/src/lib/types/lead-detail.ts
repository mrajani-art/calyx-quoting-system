export interface LeadDetail {
  id: string;
  full_name: string;
  business_name: string;
  email: string;
  phone: string;
  annual_spend: string;
  created_at: string;
}

export interface MethodPricingData {
  tiers: { quantity: number; unit_price: number; total_price: number }[];
  lead_time: string;
  notes: string[];
}

export interface QuoteDetail {
  id: string;
  created_at: string;
  specifications: {
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
  };
  pricing_digital: MethodPricingData | null;
  pricing_flexo: MethodPricingData | null;
  pricing_intl_air: MethodPricingData | null;
  pricing_intl_ocean: MethodPricingData | null;
  requested_manager: boolean;
  margin_applied: number | null;
}

export interface FileDetail {
  id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  public_url: string;
  created_at: string;
}

export interface LeadDetailResponse {
  lead: LeadDetail;
  quotes: QuoteDetail[];
  files: FileDetail[];
}
