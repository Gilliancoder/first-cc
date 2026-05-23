import { getAvailableDailyDates, getDailyData } from "@/lib/data";
import { getAdjacentDate } from "@/lib/dates";
import NavigationBar from "@/components/NavigationBar";
import DateSelector from "@/components/DateSelector";
import CategorySection from "@/components/CategorySection";

export function generateStaticParams() {
  const dates = getAvailableDailyDates();
  return dates.map((date) => ({ date }));
}

interface DailyPageProps {
  params: Promise<{ date: string }>;
}

export default async function DailyPage({ params }: DailyPageProps) {
  const { date } = await params;
  const data = getDailyData(date);

  if (!data) {
    return (
      <>
        <NavigationBar currentDate={date} />
        <main className="max-w-3xl mx-auto px-4 py-12 text-center">
          <p className="text-[var(--color-zh-text)]">No data for {date}.</p>
        </main>
      </>
    );
  }

  const allDates = getAvailableDailyDates();
  const prevDate = getAdjacentDate(date, "prev", allDates);
  const nextDate = getAdjacentDate(date, "next", allDates);

  return (
    <>
      <NavigationBar currentDate={date} />
      <main className="max-w-3xl mx-auto px-4 pb-16">
        <DateSelector date={date} prevDate={prevDate} nextDate={nextDate} />
        {data.categories.map((cat) => (
          <CategorySection
            key={cat.category.id}
            category={cat.category}
            articles={cat.articles}
            date={date}
          />
        ))}
      </main>
    </>
  );
}
