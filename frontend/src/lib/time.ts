/* Time, always IST, always explicit. The engine states windows in IST labels and every retrieved
   value carries a UTC instant; the interface never re-derives a boundary, it formats what arrived. */

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export type IstParts = { day: string; month: string; year: string; hour: string; minute: string };

export function istParts(value?: string | number | null): IstParts | null {
  if (value === undefined || value === null || value === '') return null;
  const at = new Date(value);
  if (Number.isNaN(at.getTime())) return null;
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(at);
  const pick = (type: string) => parts.find(part => part.type === type)?.value || '';
  const month = Number(pick('month'));
  return {
    day: pick('day'),
    month: MONTHS[Math.max(0, month - 1)] || pick('month'),
    year: pick('year'),
    hour: pick('hour') === '24' ? '00' : pick('hour'),
    minute: pick('minute'),
  };
}

export function istStamp(value?: string | number | null): string {
  const parts = istParts(value);
  if (!parts) return 'Time not supplied';
  return parts.day + ' ' + parts.month + ' ' + parts.year + ', ' + parts.hour + ':' + parts.minute + ' IST';
}

export function istClock(value?: string | number | null): string {
  const parts = istParts(value);
  return parts ? parts.hour + ':' + parts.minute : '';
}

export function istDay(value?: string | number | null): string {
  const parts = istParts(value);
  return parts ? parts.day + ' ' + parts.month : '';
}

/* A window as the engine states it: two IST instants, one line. Never a duration we computed. */
export function istWindow(start?: string | null, end?: string | null): string {
  if (!start || !end) return 'Window not stated';
  const from = istParts(start);
  const to = istParts(end);
  if (!from || !to) return 'Window not stated';
  /* An hourly value carries the instant it is valid for, so start equals end. Printing that as
     '00:30-00:30' tells the reader nothing and reads as a zero-length window (measured 17 September
     2026: a whole day of hourly air-quality values was summarised as "18 Sep 2026 00:30-00:30 IST").
     One instant is printed as one instant. */
  if (istStamp(start) === istStamp(end)) return istStamp(start);
  if (from.day === to.day && from.month === to.month && from.year === to.year) {
    return from.day + ' ' + from.month + ' ' + from.year + ' ' + from.hour + ':' + from.minute + '-' + to.hour + ':' + to.minute + ' IST';
  }
  return istStamp(start).replace(' IST', '') + '-' + istStamp(end);
}

export function secondsSince(iso?: string | null, now = Date.now()): number | null {
  if (!iso) return null;
  const at = new Date(iso).getTime();
  if (Number.isNaN(at)) return null;
  return Math.max(0, Math.round((now - at) / 1000));
}

/* A count of seconds as words a reader can hold: 12 s, 4 min 30 s, 1 h 12 min. Used for elapsed
   time on a working turn only — never as a completion estimate. */
export function elapsedWords(seconds?: number | null): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return 'time not recorded';
  const whole = Math.max(0, Math.round(seconds));
  if (whole < 60) return whole + ' s';
  const minutes = Math.floor(whole / 60);
  const rest = whole % 60;
  if (minutes < 60) return rest ? minutes + ' min ' + rest + ' s' : minutes + ' min';
  const hours = Math.floor(minutes / 60);
  const restMinutes = minutes % 60;
  return restMinutes ? hours + ' h ' + restMinutes + ' min' : hours + ' h';
}
