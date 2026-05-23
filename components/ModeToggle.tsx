"use client";

import Link from "next/link";

interface ModeToggleProps {
  currentMode: "daily" | "weekly";
  date?: string;
  week?: string;
}

export default function ModeToggle({ currentMode, date, week }: ModeToggleProps) {
  const dailyHref = date ? `/daily/${date}` : "/daily";
  const weeklyHref = week ? `/weekly/${week}` : "/weekly";

  return (
    <div className="flex rounded-lg bg-[var(--color-surface)] p-0.5 text-sm">
      <Link
        href={dailyHref}
        className={`px-3 py-1 rounded-md transition-colors no-underline ${
          currentMode === "daily"
            ? "bg-[var(--background)] text-[var(--color-accent)] font-medium shadow-sm"
            : "text-[var(--color-zh-text)] hover:text-[var(--foreground)]"
        }`}
      >
        Daily
      </Link>
      <Link
        href={weeklyHref}
        className={`px-3 py-1 rounded-md transition-colors no-underline ${
          currentMode === "weekly"
            ? "bg-[var(--background)] text-[var(--color-accent)] font-medium shadow-sm"
            : "text-[var(--color-zh-text)] hover:text-[var(--foreground)]"
        }`}
      >
        Weekly
      </Link>
    </div>
  );
}
