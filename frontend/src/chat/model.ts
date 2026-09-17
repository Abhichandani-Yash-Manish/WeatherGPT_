/* The transcript's model: what a turn is, and the rules that decide what a card may show.

   These constants are ported from the vanilla transcript (web/views.js) one-for-one, because the
   wording a reader has already been shown is part of the product, not a detail of its markup. */

import type { AnswerPacket, Calculation, ChatPreview, ChatProgress, Fact, ResolvedPoint } from '../api/types';
import { istWindow } from '../lib/time';

export const STATUS_LABELS: Record<string, string> = {
  answered: 'Evidence retrieved',
  partial: 'Partly answered',
  needs_selection: 'Choose a place',
  needs_clarification: 'One more detail',
  unavailable: 'Evidence gap',
  explanation: 'General explanation',
  outside_validity: 'Choose an upcoming window',
  stale: 'Evidence expired',
  degraded: 'Refresh incomplete',
  prototype_answer: 'Forecast available',
  conversation: 'Conversational reply',
  cancelled: 'Stopped at a task boundary',
};

/* Statuses where the workspace is telling the reader it could not answer as asked. The tag is set
   apart so a held answer cannot be mistaken for evidence. */
export const HELD_STATUS = ['needs_selection', 'needs_clarification', 'unavailable', 'outside_validity', 'stale', 'partial', 'degraded', 'cancelled'];

export const EVIDENCE_KINDS: Record<string, string> = {
  forecast: 'Model forecast',
  observation: 'Observation',
  reanalysis: 'Modeled reanalysis',
  air_quality_model: 'Modelled air quality',
  advisory: 'Source advisory',
  reference: 'Reference only',
  context: 'Source context',
};

export const PARAMETER_NAMES: Record<string, string> = {
  precipitation: 'precipitation',
  precipitation_probability: 'rain probability',
  temperature_2m: 'temperature',
  temperature_c: 'temperature',
  relative_humidity_2m: 'humidity',
  wind_speed_10m: 'wind speed',
  wind_speed_kt: 'wind speed',
  rainfall: 'rainfall',
  wave_height: 'significant wave height',
  wave_direction: 'wave direction',
  wave_period: 'wave period',
  discharge: 'river discharge',
  river_discharge: 'river discharge',
  official_district_warning: 'official district warning',
  pm2_5: 'PM2.5',
  us_aqi: 'US AQI',
};

export const LANGUAGE_NAMES: Record<string, string> = { en: 'English', hi: 'Hindi', gu: 'Gujarati' };

/* The warning parameter is drawn by the warning strip, never as an ordinary fact row: it is an
   official statement with hazards and a validity window, not a measurement of ours. */
export const WARNING_PARAMETERS = new Set(['official_district_warning']);

export function coverageFacts(packet: AnswerPacket): Fact[] {
  return (packet.facts || []).filter(fact => fact.value !== undefined && fact.value !== null && fact.value !== '');
}

export function warningFacts(packet: AnswerPacket): Fact[] {
  return coverageFacts(packet).filter(fact => WARNING_PARAMETERS.has(fact.parameter));
}

export function chartEvidenceIds(packet: AnswerPacket): Set<string> {
  const ids = new Set<string>();
  (packet.charts || []).forEach(chart => {
    (chart.points || []).forEach(point => {
      const id = (point as { evidence_id?: string }).evidence_id;
      if (id) ids.add(id);
    });
  });
  return ids;
}

export function sequenceFacts(packet: AnswerPacket): Fact[] {
  const plotted = chartEvidenceIds(packet);
  return coverageFacts(packet).filter(fact => !plotted.has(fact.id) && !WARNING_PARAMETERS.has(fact.parameter));
}

export function windowFacts(packet: AnswerPacket): Fact[] {
  return coverageFacts(packet).filter(
    fact => Boolean(fact.start && fact.end) && Date.parse(String(fact.start)) < Date.parse(String(fact.end)),
  );
}

export function kindOf(fact?: Fact | null): string {
  if (!fact) return '';
  const kind = fact.evidence_kind || '';
  return EVIDENCE_KINDS[kind] || (kind ? kind.replace(/_/g, ' ') : '');
}

export function parameterName(fact?: Fact | null): string {
  if (!fact) return 'Answer';
  return fact.label || PARAMETER_NAMES[fact.parameter] || fact.parameter || 'Answer';
}

/* The engine states a calculation's kind in its own fields; where it states only the operation or the
   method, that is rendered rather than a category invented here. A source comparison is always named as a
   difference, because that is what it is. */
export function calculationKind(calculation: Calculation): string {
  if (calculation.kind === 'source_comparison') return 'Difference between sources';
  if (calculation.operation === 'linear_trend') return 'Descriptive trend';
  if (calculation.operation === 'difference') return 'Difference';
  if (calculation.method && /sum/i.test(calculation.method)) return 'Deterministic total';
  return calculation.operation || calculation.kind || 'Computed value';
}

/* True when the payload carries at least one district warning day, which the warning panel renders. A
   warning fact without a day row keeps the plain warning block instead of being dropped. */
export function hasWarningDays(packet: AnswerPacket): boolean {
  return (packet.warning_evidence || []).some(entry => (entry.district_warnings || []).length > 0);
}

export function placeOf(packet: AnswerPacket, fact?: Fact | null): string | null {
  if (fact?.place) return fact.place;
  const resolved = packet.resolved_points || {};
  const key = Object.keys(resolved)[0];
  if (!key) return null;
  return resolved[key].label || resolved[key].name || key;
}

/* The window a fact covers, in the engine's own IST label. Never a duration we computed. */
export function hourLabel(fact?: Fact | null): string {
  if (!fact) return '';
  if (fact.observed_at) return istWindow(String(fact.observed_at), String(fact.observed_at));
  if (fact.start && fact.end) return istWindow(String(fact.start), String(fact.end));
  if (fact.sample_at) return istWindow(String(fact.sample_at), String(fact.sample_at));
  return '';
}

export function firstPoint(packet: AnswerPacket): { latitude: number; longitude: number; label: string } | null {
  const resolved: Record<string, ResolvedPoint> = packet.resolved_points || {};
  for (const [name, point] of Object.entries(resolved)) {
    const latitude = point.coordinates?.latitude ?? point.latitude;
    const longitude = point.coordinates?.longitude ?? point.longitude;
    if (typeof latitude === 'number' && typeof longitude === 'number') {
      return { latitude, longitude, label: point.label || name };
    }
  }
  return null;
}

export function languageRequested(packet: AnswerPacket): string | null {
  const plan = packet.plan as { language?: string } | null | undefined;
  const declared = plan?.language;
  const generated = packet.trace?.generation?.requested_language;
  const chosen = generated || declared;
  return chosen && chosen !== 'en' ? chosen : null;
}

export function languageDowngradeNote(packet: AnswerPacket): string | null {
  return (packet.notes || []).find(note => /output language could not be rendered/i.test(note)) || null;
}

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] || status.replace(/_/g, ' ');
}

export function isHeld(status: string): boolean {
  return HELD_STATUS.includes(status);
}

export function turnTitle(packet: AnswerPacket): string {
  if (packet.status === 'conversation') return 'Conversation';
  if (packet.status === 'needs_selection') return 'Which place do you mean?';
  if (packet.status === 'needs_clarification') return 'One more detail needed';
  if (packet.status === 'unavailable') return 'No verified evidence for this';
  if (packet.status === 'outside_validity') return 'That window is not available';
  if (packet.status === 'explanation') return 'General explanation';
  if (packet.status === 'cancelled') return 'Stopped';
  if ((packet.airport_reports || []).length) return 'Airport report';
  if ((packet.charts || []).length) return 'Retrieved series';
  return 'Answer';
}

/* What the turn did not do, stated in the answer itself rather than only in a disclosure. If every
   requested task completed, there is nothing to add. */
export function coverageNote(packet: AnswerPacket): string | null {
  const coverage = packet.task_coverage;
  if (!coverage) return null;
  if (coverage.requested > 0 && coverage.completed >= coverage.requested) return null;
  if (!coverage.requested) return null;
  return (
    coverage.completed + ' of ' + coverage.requested + ' requested task' + (coverage.requested === 1 ? '' : 's') +
    ' completed in this turn' + (coverage.incomplete_ids?.length ? '; ' + coverage.incomplete_ids.length + ' left incomplete and named below' : '') + '.'
  );
}

/* The reading line the working turn shows while the answer is still being retrieved. It carries the
   engine's own wording, marks itself provisional, and states no value. */
export function readingLine(preview: ChatPreview | null): string | null {
  if (!preview || preview.provisional === false) return null;
  const line = (preview.reading as { line?: string } | null | undefined)?.line;
  return typeof line === 'string' && line.trim() ? line.trim() : null;
}

export function stageWords(progress: ChatProgress | null): string {
  if (!progress) return 'Reading the question';
  if (progress.queue && progress.queue.waiting > 0 && progress.state !== 'working') {
    return 'Waiting for the queue (' + progress.queue.waiting + ' ahead)';
  }
  return progress.stage_label || 'Reading the question';
}

/* What the server is doing now. These are checkpoints the engine reports, not a completion estimate:
   nothing here can be turned into a percentage, an ETA or a confidence score. */
export const STAGE_LABELS: Record<string, string> = {
  started: 'Reading the question',
  planned: 'Planning the tasks',
  resolving: 'Resolving the place',
  retrieving: 'Retrieving evidence',
  assembling: 'Assembling the answer',
  finalising: 'Final check',
  'task boundary': 'Stopping at the task boundary',
};

export function stageLabel(stage?: string | null): string {
  if (!stage) return 'Reading the question';
  return STAGE_LABELS[stage] || stage;
}

/* ---- turns --------------------------------------------------------------------------------- */

export type UserTurn = { key: string; role: 'user'; text: string; at: string };
export type AnswerTurn = { key: string; role: 'answer'; packet: AnswerPacket; at: string; restored?: boolean };
export type NoticeTurn = { key: string; role: 'notice'; tone: 'calm' | 'error'; text: string; at: string };
/* A restored transcript is the stored sentence, not a receipt: the engine keeps the text of past turns
   and a restored turn says so rather than pretending to be a freshly retrieved answer. */
export type RestoredTurn = { key: string; role: 'restored'; text: string; at: string };

export type Turn = UserTurn | AnswerTurn | NoticeTurn | RestoredTurn;

export type Working = {
  key: string;
  requestId: string;
  question: string;
  startedAt: number;
  preview: ChatPreview | null;
  previewFailed: string | null;
  progress: ChatProgress | null;
  stopRequested: boolean;
  stopDetail: string | null;
};

/* The register a reader chooses. It changes how much of the evidence is unfolded on a card; it never
   changes a value, a source or a warning level, and the transcript's default is conversational. */
export type Register = 'brief' | 'conversational' | 'full';
export const REGISTER_KEY = 'weathergpt.register';
export const REGISTER_ORDER: Register[] = ['brief', 'conversational', 'full'];

export function readRegister(): Register {
  try {
    const stored = window.localStorage.getItem(REGISTER_KEY);
    if (stored === 'brief' || stored === 'conversational' || stored === 'full') return stored;
  } catch {
    /* a browser that refuses storage keeps the default */
  }
  return 'conversational';
}

export function writeRegister(register: Register): void {
  try {
    window.localStorage.setItem(REGISTER_KEY, register);
  } catch {
    /* the choice simply does not survive this session */
  }
}
