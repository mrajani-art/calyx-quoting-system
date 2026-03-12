"use client";

import { useRef } from "react";
import { MessageSquare, Upload, Check } from "lucide-react";

interface Props {
  onRequestManager: () => void;
  onUploadArtwork: () => void;
  isRequestingManager?: boolean;
  managerRequested?: boolean;
}

export function PostQuoteActions({
  onRequestManager,
  onUploadArtwork,
  isRequestingManager = false,
  managerRequested = false,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files.length > 0) {
      onUploadArtwork();
    }
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {/* Request Account Manager */}
      <div className="flex flex-col rounded-xl border border-gray-10 bg-white p-5">
        <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-powder-blue">
          <MessageSquare size={20} className="text-calyx-blue" />
        </div>
        <h4 className="text-sm font-semibold text-gray-90">
          Request to Speak with an Account Manager
        </h4>
        <p className="mt-1 flex-1 text-sm text-gray-60">
          An account manager will reach out within one business day to discuss
          your project and answer any questions.
        </p>
        {managerRequested ? (
          <div className="mt-4 flex items-center gap-2 text-sm font-medium text-green-700">
            <Check size={16} />
            <span>Request Sent</span>
          </div>
        ) : (
          <button
            type="button"
            onClick={onRequestManager}
            disabled={isRequestingManager}
            className="mt-4 rounded-lg border border-calyx-blue px-4 py-2 text-sm font-semibold text-calyx-blue hover:bg-calyx-blue hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isRequestingManager ? "Sending..." : "Request a Call"}
          </button>
        )}
      </div>

      {/* Upload Artwork */}
      <div className="flex flex-col rounded-xl border border-gray-10 bg-white p-5">
        <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-powder-blue">
          <Upload size={20} className="text-calyx-blue" />
        </div>
        <h4 className="text-sm font-semibold text-gray-90">
          Upload Artwork to Finalize Quote
        </h4>
        <p className="mt-1 flex-1 text-sm text-gray-60">
          Upload your label artwork so our team can prepare a finalized quote
          with exact production specifications.
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.pdf"
          onChange={handleFileChange}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="mt-4 rounded-lg border border-calyx-blue px-4 py-2 text-sm font-semibold text-calyx-blue hover:bg-calyx-blue hover:text-white transition-colors"
        >
          Upload Artwork
        </button>
      </div>
    </div>
  );
}
