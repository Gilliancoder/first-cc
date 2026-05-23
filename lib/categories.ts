import { Category, CategoryId } from './types';

export const CATEGORIES: Category[] = [
  {
    id: 'macroeconomics' as CategoryId,
    name_en: 'Macroeconomics',
    name_zh: '宏观经济',
  },
  {
    id: 'industry-focus' as CategoryId,
    name_en: 'Industry Focus',
    name_zh: '行业聚焦',
  },
  {
    id: 'special-topics' as CategoryId,
    name_en: 'Special Topics',
    name_zh: '专题研究',
  },
  {
    id: 'uncategorized' as CategoryId,
    name_en: 'Other Articles',
    name_zh: '其他文章',
  },
];

export const CATEGORY_MAP: Record<CategoryId, Category> = Object.fromEntries(
  CATEGORIES.map((c) => [c.id, c])
) as Record<CategoryId, Category>;

export function getCategoryById(id: CategoryId): Category {
  return CATEGORY_MAP[id];
}
