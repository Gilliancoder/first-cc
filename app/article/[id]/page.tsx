import { getAllArticleIds, getArticleById } from "@/lib/data";
import ArticleContent from "@/components/ArticleContent";
import RecapBox from "@/components/RecapBox";
import BackButton from "@/components/BackButton";
import Link from "next/link";

export function generateStaticParams() {
  return getAllArticleIds();
}

interface ArticlePageProps {
  params: Promise<{ id: string }>;
}

export default async function ArticlePage({ params }: ArticlePageProps) {
  const { id } = await params;
  const article = getArticleById(id);

  if (!article) {
    return (
      <main className="max-w-3xl mx-auto px-4 py-12 text-center">
        <p className="text-[var(--color-zh-text)]">Article not found.</p>
        <Link href="/" className="text-[var(--color-accent)] mt-4 inline-block no-underline">
          &larr; Home
        </Link>
      </main>
    );
  }

  return (
    <>
      <header className="sticky top-0 z-50 bg-[var(--background)] border-b border-[var(--color-border)]">
        <div className="max-w-3xl mx-auto px-4 h-14 flex items-center gap-4">
          <BackButton />
          <span className="text-sm text-[var(--color-zh-text)] truncate">
            {article.sender} &mdash; {article.title}
          </span>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8 pb-16">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-[var(--foreground)] leading-tight mb-2">
            {article.title}
          </h1>
          <div className="flex items-center gap-3 text-sm">
            <span className="font-semibold text-[var(--color-accent)]">{article.sender}</span>
            {article.source === "WSJ" && (
              <span className="text-xs px-2 py-0.5 rounded bg-[var(--color-zh-bg)] text-[var(--color-zh-text)]">
                via Wall Street Journal
              </span>
            )}
          </div>
        </div>

        <ArticleContent
          paragraphs={article.paragraphs}
          sections={article.sections}
          images={article.images}
        />
        <RecapBox recapEn={article.recap_en} recapZh={article.recap_zh} />
      </main>
    </>
  );
}
