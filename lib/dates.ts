export function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function formatDateShort(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

export function getAdjacentDate(dateStr: string, direction: 'prev' | 'next', availableDates: string[]): string | null {
  const sorted = [...availableDates].sort();
  const idx = sorted.indexOf(dateStr);
  if (idx === -1) return null;
  const newIdx = direction === 'prev' ? idx - 1 : idx + 1;
  return sorted[newIdx] ?? null;
}

export function getTodayStr(): string {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}
