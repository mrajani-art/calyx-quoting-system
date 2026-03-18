"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import { X, Upload, Check, Loader2, ArrowRight, Calendar } from "lucide-react";

interface ContactRequestModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (note: string, files: File[]) => Promise<void>;
  leadName?: string;
  leadEmail?: string;
}

type ModalStep = "notes" | "calendar" | "success";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const MEETINGS_SLUG = process.env.NEXT_PUBLIC_HUBSPOT_MEETINGS_SLUG || "owen-labombard";

export function ContactRequestModal({
  open,
  onClose,
  onSubmit,
  leadName,
  leadEmail,
}: ContactRequestModalProps) {
  const [step, setStep] = useState<ModalStep>("notes");
  const [note, setNote] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [meetingBooked, setMeetingBooked] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setStep("notes");
      setNote("");
      setFiles([]);
      setLoading(false);
      setError(null);
      setMeetingBooked(false);
    }
  }, [open]);

  // Close on Escape key
  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && !loading) {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, loading, onClose]);

  // Auto-close after success
  useEffect(() => {
    if (step !== "success") return;
    const timer = setTimeout(() => {
      onClose();
    }, 1500);
    return () => clearTimeout(timer);
  }, [step, onClose]);

  // Listen for HubSpot meeting booked postMessage
  useEffect(() => {
    if (step !== "calendar") return;

    function handleMessage(event: MessageEvent) {
      if (event.origin !== "https://meetings.hubspot.com") return;
      if (event.data?.meetingBookSucceeded) {
        setMeetingBooked(true);
      }
    }

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [step]);

  const handleBackdropClick = useCallback(() => {
    if (!loading) {
      onClose();
    }
  }, [loading, onClose]);

  // Submit the API call (fires on calendar step)
  const handleApiSubmit = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await onSubmit(note, files);
      setStep("success");
    } catch (err) {
      setLoading(false);
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong. Please try again."
      );
    }
  }, [note, files, onSubmit]);

  // Continue from notes to calendar
  const handleContinue = useCallback(() => {
    setStep("calendar");
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newFiles = e.target.files ? Array.from(e.target.files) : [];
      if (newFiles.length > 0) {
        setFiles((prev) => [...prev, ...newFiles]);
      }
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    []
  );

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, []);

  // Build HubSpot meetings iframe URL
  const meetingsUrl = (() => {
    const nameParts = (leadName || "").trim().split(/\s+/);
    const firstName = nameParts[0] || "";
    const lastName = nameParts.slice(1).join(" ") || "";
    const params = new URLSearchParams({
      embed: "true",
      firstname: firstName,
      lastname: lastName,
      email: leadEmail || "",
    });
    return `https://meetings.hubspot.com/${MEETINGS_SLUG}?${params.toString()}`;
  })();

  if (!open) return null;

  const modalContent = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={handleBackdropClick}
      />

      {/* Dialog card */}
      <div
        className={`relative w-full rounded-xl bg-white p-6 shadow-xl transition-all duration-200 ${
          step === "calendar" ? "max-w-2xl" : "max-w-lg"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Success state */}
        {step === "success" ? (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
              <Check size={32} className="text-green-600" />
            </div>
            <p className="text-lg font-semibold text-gray-90">
              {meetingBooked ? "Meeting Booked!" : "Request Sent!"}
            </p>
          </div>
        ) : (
          <>
            {/* Close button */}
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="absolute right-4 top-4 rounded-lg p-1 text-gray-40 hover:bg-gray-5 hover:text-gray-60 disabled:opacity-50 transition-colors"
              aria-label="Close"
            >
              <X size={20} />
            </button>

            {/* Step 1: Notes */}
            {step === "notes" && (
              <>
                <h2 className="text-lg font-semibold text-gray-90 pr-8">
                  Request to Speak with an Account Manager
                </h2>
                <p className="mt-1 text-sm text-gray-60">
                  Add any notes, then schedule a time to connect.
                </p>

                {/* Note textarea */}
                <div className="mt-5">
                  <textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Add a note about your project (optional)..."
                    rows={4}
                    className="w-full rounded-lg border border-gray-10 bg-gray-5 px-4 py-3 text-sm text-gray-90 placeholder:text-gray-40 focus:border-calyx-blue focus:outline-none focus:ring-1 focus:ring-calyx-blue resize-none"
                  />
                </div>

                {/* File upload */}
                <div className="mt-4">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,.pdf,.ai,.eps"
                    multiple
                    onChange={handleFileChange}
                    className="hidden"
                  />

                  {files.length > 0 && (
                    <div className="space-y-2 mb-2">
                      {files.map((f, index) => (
                        <div
                          key={`${f.name}-${index}`}
                          className="flex items-center gap-3 rounded-lg border border-gray-10 bg-gray-5 px-4 py-3"
                        >
                          <Upload size={18} className="shrink-0 text-calyx-blue" />
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium text-gray-90">
                              {f.name}
                            </p>
                            <p className="text-xs text-gray-60">
                              {formatFileSize(f.size)}
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => removeFile(index)}
                            className="shrink-0 rounded p-1 text-gray-40 hover:bg-white hover:text-gray-60 transition-colors"
                            aria-label="Remove file"
                          >
                            <X size={16} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-gray-10 bg-gray-5 px-4 py-3 text-sm font-medium text-gray-60 hover:border-calyx-blue hover:text-calyx-blue transition-colors"
                  >
                    <Upload size={18} />
                    <span>Attach artwork (optional)</span>
                  </button>
                </div>

                {/* Continue button */}
                <button
                  type="button"
                  onClick={handleContinue}
                  className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-calyx-blue px-4 py-3 text-sm font-semibold text-white hover:bg-flash-blue transition-colors"
                >
                  <span>Continue</span>
                  <ArrowRight size={18} />
                </button>
              </>
            )}

            {/* Step 2: Calendar */}
            {step === "calendar" && (
              <>
                <div className="flex items-center gap-2 pr-8">
                  <Calendar size={20} className="text-calyx-blue" />
                  <h2 className="text-lg font-semibold text-gray-90">
                    Schedule a Call
                  </h2>
                </div>
                <p className="mt-1 text-sm text-gray-60">
                  Pick a time that works for you, or submit your request without scheduling.
                </p>

                {/* HubSpot meetings iframe */}
                <div className="mt-4 rounded-lg border border-gray-10 overflow-hidden">
                  <iframe
                    src={meetingsUrl}
                    width="100%"
                    height="650"
                    frameBorder="0"
                    className="block"
                    title="Schedule a meeting"
                  />
                </div>

                {/* Error message */}
                {error && (
                  <div className="mt-4 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
                    {error}
                  </div>
                )}

                {/* Submit / Skip buttons */}
                <div className="mt-4 flex flex-col gap-2">
                  <button
                    type="button"
                    onClick={handleApiSubmit}
                    disabled={loading}
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-calyx-blue px-4 py-3 text-sm font-semibold text-white hover:bg-flash-blue disabled:opacity-70 disabled:cursor-not-allowed transition-colors"
                  >
                    {loading ? (
                      <>
                        <Loader2 size={18} className="animate-spin" />
                        <span>Submitting...</span>
                      </>
                    ) : (
                      <span>Submit Request</span>
                    )}
                  </button>
                  {!loading && (
                    <button
                      type="button"
                      onClick={handleApiSubmit}
                      className="text-sm text-gray-40 hover:text-gray-60 transition-colors py-1"
                    >
                      Skip scheduling &amp; submit request
                    </button>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
