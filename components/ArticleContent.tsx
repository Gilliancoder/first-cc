import { BilingualParagraph, ArticleSection } from "@/lib/types";

interface ArticleContentProps {
  paragraphs: BilingualParagraph[];
  sections?: ArticleSection[];
  images?: string[];
}

export default function ArticleContent({ paragraphs, sections, images }: ArticleContentProps) {
  const hasSections = sections && sections.length > 0;
  const hasParagraphs = paragraphs && paragraphs.length > 0;
  const hasImages = images && images.length > 0;

  if (!hasSections && !hasParagraphs && !hasImages) {
    return (
      <p className="text-sm text-[var(--color-zh-text)]">
        Content not available.
      </p>
    );
  }

  // New screenshot-based rendering
  if (hasSections) {
    return (
      <div className="article-content space-y-8">
        {sections.map((section, i) => (
          <div key={i} className="section-block">
            {/* Screenshot of original email section */}
            {section.screenshot && (
              <figure className="m-0 mb-4">
                <img
                  src={`/${section.screenshot}`}
                  alt={`Section ${i + 1}`}
                  className="w-full h-auto rounded-lg border border-[var(--color-border)] shadow-sm"
                  loading="lazy"
                />
              </figure>
            )}
            {/* English text */}
            {section.en && (
              <p className="paragraph-en text-[15px] leading-relaxed mb-3">
                {section.en}
              </p>
            )}
            {/* Chinese translation (from paragraphs if available) */}
            {section.zh && (
              <div className="paragraph-zh bg-[var(--color-zh-bg)] rounded-md px-4 py-3">
                <p className="text-[15px] leading-relaxed" style={{ fontFamily: 'var(--font-zh)' }}>
                  {section.zh}
                </p>
              </div>
            )}
          </div>
        ))}
        {hasImages && _renderImages(images)}
      </div>
    );
  }

  // Legacy paragraph-based rendering (fallback)
  return (
    <div className="article-content">
      {hasParagraphs &&
        paragraphs.map((para, i) => (
          <div key={i}>
            <p className="paragraph-en">{para.en}</p>
            {para.zh && (
              <div className="paragraph-zh">
                <p style={{ fontFamily: 'var(--font-zh)' }}>{para.zh}</p>
              </div>
            )}
          </div>
        ))}

      {hasImages && _renderImages(images)}
    </div>
  );
}

function _renderImages(images: string[]) {
  return (
    <div className="mt-6 pt-4 border-t border-[var(--color-border)]">
      <h4 className="text-xs font-semibold text-[var(--color-zh-text)] uppercase tracking-wide mb-3">
        Charts & Figures / 图表
      </h4>
      <div className="space-y-4">
        {images.map((imgPath, i) => (
          <figure key={i} className="m-0">
            <img
              src={`/${imgPath}`}
              alt={`Chart ${i + 1}`}
              className="w-full h-auto rounded-lg border border-[var(--color-border)]"
              loading="lazy"
            />
          </figure>
        ))}
      </div>
    </div>
  );
}
