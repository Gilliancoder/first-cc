import { getIndex } from "@/lib/data";
import { formatDateShort } from "@/lib/dates";
import Link from "next/link";
import NavigationBar from "@/components/NavigationBar";

export default function ArchivePage() {
  const index = getIndex();

  return (
    <>
      <NavigationBar currentMode="daily" />
      <main className="max-w-3xl mx-auto px-4 py-8 pb-16">
        <h1 className="text-2xl font-bold text-[var(--foreground)] mb-8">Archive</h1>

        {!index || (index.daily.length === 0 && index.weekly.length === 0) ? (
          <p className="text-[var(--color-zh-text)]">No archived content yet.</p>
        ) : (
          <div className="space-y-10">
            {/* Daily entries */}
            {index.daily.length > 0 && (
              <section>
                <h2 className="text-lg font-semibold text-[var(--foreground)] mb-4 uppercase tracking-wide">
                  Daily
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                  {[...index.daily].reverse().map((entry) => (
                    <Link
                      key={entry.date}
                      href={`/daily/${entry.date}`}
                      className="block p-3 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-border)] transition-colors no-underline"
                    >
                      <div className="text-sm font-medium text-[var(--foreground)]">
                        {formatDateShort(entry.date)}
                      </div>
                      <div className="text-xs text-[var(--color-zh-text)] mt-1">
                        {entry.article_count} articles
                      </div>
                    </Link>
                  ))}
                </div>
              </section>
            )}

            {/* Weekly entries */}
            {index.weekly.length > 0 && (
              <section>
                <h2 className="text-lg font-semibold text-[var(--foreground)] mb-4 uppercase tracking-wide">
                  Weekly
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                  {[...index.weekly].reverse().map((entry) => (
                    <Link
                      key={entry.week}
                      href={`/weekly/${entry.week}`}
                      className="block p-3 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-border)] transition-colors no-underline"
                    >
                      <div className="text-sm font-medium text-[var(--foreground)]">
                        {entry.week}
                      </div>
                      <div className="text-xs text-[var(--color-zh-text)] mt-1">
                        {formatDateShort(entry.start_date)} – {formatDateShort(entry.end_date)}
                      </div>
                      <div className="text-xs text-[var(--color-zh-text)]">
                        {entry.article_count} articles
                      </div>
                    </Link>
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </main>
    </>
  );
}
