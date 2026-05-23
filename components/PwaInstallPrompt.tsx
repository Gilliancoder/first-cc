"use client";

import { usePwaInstall } from "@/hooks/usePwaInstall";

export default function PwaInstallPrompt() {
  const { isInstallable, promptInstall, dismissPrompt } = usePwaInstall();

  if (!isInstallable) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4 bg-[var(--color-accent)] text-white">
      <div className="max-w-3xl mx-auto flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold">Add to Home Screen</p>
          <p className="text-xs opacity-80 mt-0.5">Read newsletters offline, anytime.</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={dismissPrompt}
            className="px-3 py-1.5 text-xs bg-transparent border border-white/30 rounded-md hover:bg-white/10 transition-colors cursor-pointer"
          >
            Later
          </button>
          <button
            onClick={promptInstall}
            className="px-3 py-1.5 text-xs bg-white text-[var(--color-accent)] font-medium rounded-md hover:bg-white/90 transition-colors cursor-pointer"
          >
            Install
          </button>
        </div>
      </div>
    </div>
  );
}
