"use client";

import { useState, useCallback } from "react";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import StandardSizeSelector from "@/components/configurator/StandardSizeSelector";
import CustomSizeInput from "@/components/configurator/CustomSizeInput";
import BagOptionsForm from "@/components/configurator/BagOptionsForm";
import TierSelector from "@/components/configurator/TierSelector";
import { LeadCaptureForm } from "@/components/lead-capture/LeadCaptureForm";
import { PricingComparison } from "@/components/results/PricingComparison";
import { TierButtons } from "@/components/results/TierButtons";
import { PostQuoteActions } from "@/components/results/PostQuoteActions";
import { useLeadSession } from "@/lib/hooks/useLeadSession";
import { submitLead, getInstantQuote, requestAccountManager } from "@/lib/api/quote-client";
import { DEFAULTS } from "@/lib/constants/bag-options";
import { DEFAULT_ACTIVE_QTY, METHODS } from "@/lib/constants/method-config";
import type { InstantQuoteResponse, BagConfig } from "@/lib/types/quote";

type Step = "configure" | "lead-capture" | "results";

// Collect all unique tiers from all methods, sorted
function buildUnifiedTiers(): number[] {
  const all = new Set<number>();
  for (const m of Object.values(METHODS)) {
    for (const t of m.defaultTiers) all.add(t);
  }
  return Array.from(all).sort((a, b) => a - b);
}

export default function QuotePage() {
  const { lead, saveLead, isLoaded } = useLeadSession();

  // Step management
  const [step, setStep] = useState<Step>("configure");

  // Bag configuration state
  const [selectedSize, setSelectedSize] = useState<{ w: number; h: number; g: number } | null>({
    w: 4.5, h: 5, g: 2, // Default: 1/8th Ounce, 100mg Edibles
  });
  const [isCustomSize, setIsCustomSize] = useState(false);
  const [customWidth, setCustomWidth] = useState(4.5);
  const [customHeight, setCustomHeight] = useState(5);
  const [customGusset, setCustomGusset] = useState(2);

  // Bag options (pre-set defaults)
  const [substrate, setSubstrate] = useState<string>(DEFAULTS.substrate);
  const [finish, setFinish] = useState<string>(DEFAULTS.finish);
  const [sealType, setSealType] = useState<string>(DEFAULTS.sealType);
  const [fillStyle, setFillStyle] = useState<string>(DEFAULTS.fillStyle);
  const [zipper, setZipper] = useState<string>(DEFAULTS.zipper);
  const [tearNotch, setTearNotch] = useState<string>(DEFAULTS.tearNotch);
  const [holePunch, setHolePunch] = useState<string>(DEFAULTS.holePunch);
  const [corners, setCorners] = useState<string>(DEFAULTS.corners);
  const [embellishment, setEmbellishment] = useState<string>(DEFAULTS.embellishment);

  // Tier state
  const allTiers = buildUnifiedTiers();
  const defaultTiers = [5_000, 10_000, 25_000, 50_000, 100_000, 250_000];
  const [selectedTiers] = useState<number[]>(defaultTiers);
  const [activeTier, setActiveTier] = useState(DEFAULT_ACTIVE_QTY);

  // Results state
  const [quote, setQuote] = useState<InstantQuoteResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [managerRequested, setManagerRequested] = useState(false);

  // Get current dimensions
  const dims = isCustomSize
    ? { w: customWidth, h: customHeight, g: customGusset }
    : selectedSize ?? { w: 4.5, h: 5, g: 2 };

  const handleSizeSelect = useCallback(
    (size: { w: number; h: number; g: number } | "custom") => {
      if (size === "custom") {
        setIsCustomSize(true);
        setSelectedSize(null);
      } else {
        setIsCustomSize(false);
        setSelectedSize(size);
        setCustomWidth(size.w);
        setCustomHeight(size.h);
        setCustomGusset(size.g);
      }
    },
    []
  );

  const handleCustomDimChange = useCallback(
    (field: "width" | "height" | "gusset", value: number) => {
      if (field === "width") setCustomWidth(value);
      else if (field === "height") setCustomHeight(value);
      else setCustomGusset(value);
    },
    []
  );

  const handleOptionChange = useCallback((field: string, value: string) => {
    switch (field) {
      case "substrate": setSubstrate(value); break;
      case "finish": setFinish(value); break;
      case "sealType":
        setSealType(value);
        if (value === "Stand Up Pouch") setFillStyle("Top");
        break;
      case "fillStyle": setFillStyle(value); break;
      case "zipper": setZipper(value); break;
      case "tearNotch": setTearNotch(value); break;
      case "holePunch": setHolePunch(value); break;
      case "corners": setCorners(value); break;
      case "embellishment": setEmbellishment(value); break;
    }
  }, []);

  const buildBagConfig = useCallback((): BagConfig => ({
    width: dims.w,
    height: dims.h,
    gusset: dims.g,
    substrate,
    finish,
    seal_type: sealType,
    fill_style: fillStyle,
    zipper,
    tear_notch: tearNotch,
    hole_punch: holePunch,
    corners,
    embellishment,
    quantities: selectedTiers,
  }), [dims, substrate, finish, sealType, fillStyle, zipper, tearNotch, holePunch, corners, embellishment, selectedTiers]);

  const handleContinue = () => {
    // If lead already captured in session, skip to results
    if (lead) {
      fetchQuote(lead.lead_id);
    } else {
      setStep("lead-capture");
    }
  };

  const handleLeadSubmit = async (data: {
    full_name: string;
    business_name: string;
    email: string;
    phone: string;
    annual_spend: string;
  }) => {
    try {
      const leadData = await submitLead(data);
      saveLead(leadData);
      await fetchQuote(leadData.lead_id);
    } catch (err) {
      setError("Failed to submit. Please try again.");
    }
  };

  const fetchQuote = async (leadId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const config = buildBagConfig();
      const result = await getInstantQuote(config, leadId);
      setQuote(result);
      setStep("results");
    } catch (err) {
      setError("Failed to get pricing. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRequestManager = async () => {
    if (!quote || !lead) return;
    setManagerRequested(true);
    try {
      await requestAccountManager(quote.quote_id, lead.lead_id);
    } catch (err) {
      console.error("Failed to request manager:", err);
    }
  };

  const handleUploadArtwork = () => {
    // TODO: Upload to Supabase Storage
  };

  if (!isLoaded) return null;

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-8">
        {/* Step indicators */}
        <div className="flex items-center gap-3 mb-8">
          {["Configure", "Contact Info", "Your Pricing"].map((label, i) => {
            const stepKeys: Step[] = ["configure", "lead-capture", "results"];
            const isActive = stepKeys.indexOf(step) >= i;
            return (
              <div key={label} className="flex items-center gap-3">
                {i > 0 && (
                  <div className={`h-px w-8 ${isActive ? "bg-calyx-blue" : "bg-gray-10"}`} />
                )}
                <div className={`flex items-center gap-2 text-sm font-medium ${isActive ? "text-calyx-blue" : "text-gray-30"}`}>
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${isActive ? "bg-calyx-blue text-white" : "bg-gray-10 text-gray-30"}`}>
                    {i + 1}
                  </span>
                  {label}
                </div>
              </div>
            );
          })}
        </div>

        {error && (
          <div className="mb-6 rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Step 1: Configure Bag */}
        {step === "configure" && (
          <div className="space-y-8">
            <div>
              <h2 className="text-2xl font-semibold text-gray-90">Configure Your Bag</h2>
              <p className="mt-1 text-gray-60">Select a standard size or enter custom dimensions.</p>
            </div>

            <StandardSizeSelector
              selectedSize={selectedSize}
              onSelect={handleSizeSelect}
              isCustom={isCustomSize}
            />

            {isCustomSize && (
              <CustomSizeInput
                width={customWidth}
                height={customHeight}
                gusset={customGusset}
                onChange={handleCustomDimChange}
              />
            )}

            <div>
              <h3 className="text-lg font-semibold text-gray-90 mb-4">Bag Options</h3>
              <BagOptionsForm
                substrate={substrate}
                finish={finish}
                sealType={sealType}
                fillStyle={fillStyle}
                zipper={zipper}
                tearNotch={tearNotch}
                holePunch={holePunch}
                corners={corners}
                embellishment={embellishment}
                onChange={handleOptionChange}
              />
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-90 mb-4">Quantity Tiers</h3>
              <p className="text-sm text-gray-60 mb-3">Select a quantity to compare pricing across methods.</p>
              <TierSelector
                tiers={selectedTiers}
                activeTier={activeTier}
                onTierClick={setActiveTier}
              />
            </div>

            <button
              onClick={handleContinue}
              disabled={isLoading}
              className="bg-calyx-blue text-white px-8 py-3 rounded-lg font-medium hover:bg-flash-blue transition-colors disabled:opacity-50"
            >
              {isLoading ? "Loading..." : lead ? "See My Price" : "Continue"}
            </button>
          </div>
        )}

        {/* Step 2: Lead Capture */}
        {step === "lead-capture" && (
          <div className="max-w-lg mx-auto space-y-6">
            <div>
              <h2 className="text-2xl font-semibold text-gray-90">Tell Us About Your Business</h2>
              <p className="mt-1 text-gray-60">
                We need a few details before showing your pricing.
              </p>
            </div>
            <LeadCaptureForm
              onSubmit={handleLeadSubmit}
              isSubmitting={isLoading}
            />
          </div>
        )}

        {/* Step 3: Pricing Results */}
        {step === "results" && quote && (
          <div className="space-y-8">
            <div>
              <h2 className="text-2xl font-semibold text-gray-90">Your Instant Pricing</h2>
              <p className="mt-1 text-gray-60">
                Compare production methods side by side. Select a quantity tier to update pricing.
              </p>
            </div>

            <TierButtons
              tiers={selectedTiers}
              selectedTier={activeTier}
              onSelect={setActiveTier}
            />

            <PricingComparison
              quote={quote}
              selectedQuantity={activeTier}
            />

            <PostQuoteActions
              onRequestManager={handleRequestManager}
              onUploadArtwork={handleUploadArtwork}
              managerRequested={managerRequested}
            />

            <div className="pt-4 border-t border-gray-10">
              <button
                onClick={() => setStep("configure")}
                className="text-sm text-calyx-blue hover:text-flash-blue font-medium"
              >
                &larr; Modify Configuration
              </button>
            </div>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
