import { redirect } from "next/navigation";
import { getLatestDate, getLatestWeek } from "@/lib/data";

export default function Home() {
  const latestDate = getLatestDate();
  if (latestDate) {
    redirect(`/daily/${latestDate}`);
  }
  const latestWeek = getLatestWeek();
  if (latestWeek) {
    redirect(`/weekly/${latestWeek}`);
  }
  return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-[var(--color-zh-text)]">No data available. Run the pipeline to generate content.</p>
    </div>
  );
}
