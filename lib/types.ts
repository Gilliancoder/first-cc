export type CategoryId = 'macroeconomics' | 'industry-focus' | 'special-topics' | 'uncategorized';

export interface Category {
  id: CategoryId;
  name_en: string;
  name_zh: string;
}

export interface BilingualParagraph {
  en: string;
  zh: string;
}

export interface ArticleSection {
  screenshot: string;
  en: string;
  zh?: string;
}

export interface Article {
  id: string;
  sender: string;
  title: string;
  paragraphs: BilingualParagraph[];
  sections?: ArticleSection[];
  recap_en: string;
  recap_zh: string;
  source?: string;
  images?: string[];
}

export interface DailyData {
  date: string;
  generated_at: string;
  mode: 'daily';
  categories: {
    category: Category;
    articles: Article[];
  }[];
}

export interface WeeklyData {
  week: string;
  start_date: string;
  end_date: string;
  generated_at: string;
  mode: 'weekly';
  days: DailyData[];
}

export interface IndexEntry {
  date: string;
  article_count: number;
  available: boolean;
}

export interface WeeklyIndexEntry {
  week: string;
  start_date: string;
  end_date: string;
  article_count: number;
}

export interface DataIndex {
  last_updated: string;
  daily: IndexEntry[];
  weekly: WeeklyIndexEntry[];
}
