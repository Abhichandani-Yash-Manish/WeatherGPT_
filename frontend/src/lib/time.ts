/* Time, always IST, always explicit. The engine states windows in IST labels and every retrieved
   value carries a UTC instant; the interface never re-derives a boundary, it formats what arrived.

   The CONVENTIONS it formats them in come from lib/locale.ts rather than from this file, and the default is
   the product's own: a Hindi, Gujarati or Tamil interface prints the locale's month, and an English one
   keeps printing what every recorded example in this repository already says. */

import { currentLocale, isDefaultLocale } from './locale';

/* The product's own three-letter months, kept for the default rendering alone. They are not a stand-in for
   Intl: they exist because "18 Sep 2026" is what this product's evidence, specs and documents state, and
   Intl's short month for en is "Sept" on the ICU this workspace runs. Every other locale reads Intl. */
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const IST = 'Asia/Kolkata';

export type IstParts = { day: string; month: string; year: string; hour: string; minute: string };

const dateFormats = new Map<string, Intl.DateTimeFormat>();
const monthFormats = new Map<string, Intl.DateTimeFormat>();

/* Formatters are kept: istStamp is called once per fact in a list, and constructing an Intl formatter per
   call is the expensive part of Intl. Keyed by locale, so a language change builds one each rather than
   reading a stale one. */
function dateFormat(locale: string): Intl.DateTimeFormat {
  let format = dateFormats.get(locale);
  if (!format) {
    format = new Intl.DateTimeFormat(locale, { timeZone: IST, day: '2-digit', month: 'short', year: 'numeric' });
    dateFormats.set(locale, format);
  }
  return format;
}

/* The month alone. Requesting month:'2-digit' alongside the others is what gives a numeric month, and a
   numeric month cannot be turned into another language's month name - so the name is read from Intl in the
   active locale, and the number is used only to index the product's own table for its default rendering. */
function monthFormat(locale: string): Intl.DateTimeFormat {
  let format = monthFormats.get(locale);
  if (!format) {
    format = new Intl.DateTimeFormat(locale, { timeZone: IST, month: 'short' });
    monthFormats.set(locale, format);
  }
  return format;
}

function parse(value?: string | number | null): Date | null {
  if (value === undefined || value === null || value === '') return null;
  const at = new Date(value);
  return Number.isNaN(at.getTime()) ? null : at;
}

function partsAt(at: Date): IstParts {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: IST,
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
    month: isDefaultLocale() ? MONTHS[Math.max(0, month - 1)] || pick('month') : monthFormat(currentLocale()).format(at),
    year: pick('year'),
    hour: pick('hour') === '24' ? '00' : pick('hour'),
    minute: pick('minute'),
  };
}

/* The day and the month name, for a caller that holds a month NUMBER rather than an instant (the edition
   labels come from a date-only string the publisher printed). Same table, same locale. */
export function monthName(month: number): string {
  /* A month that is not a month is answered with nothing, which every caller already treats as "the source
     did not state a usable date". Passing it to Intl instead would throw on an Invalid Date, and a crash on
     a malformed edition string is a worse answer than the raw string. */
  if (!Number.isFinite(month) || month < 1 || month > 12) return '';
  if (isDefaultLocale()) return MONTHS[month - 1];
  return monthFormat(currentLocale()).format(new Date(Date.UTC(2026, month - 1, 15)));
}

/* The date as one string. The default composes it from its own parts, so the output is byte-identical to
   what this product has always printed. Every other locale is given the browser's own composition, because
   a locale may separate the parts with something of its own - Gujarati writes a comma after the month - and
   assembling it here would silently drop that. */
function dateText(at: Date, parts: IstParts): string {
  if (isDefaultLocale()) return parts.day + ' ' + parts.month + ' ' + parts.year;
  return dateFormat(currentLocale()).format(at);
}

export function istParts(value?: string | number | null): IstParts | null {
  const at = parse(value);
  return at ? partsAt(at) : null;
}

export function istStamp(value?: string | number | null): string {
  const at = parse(value);
  if (!at) return 'Time not supplied';
  const parts = partsAt(at);
  return dateText(at, parts) + ', ' + parts.hour + ':' + parts.minute + ' IST';
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
  const fromAt = parse(start);
  const toAt = parse(end);
  if (!fromAt || !toAt) return 'Window not stated';
  const from = partsAt(fromAt);
  const to = partsAt(toAt);
  /* An hourly value carries the instant it is valid for, so start equals end. Printing that as
     '00:30-00:30' tells the reader nothing and reads as a zero-length window (measured 17 September
     2026: a whole day of hourly air-quality values was summarised as "18 Sep 2026 00:30-00:30 IST").
     One instant is printed as one instant. */
  if (istStamp(start) === istStamp(end)) return istStamp(start);
  if (from.day === to.day && from.month === to.month && from.year === to.year) {
    return dateText(fromAt, from) + ' ' + from.hour + ':' + from.minute + '-' + to.hour + ':' + to.minute + ' IST';
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
   time on a working turn only - never as a completion estimate.

   These are WORDS the interface wrote about itself, so they are a translation rather than a format and
   belong in a catalogue key. Left as English here deliberately: moving them is the call-site lane's work,
   and a half-moved string would be worse than an honest English one. */
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
