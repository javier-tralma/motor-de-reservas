import type { AdminAvailabilityRuleItem } from '../api/admin';

export function normalizeIntervals(rules: AdminAvailabilityRuleItem[]): AdminAvailabilityRuleItem[] {
  const byWeekday = new Map<number, AdminAvailabilityRuleItem[]>();
  for (const item of rules) {
    const list = byWeekday.get(item.weekday) || [];
    // Ensure seconds are included if only HH:MM
    const st = item.start_time.length === 5 ? `${item.start_time}:00` : item.start_time;
    const et = item.end_time.length === 5 ? `${item.end_time}:00` : item.end_time;
    list.push({ weekday: item.weekday, start_time: st, end_time: et });
    byWeekday.set(item.weekday, list);
  }

  const result: AdminAvailabilityRuleItem[] = [];
  for (const [, dayRules] of byWeekday.entries()) {
    dayRules.sort((a, b) => a.start_time.localeCompare(b.start_time));
    const merged: AdminAvailabilityRuleItem[] = [];
    for (const rule of dayRules) {
      if (merged.length === 0) {
        merged.push({ ...rule });
      } else {
        const last = merged[merged.length - 1];
        // If adjacent (last.end_time === rule.start_time), merge them
        if (last.end_time === rule.start_time) {
          last.end_time = rule.end_time;
        } else {
          merged.push({ ...rule });
        }
      }
    }
    result.push(...merged);
  }
  result.sort((a, b) => a.weekday - b.weekday || a.start_time.localeCompare(b.start_time));
  return result;
}

export function getInitialLocalDate(timeZone: string = 'America/Santiago', date: Date = new Date()): string {
  try {
    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
    const parts = formatter.formatToParts(date);
    const year = parts.find((p) => p.type === 'year')?.value;
    const month = parts.find((p) => p.type === 'month')?.value;
    const day = parts.find((p) => p.type === 'day')?.value;
    if (year && month && day) {
      return `${year}-${month}-${day}`;
    }
  } catch {
    // fallback if invalid timezone
  }
  return date.toISOString().split('T')[0];
}
