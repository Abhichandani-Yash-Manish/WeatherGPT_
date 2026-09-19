/* The actions a reader can take on a turn, and the text each one carries away.

   Copying a receipt is copying what it shows, in the order it shows it, so a pasted receipt cannot
   disagree with the card it came from. A download is a file the reader keeps; nothing here publishes
   anything, and no action sends evidence off this machine. */

import type { AnswerPacket, Fact } from '../api/types';
import { istStamp, istWindow } from '../lib/time';
import { EVIDENCE_KINDS, placeOf, parameterName } from './model';

export function kindOf(fact: Fact): string {
  const kind = fact.evidence_kind || '';
  return EVIDENCE_KINDS[kind] || (kind ? kind.replace(/_/g, ' ') : '');
}

export function receiptRows(packet: AnswerPacket, fact: Fact): [string, string][] {
  const citation = (packet.citations || []).find(entry => (fact.citation_ids || []).includes(entry.id));
  /* The engine states a locator either as an object with page/row/column or as the plain path it read from
     ("$.hourly.precipitation[26]"). Both are the record locator, so both are printed. */
  const locator = (fact.source_locators || [])[0] as
    | { page?: number | string; row?: number | string; column?: string; prefix?: string; locator?: string }
    | string
    | undefined;
  const rows: [string, string][] = [];
  rows.push(['Measure', parameterName(fact) + (fact.parameter ? ' (' + fact.parameter + ')' : '')]);
  rows.push(['Value', String(fact.value) + (fact.unit ? ' ' + fact.unit : '') + (fact.method ? ' \u00b7 method ' + fact.method : '')]);
  rows.push(['Place', placeOf(packet, fact) || 'not recorded']);
  if (fact.entity_id) rows.push(['Entity', fact.entity_id]);
  rows.push(['Window', fact.start && fact.end ? istWindow(String(fact.start), String(fact.end)) : fact.observed_at ? istWindow(String(fact.observed_at), String(fact.observed_at)) : 'not recorded']);
  if (fact.observed_at) rows.push(['Observed', istStamp(fact.observed_at)]);
  rows.push(['Evidence', kindOf(fact) || 'not recorded']);
  rows.push(['Source', fact.source_id || citation?.source_id || 'not recorded']);
  if (citation?.product) rows.push(['Source product', citation.product]);
  if (citation?.retrieved_at_utc) rows.push(['Retrieved', istStamp(citation.retrieved_at_utc)]);
  if (citation?.url) rows.push(['Address', citation.url]);
  if (typeof locator === 'string') {
    if (locator.trim()) rows.push(['Locator', locator.trim()]);
  } else if (locator) {
    const parts = [
      locator.page ? 'page ' + locator.page : null,
      locator.row ? 'row ' + locator.row : null,
      locator.column || locator.prefix || locator.locator || null,
    ].filter(Boolean);
    if (parts.length) rows.push(['Locator', parts.join(' \u00b7 ')]);
  }
  if (fact.evidence_version) rows.push(['Evidence id', String(fact.evidence_version).slice(0, 16) + '\u2026']);
  if (fact.task_id) rows.push(['Task', fact.task_id]);
  return rows;
}

export function receiptText(packet: AnswerPacket, fact: Fact): string {
  const lines = ['WeatherGPT evidence receipt', 'Question: ' + packet.question, 'Answered: ' + istStamp(packet.answered_at_utc), ''];
  receiptRows(packet, fact).forEach(([key, value]) => lines.push(key + ': ' + value));
  const source = (packet.citations || []).find(entry => (fact.citation_ids || []).includes(entry.id));
  lines.push('');
  lines.push(
    'Chain: ' + (fact.source_id || 'source not stated') + ' \u2192 retrieved ' +
    (source?.retrieved_at_utc ? istStamp(source.retrieved_at_utc) : 'time not recorded') + ' \u2192 ' +
    (fact.method || kindOf(fact) || 'typed contract'),
  );
  lines.push('A receipt for the moment it was retrieved, not a standing fact. Model output is not an observation and not a district average.');
  return lines.join('\n');
}

/* One claim as a line of text, for a reader who has to send it to somebody else.
   ============================================================================
   The claim is the atom — a measure, a value with its unit, a place, a window and a source — so the line is
   those things in that order and nothing else. No headings, no prose, no confidence: what is copied is what
   the card states, and the card states only what a tool returned. */
export function claimLine(packet: AnswerPacket, fact: Fact): string {
  const window = fact.start && fact.end ? istWindow(String(fact.start), String(fact.end))
    : fact.observed_at ? istWindow(String(fact.observed_at), String(fact.observed_at)) : null;
  const parts = [
    parameterName(fact) || fact.label || 'a measure',
    String(fact.value) + (fact.unit ? ' ' + fact.unit : ''),
    placeOf(packet, fact),
    window,
    fact.source_id ? 'source ' + fact.source_id : null,
    kindOf(fact) || null,
  ];
  return parts.filter(Boolean).join(' · ');
}

export function answerText(packet: AnswerPacket): string {
  return ['Question: ' + packet.question, 'Answered: ' + istStamp(packet.answered_at_utc), 'Status: ' + packet.status, '', packet.answer].join('\n');
}

export function markdownTurn(packet: AnswerPacket): string {
  const lines = ['# ' + packet.question, '', packet.answer, ''];
  const facts = packet.facts || [];
  if (facts.length) {
    lines.push('| Measure | Value | Place | Window | Source |', '| --- | --- | --- | --- | --- |');
    facts.forEach(fact => {
      const window = fact.start && fact.end ? istWindow(String(fact.start), String(fact.end)) : fact.observed_at ? istWindow(String(fact.observed_at), String(fact.observed_at)) : 'not recorded';
      lines.push('| ' + parameterName(fact) + ' | ' + String(fact.value) + (fact.unit ? ' ' + fact.unit : '') + ' | ' + (placeOf(packet, fact) || 'not recorded') + ' | ' + window + ' | ' + (fact.source_id || 'not recorded') + ' |');
    });
    lines.push('');
  }
  (packet.notes || []).forEach(note => lines.push('> ' + note));
  lines.push('', '_Status: ' + packet.status + ' \u00b7 answered ' + istStamp(packet.answered_at_utc) + '_');
  return lines.join('\n');
}

export function downloadFile(filename: string, text: string, kind = 'text/plain'): void {
  const blob = new Blob([text], { type: kind + ';charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 4000);
}

export function stampName(prefix: string, extension: string): string {
  return prefix + '-' + new Date().toISOString().replace(/[:.]/g, '-') + '.' + extension;
}

export async function copyText(text: string): Promise<'copied' | 'unsupported'> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return 'copied';
    }
  } catch {
    /* the permission or the browser refused: the caller says so rather than claiming a copy */
  }
  return 'unsupported';
}
