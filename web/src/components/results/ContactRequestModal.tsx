"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import { X, Upload, Check, Loader2 } from "lucide-react";

interface ContactRequestModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (note: string, files: File[]) => Promise<void>;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ContactRequestModal({
  open,
  onClose,
  onSubmit,
}: ContactRequestModalProps) {
  const [note, setNote] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setNote("");
      setFiles([]);
      setLoading(false);
      setSuccess(false);
      setError(null);
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
    if (!success) return;
    const timer = setTimeout(() => {
      onClose();
    }, 1500);
    return () => clearTimeout(timer);
  }, [success, onClose]);

  const handleBackdropClick = useCallback(() => {
    if (!loading) {
      onClose();
    }
  }, [loading, onClose]);

  const handleSubmit = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await onSubmit(note, files);
      setSuccess(true);
    } catch (err) {
      setLoading(false);
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong. Please try again."
      );
    }
  }, [note, files, onSubmit]);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        setFiles(prev => [...prev, ...Array.from(e.target.files!)]);
      }
      // Reset input so the same file can be re-selected
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    []
  );

  const removeFile = useCallback((index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, []);

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
        className="relative w-full max-w-lg rounded-xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Success state */}
        {success ? (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
              <Check size={32} className="text-green-600" />
            </div>
            <p className="text-lg font-semibold text-gray-90">Request Sent!</p>
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

            {/* Title & subtitle */}
            <h2 className="text-lg font-semibold text-gray-90 pr-8">
              Request to Speak with an Account Manager
            </h2>
            <p className="mt-1 text-sm text-gray-60">
              An account manager will reach out within one business day.
            </p>

            {/* Note textarea */}
            <div className="mt-5">
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Add a note about your project (optional)..."
                rows={4}
                disabled={loading}
                className="w-full rounded-lg border border-gray-10 bg-gray-5 px-4 py-3 text-sm text-gray-90 placeholder:text-gray-40 focus:border-calyx-blue focus:outline-none focus:ring-1 focus:ring-calyx-blue disabled:opacity-50 resize-none"
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
                    <div key={`${f.name}-${index}`} className="flex items-center gap-3 rounded-lg border border-gray-10 bg-gray-5 px-4 py-3">
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
                        disabled={loading}
                        className="shrink-0 rounded p-1 text-gray-40 hover:bg-white hover:text-gray-60 disabled:opacity-50 transition-colors"
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
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-gray-10 bg-gray-5 px-4 py-3 text-sm font-medium text-gray-60 hover:border-calyx-blue hover:text-calyx-blue disabled:opacity-50 transition-colors"
              >
                <Upload size={18} />
                <span>Attach artwork (optional)</span>
              </button>
            </div>

            {/* Error message */}
            {error && (
              <div className="mt-4 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
                {error}
              </div>
            )}

            {/* Submit button */}
            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-calyx-blue px-4 py-3 text-sm font-semibold text-white hover:bg-flash-blue disabled:opacity-70 disabled:cursor-not-allowed transition-colors"
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
          </>
        )}
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
