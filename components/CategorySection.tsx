import { Category, Article as ArticleType } from "@/lib/types";
import ArticleCard from "./ArticleCard";

interface CategorySectionProps {
  category: Category;
  articles: ArticleType[];
  date: string;
}

export default function CategorySection({ category, articles, date }: CategorySectionProps) {
  return (
    <section className="mb-8">
      <div
        className={`border-l-4 pl-4 mb-3 category-accent-${category.id}`}
      >
        <h3 className="text-lg font-semibold text-[var(--foreground)]">
          {category.name_en}
        </h3>
        <p className="text-sm text-[var(--color-zh-text)] font-[var(--font-zh)]">
          {category.name_zh}
        </p>
      </div>

      {articles.length > 0 ? (
        <div className="divide-y divide-[var(--color-border)]">
          {articles.map((article) => (
            <ArticleCard key={article.id} article={article} date={date} />
          ))}
        </div>
      ) : (
        <div className="py-8 text-center text-sm text-[var(--color-zh-text)]">
          <p className="font-[var(--font-en)]">No articles in this category today.</p>
          <p className="font-[var(--font-zh)] mt-1">今日该分类暂无文章。</p>
        </div>
      )}
    </section>
  );
}
