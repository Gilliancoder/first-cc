import { getAvailableWeeklyWeeks, getWeeklyData } from "@/lib/data";
import { getWeekRange } from "@/lib/dates";
import NavigationBar from "@/components/NavigationBar";
import WeekSelector from "@/components/WeekSelector";
import CategorySection from "@/components/CategorySection";

export function generateStaticParams() {
  const weeks = getAvailableWeeklyWeeks();
  return weeks.map((week) => ({ week }));
}

interface WeeklyPageProps {
  params: Promise<{ week: string }>;
}

export default async function WeeklyPage({ params }: WeeklyPageProps) {
  const { week } = await params;
  const data = getWeeklyData(week);

  if (!data) {
    return (
      <>
        <NavigationBar currentMode="weekly" currentWeek={week} />
        <main className="max-w-3xl mx-auto px-4 py-12 text-center">
          <p className="text-[var(--color-zh-text)]">No data for {week}.</p>
        </main>
      </>
    );
  }

  const allWeeks = getAvailableWeeklyWeeks();
  const sorted = [...allWeeks].sort();
  const idx = sorted.indexOf(week);
  const prevWeek = idx > 0 ? sorted[idx - 1] : null;
  const nextWeek = idx < sorted.length - 1 ? sorted[idx + 1] : null;

  return (
    <>
      <NavigationBar currentMode="weekly" currentWeek={week} />
      <main className="max-w-3xl mx-auto px-4 pb-16">
        <WeekSelector
          week={week}
          startDate={data.start_date}
          endDate={data.end_date}
          prevWeek={prevWeek}
          nextWeek={nextWeek}
        />

        {data.days.map((day) => {
          const { start, end } = getWeekRange(week);
          const isInRange = day.date >= start && day.date <= end;
          if (!isInRange) return null;

          return (
            <details key={day.date} className="mb-6 group" open={data.days.length <= 3}>
              <summary className="cursor-pointer list-none flex items-center gap-2 mb-3 text-sm font-medium text-[var(--color-accent)] hover:text-[var(--color-accent-light)] transition-colors">
                <span className="text-xs transition-transform group-open:rotate-90">&rarr;</span>
                {day.date}
                <span className="text-xs text-[var(--color-zh-text)] font-normal">
                  ({day.categories.reduce((sum, c) => sum + c.articles.length, 0)} articles)
                </span>
              </summary>

              <div className="ml-4 pl-4 border-l-2 border-[var(--color-border)]">
                {day.categories
                  .filter((cat) => cat.articles.length > 0)
                  .map((cat) => (
                    <CategorySection
                      key={cat.category.id}
                      category={cat.category}
                      articles={cat.articles}
                      date={day.date}
                    />
                  ))}
                {day.categories.every((cat) => cat.articles.length === 0) && (
                  <div className="py-4 text-center text-sm text-[var(--color-zh-text)]">
                    No articles this day.
                  </div>
                )}
              </div>
            </details>
          );
        })}
      </main>
    </>
  );
}
