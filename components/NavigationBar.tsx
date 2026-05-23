import Link from "next/link";
import { APP_NAME } from "@/lib/constants";

interface NavigationBarProps {
  currentDate?: string;
}

export default function NavigationBar({ currentDate }: NavigationBarProps) {
  return (
    <header className="sticky top-0 z-50 bg-[var(--background)] border-b border-[var(--color-border)]">
      <div className="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link
          href="/"
          className="font-bold text-lg tracking-tight text-[var(--color-accent)] no-underline"
        >
          {APP_NAME}
        </Link>

        <div className="flex items-center gap-3">
          <Link
            href="/archive"
            className="text-sm text-[var(--color-zh-text)] hover:text-[var(--color-accent)] transition-colors no-underline"
          >
            Archive
          </Link>
        </div>
      </div>
    </header>
  );
}
