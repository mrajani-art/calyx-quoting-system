"use client";

import { useState, useCallback } from "react";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import StepTransition from "@/components/layout/StepTransition";
import StandardSizeSelector from "@/components/configurator/StandardSizeSelector";
import CustomSizeInput from "@/components/configurator/CustomSizeInput";
import BagOptionsForm from "@/components/configurator/BagOptionsForm";
import TierSelector from "@/components/configurator/TierSelector";
import BagPreview from "@/components/configurator/BagPreview";
import { LeadCaptureForm } from "@/components/lead-capture/LeadCaptureForm";
import QuoteSummaryHeader from "@/components/results/QuoteSummaryHeader";
import PricingGrid from "@/components/results/PricingGrid";
import ResultsSkeleton from "@/components/results/ResultsSkeleton";
import { PostQuoteActions } from "@/components/results/PostQuoteActions";
import { useLeadSession } from "@/lib/hooks/useLeadSession";
import { submitLead, getInstantQuote, requestAccountManager } from "@/lib/api/quote-client";
import { getUserFriendlyError } from "@/lib/api/errors";
import { DEFAULTS } from "@/lib/constants/bag-options";
import { DEFAULT_ACTIVE_QTY } from "@/lib/constants/method-config";
import type { InstantQuoteResponse, BagConfig } from "@/lib/types/quote";

type Step = "configure" | "lead-capture" | "results";

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
  const [gussetType, setGussetType] = useState<string>(DEFAULTS.gussetType);

  // Tier state
  const defaultTiers = [5_000, 10_000, 25_000, 50_000, 100_000, 250_000];
  const [selectedTiers, setSelectedTiers] = useState<number[]>(defaultTiers);
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
        if (value === "Stand Up Pouch") {
          setFillStyle("Top");
          // Stand Up Pouches always need a gusset type
          setGussetType((prev) => prev === "None" ? "K Seal" : prev);
        }
        break;
      case "fillStyle": setFillStyle(value); break;
      case "gussetType": setGussetType(value); break;
      case "zipper": setZipper(value); break;
      case "tearNotch": setTearNotch(value); break;
      case "holePunch": setHolePunch(value); break;
      case "corners": setCorners(value); break;
    }
  }, []);

  const handleEditTier = useCallback((oldQty: number, newQty: number) => {
    setSelectedTiers((prev) =>
      prev.map((t) => (t === oldQty ? newQty : t)).sort((a, b) => a - b)
    );
    // If the active tier was the one edited, update it
    if (oldQty === activeTier) {
      setActiveTier(newQty);
    }
  }, [activeTier]);

  const buildBagConfig = useCallback((): BagConfig => ({
    width: dims.w,
    height: dims.h,
    gusset: dims.g,
    substrate,
    finish,
    seal_type: sealType,
    fill_style: fillStyle,
    gusset_type: gussetType,
    zipper,
    tear_notch: tearNotch,
    hole_punch: holePunch,
    corners,
    embellishment: "None",
    quantities: selectedTiers,
  }), [dims, substrate, finish, sealType, fillStyle, gussetType, zipper, tearNotch, holePunch, corners, selectedTiers]);

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
      setError(getUserFriendlyError(err));
    }
  };

  const fetchQuote = async (leadId: string) => {
    setIsLoading(true);
    setError(null);
    setStep("results");
    try {
      const config = buildBagConfig();
      const result = await getInstantQuote(config, leadId);
      setQuote(result);
    } catch (err) {
      setError(getUserFriendlyError(err));
      setStep("configure");
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
    <div className="min-h-[100dvh] flex flex-col overflow-x-hidden">
      <Header />
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-8">
        {/* Step indicators */}
        <div className="flex items-center gap-3 mb-8">
          {["Configure", "Contact Info", "Your Pricing"].map((label, i) => {
            const stepKeys: Step[] = ["configure", "lead-capture", "results"];
            const currentIdx = stepKeys.indexOf(step);
            const isActive = currentIdx >= i;
            const isCompleted = i < currentIdx;
            const canClick = isCompleted && (stepKeys[i] !== "results" || quote !== null);

            const indicator = (
              <>
                <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${isActive ? "bg-calyx-blue text-white" : "bg-gray-10 text-gray-30"}`}>
                  {i + 1}
                </span>
                {label}
              </>
            );

            return (
              <div key={label} className="flex items-center gap-3">
                {i > 0 && (
                  <div className={`h-px w-8 ${isActive ? "bg-calyx-blue" : "bg-gray-10"}`} />
                )}
                {canClick ? (
                  <button
                    type="button"
                    onClick={() => setStep(stepKeys[i])}
                    className={`flex items-center gap-2 text-sm font-medium cursor-pointer hover:text-flash-blue ${isActive ? "text-calyx-blue" : "text-gray-30"}`}
                  >
                    {indicator}
                  </button>
                ) : (
                  <div className={`flex items-center gap-2 text-sm font-medium ${isActive ? "text-calyx-blue" : "text-gray-30"}`}>
                    {indicator}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {error && (
          <div className="mb-6 rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        <StepTransition stepKey={step}>
        {/* Step 1: Configure Bag */}
        {step === "configure" && (
          <div className="lg:flex lg:gap-8">
            {/* Left: form content */}
            <div className="flex-1 min-w-0 space-y-8">
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
                  gussetType={gussetType}
                  zipper={zipper}
                  tearNotch={tearNotch}
                  holePunch={holePunch}
                  corners={corners}
                  gusset={dims.g}
                  onChange={handleOptionChange}
                />
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-90 mb-4">Quantity Tiers</h3>
                <p className="text-sm text-gray-60 mb-3">Click to compare pricing. Tap the pencil to edit quantities.</p>
                <TierSelector
                  tiers={selectedTiers}
                  activeTier={activeTier}
                  onTierClick={setActiveTier}
                  onEditTier={handleEditTier}
                />
              </div>

              {/* Mobile bag preview */}
              <div className="lg:hidden">
                <BagPreview
                  compact
                  width={dims.w}
                  height={dims.h}
                  gusset={dims.g}
                  sealType={sealType}
                  gussetType={gussetType}
                  zipper={zipper}
                  tearNotch={tearNotch}
                  holePunch={holePunch}
                  corners={corners}
                  substrate={substrate}
                  finish={finish}
                />
              </div>

              <button
                onClick={handleContinue}
                disabled={isLoading}
                className="bg-calyx-blue text-white px-8 py-3 rounded-lg font-medium hover:bg-flash-blue transition-colors disabled:opacity-50"
              >
                {isLoading ? "Loading..." : lead ? "See My Quote" : "Continue"}
              </button>
            </div>

            {/* Right: sticky bag preview (desktop only) */}
            <div className="hidden lg:block lg:w-80 xl:w-96 shrink-0">
              <div className="sticky top-8">
                <BagPreview
                  width={dims.w}
                  height={dims.h}
                  gusset={dims.g}
                  sealType={sealType}
                  gussetType={gussetType}
                  zipper={zipper}
                  tearNotch={tearNotch}
                  holePunch={holePunch}
                  corners={corners}
                  substrate={substrate}
                  finish={finish}
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Lead Capture */}
        {step === "lead-capture" && (
          <div className="max-w-lg mx-auto space-y-6">
            <button
              type="button"
              onClick={() => setStep("configure")}
              className="text-sm text-calyx-blue hover:text-flash-blue font-medium mb-4"
            >
              &larr; Back to Configuration
            </button>

            <div className="rounded-xl border border-gray-10 bg-gray-5 p-4 flex items-center gap-4 mb-6">
              <BagPreview compact width={dims.w} height={dims.h} gusset={dims.g} sealType={sealType} gussetType={gussetType} zipper={zipper} tearNotch={tearNotch} holePunch={holePunch} corners={corners} substrate={substrate} finish={finish} />
              <div className="text-sm text-gray-60">
                <p className="font-medium text-gray-90">{dims.w}&quot; &times; {dims.h}&quot;{dims.g > 0 ? ` \u00d7 ${dims.g}"` : ""} {sealType}</p>
                <p>{substrate} &middot; {finish} &middot; {zipper} Zipper</p>
              </div>
            </div>

            <div>
              <h2 className="text-2xl font-semibold text-gray-90">One more step to see your pricing</h2>
              <p className="mt-1 text-gray-60">
                Enter your details and we&apos;ll show your instant quote.
              </p>
            </div>
            <LeadCaptureForm
              onSubmit={handleLeadSubmit}
              isSubmitting={isLoading}
            />
          </div>
        )}

        {/* Step 3: Loading */}
        {step === "results" && !quote && isLoading && (
          <ResultsSkeleton />
        )}

        {/* Step 3: Pricing Results */}
        {step === "results" && quote && (
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-gray-90">Your Instant Quote</h2>
                <p className="mt-1 text-gray-60">
                  Compare production methods and quantities side by side.
                </p>
              </div>
              <button
                onClick={() => setStep("configure")}
                className="shrink-0 rounded-lg border border-calyx-blue px-4 py-2 text-sm font-semibold text-calyx-blue hover:bg-calyx-blue hover:text-white transition-colors"
              >
                Edit Configuration
              </button>
            </div>

            <QuoteSummaryHeader
              visualProps={{
                width: dims.w,
                height: dims.h,
                gusset: dims.g,
                sealType,
                gussetType,
                zipper,
                tearNotch,
                holePunch,
                corners,
                substrate,
                finish,
              }}
            />

            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-90 mb-3">Quantity Tiers</h3>
              <div className="flex justify-center">
                <TierSelector
                  tiers={selectedTiers}
                  activeTier={activeTier}
                  onTierClick={setActiveTier}
                  onEditTier={handleEditTier}
                />
              </div>
            </div>

            <PricingGrid
              quote={quote}
              tiers={selectedTiers}
              activeTier={activeTier}
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
        </StepTransition>
      </main>
      <Footer />
    </div>
  );
}
