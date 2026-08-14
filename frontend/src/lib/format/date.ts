export function getTodayYMD(timeZone = 'America/Santiago'): string {
  const now = new Date();
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  return fmt.format(now); // YYYY-MM-DD
}

export function formatLocalDate(
  dateStr: string,
  timeZone = 'America/Santiago',
  locale = 'es-CL'
): string {
  if (!dateStr) return '';
  const parts = dateStr.split('-').map(Number);
  if (parts.length !== 3) return dateStr;
  // Construct UTC noon date to prevent day shifting across timezones
  const date = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2], 12, 0, 0));
  return new Intl.DateTimeFormat(locale, {
    timeZone,
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(date);
}

export function formatTimeRange(
  startsAtISO: string,
  endsAtISO: string,
  timeZone = 'America/Santiago',
  locale = 'es-CL'
): string {
  if (!startsAtISO || !endsAtISO) return '';
  const start = new Date(startsAtISO);
  const end = new Date(endsAtISO);
  const timeFmt = new Intl.DateTimeFormat(locale, {
    timeZone,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
  return `${timeFmt.format(start)} – ${timeFmt.format(end)}`;
}

export function formatTimeSlot(
  isoString: string,
  timeZone = 'America/Santiago',
  locale = 'es-CL'
): string {
  if (!isoString) return '';
  const date = new Date(isoString);
  return new Intl.DateTimeFormat(locale, {
    timeZone,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date);
}

export function getSlotHourInTimezone(
  isoString: string,
  timeZone = 'America/Santiago'
): number {
  const date = new Date(isoString);
  const hourStr = new Intl.DateTimeFormat('en-US', {
    timeZone,
    hour: 'numeric',
    hour12: false,
  }).format(date);
  return parseInt(hourStr, 10);
}

export interface UpcomingDateItem {
  dateStr: string;
  label: string;
  sublabel: string;
}

export function getUpcomingDatesInTimezone(
  daysCount: number,
  timeZone = 'America/Santiago',
  locale = 'es-CL',
  nowDate: Date = new Date()
): UpcomingDateItem[] {
  const dates: UpcomingDateItem[] = [];

  // Determine current civil year, month, day in target timeZone
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
  }).formatToParts(nowDate);

  let year = 0;
  let month = 0;
  let day = 0;

  for (const p of parts) {
    if (p.type === 'year') year = parseInt(p.value, 10);
    if (p.type === 'month') month = parseInt(p.value, 10);
    if (p.type === 'day') day = parseInt(p.value, 10);
  }

  // Base UTC midnight representing local day 0
  const baseUtc = Date.UTC(year, month - 1, day, 12, 0, 0);

  for (let i = 0; i < daysCount; i++) {
    const d = new Date(baseUtc + i * 86400000);
    const yStr = d.getUTCFullYear();
    const mStr = String(d.getUTCMonth() + 1).padStart(2, '0');
    const dStr = String(d.getUTCDate()).padStart(2, '0');
    const dateStr = `${yStr}-${mStr}-${dStr}`;

    let label: string;
    if (i === 0) label = 'Hoy';
    else if (i === 1) label = 'Mañana';
    else {
      label = new Intl.DateTimeFormat(locale, { timeZone: 'UTC', weekday: 'short' }).format(d);
    }

    const sublabel = `${d.getUTCDate()} ${new Intl.DateTimeFormat(locale, {
      timeZone: 'UTC',
      month: 'short',
    }).format(d)}`;

    dates.push({ dateStr, label, sublabel });
  }

  return dates;
}

export function formatCivilDateInTimezone(date: Date, timeZone = 'America/Santiago'): string {
  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  const parts = formatter.formatToParts(date);
  const year = parts.find((p) => p.type === 'year')?.value;
  const month = parts.find((p) => p.type === 'month')?.value;
  const day = parts.find((p) => p.type === 'day')?.value;
  if (!year || !month || !day) {
    throw new Error(`Unable to extract civil date parts for timezone ${timeZone}`);
  }
  return `${year}-${month}-${day}`;
}
