"use client";

import Link from "next/link";
import { formatDate } from "@/lib/dates";

interface DateSelectorProps {
  date: string;
  prevDate: string | null;
  nextDate: string | null;
}

export default function DateSelector({ date, prevDate, nextDate }: DateSelectorProps) {
  return (
    <div className="flex items-center justify-center gap-4 py-6">
      {prevDate ? (
        <Link
          href={`/daily/${prevDate}`}
          className="flex items-center justify-center w-9 h-9 rounded-full bg-[var(--color-surface)] hover:bg-[var(--color-border)] text-[var(--color-zh-text)] hover:text-[var(--foreground)] transition-colors no-underline text-lg"
          aria-label="Previous day"
        >
          &larr;
        </Link>
      ) : (
        <div className="w-9 h-9" />
      )}

      <h2 className="text-lg font-semibold text-[var(--foreground)] min-w-[200px] text-center">
        {formatDate(date)}
      </h2>

      {nextDate ? (
        <Link
          href={`/daily/${nextDate}`}
          className="flex items-center justify-center w-9 h-9 rounded-full bg-[var(--color-surface)] hover:bg-[var(--color-border)] text-[var(--color-zh-text)] hover:text-[var(--foreground)] transition-colors no-underline text-lg"
          aria-label="Next day"
        >
          &rarr;
        </Link>
      ) : (
        <div className="w-9 h-9" />
      )}
    </div>
  );
}
