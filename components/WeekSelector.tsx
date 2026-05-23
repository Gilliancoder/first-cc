"use client";

import Link from "next/link";
import { formatWeekRange } from "@/lib/dates";

interface WeekSelectorProps {
  week: string;
  startDate: string;
  endDate: string;
  prevWeek: string | null;
  nextWeek: string | null;
}

export default function WeekSelector({
  week,
  startDate,
  endDate,
  prevWeek,
  nextWeek,
}: WeekSelectorProps) {
  return (
    <div className="flex items-center justify-center gap-4 py-6">
      {prevWeek ? (
        <Link
          href={`/weekly/${prevWeek}`}
          className="flex items-center justify-center w-9 h-9 rounded-full bg-[var(--color-surface)] hover:bg-[var(--color-border)] text-[var(--color-zh-text)] hover:text-[var(--foreground)] transition-colors no-underline text-lg"
          aria-label="Previous week"
        >
          &larr;
        </Link>
      ) : (
        <div className="w-9 h-9" />
      )}

      <div className="text-center">
        <h2 className="text-lg font-semibold text-[var(--foreground)]">
          {formatWeekRange(startDate, endDate)}
        </h2>
        <p className="text-xs text-[var(--color-zh-text)]">{week}</p>
      </div>

      {nextWeek ? (
        <Link
          href={`/weekly/${nextWeek}`}
          className="flex items-center justify-center w-9 h-9 rounded-full bg-[var(--color-surface)] hover:bg-[var(--color-border)] text-[var(--color-zh-text)] hover:text-[var(--foreground)] transition-colors no-underline text-lg"
          aria-label="Next week"
        >
          &rarr;
        </Link>
      ) : (
        <div className="w-9 h-9" />
      )}
    </div>
  );
}
