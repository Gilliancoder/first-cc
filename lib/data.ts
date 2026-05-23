import fs from 'fs';
import path from 'path';
import { DailyData, WeeklyData, DataIndex, Article } from './types';

const DATA_DIR = path.join(process.cwd(), 'data');

function readJSON<T>(filePath: string): T | null {
  try {
    const raw = fs.readFileSync(filePath, 'utf-8');
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function getDailyData(date: string): DailyData | null {
  return readJSON<DailyData>(path.join(DATA_DIR, 'daily', `${date}.json`));
}

export function getWeeklyData(week: string): WeeklyData | null {
  return readJSON<WeeklyData>(path.join(DATA_DIR, 'weekly', `${week}.json`));
}

export function getIndex(): DataIndex | null {
  return readJSON<DataIndex>(path.join(DATA_DIR, 'index.json'));
}

export function getAvailableDailyDates(): string[] {
  const dir = path.join(DATA_DIR, 'daily');
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith('.json'))
    .map((f) => f.replace('.json', ''))
    .sort();
}

export function getAvailableWeeklyWeeks(): string[] {
  const dir = path.join(DATA_DIR, 'weekly');
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith('.json'))
    .map((f) => f.replace('.json', ''))
    .sort();
}

export function getLatestDate(): string | null {
  const dates = getAvailableDailyDates();
  return dates.length > 0 ? dates[dates.length - 1] : null;
}

export function getLatestWeek(): string | null {
  const weeks = getAvailableWeeklyWeeks();
  return weeks.length > 0 ? weeks[weeks.length - 1] : null;
}

export function getAllArticleIds(): { id: string }[] {
  const dates = getAvailableDailyDates();
  const seen = new Set<string>();
  const ids: { id: string }[] = [];
  for (const date of dates) {
    const data = getDailyData(date);
    if (!data) continue;
    for (const cat of data.categories) {
      for (const article of cat.articles) {
        if (!seen.has(article.id)) {
          seen.add(article.id);
          ids.push({ id: article.id });
        }
      }
    }
  }
  return ids;
}

export function getArticleById(id: string): Article | null {
  const dates = getAvailableDailyDates();
  for (const date of dates) {
    const data = getDailyData(date);
    if (!data) continue;
    for (const cat of data.categories) {
      for (const article of cat.articles) {
        if (article.id === id) {
          return article;
        }
      }
    }
  }
  return null;
}
