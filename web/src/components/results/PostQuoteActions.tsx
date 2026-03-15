"use client";

import { useState } from "react";
import { MessageSquare, Check } from "lucide-react";
import { ContactRequestModal } from "./ContactRequestModal";

interface Props {
  onSubmitRequest: (note: string, file: File | null) => Promise<void>;
  managerRequested?: boolean;
}

export function PostQuoteActions({
  onSubmitRequest,
  managerRequested = false,
}: Props) {
  const [showModal, setShowModal] = useState(false);

  return (
    <>
      <div className="grid grid-cols-1 gap-4">
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
              onClick={() => setShowModal(true)}
              className="mt-4 rounded-lg border border-calyx-blue px-4 py-2 text-sm font-semibold text-calyx-blue hover:bg-calyx-blue hover:text-white transition-colors"
            >
              Request a Call
            </button>
          )}
        </div>
      </div>

      <ContactRequestModal
        open={showModal}
        onClose={() => setShowModal(false)}
        onSubmit={onSubmitRequest}
      />
    </>
  );
}
