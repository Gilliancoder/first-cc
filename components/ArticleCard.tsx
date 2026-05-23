import Link from "next/link";
import { Article } from "@/lib/types";

interface ArticleCardProps {
  article: Article;
  date: string;
}

export default function ArticleCard({ article, date }: ArticleCardProps) {
  return (
    <Link
      href={`/article/${article.id}`}
      className="block py-3 px-4 -mx-4 rounded-lg hover:bg-[var(--color-surface)] transition-colors no-underline group"
    >
      <div className="flex items-baseline gap-2">
        <span className="text-xs font-semibold text-[var(--color-accent)] tracking-wide whitespace-nowrap">
          {article.sender}
        </span>
        <span className="text-[var(--color-zh-text)] text-xs">&mdash;</span>
        <span className="text-[var(--foreground)] group-hover:text-[var(--color-accent)] transition-colors leading-snug">
          {article.title}
        </span>
        {article.source === "WSJ" && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-zh-bg)] text-[var(--color-zh-text)]">
            WSJ
          </span>
        )}
      </div>
    </Link>
  );
}
