
/* ---------- what was retrieved, and what is still needed ---------- */
/* retrieval_coverage, pending_slots, edition_comparison and document_evidence are records the
   tools produce; until this renderer existed they were only visible in the raw packet. Nothing
   here computes anything: every number is the tool's own, and an absence is shown as an absence. */
const CURRENCY_WORDS = {
  printed_issue_matches_retrieval_date: 'the printed issue date is the retrieval date',
  printed_issue_differs_from_retrieval_date: 'the printed issue is older than the retrieval date',
  printed_issue_not_stated: 'the document states no printed issue date, so its currency is unknown',
  printed_issue_in_the_future: 'the printed issue date is later than the retrieval date'
};
function renderRetrievalAccount(packet) {
  const slots = packet.pending_slots || [];
  const coverage = packet.retrieval_coverage || [];
  const comparison = packet.edition_comparison || null;
  const editions = packet.document_evidence || [];
  if (!slots.length && !coverage.length && !comparison && !editions.length) return null;
  const box = el('section', undefined, 'receipt');
  box.append(el('p', 'What was retrieved, and what is missing', 'receipt-title'));
  if (slots.length) {
    box.append(el('p', 'Still needed before this can be answered', 'field-label'));
    const list = el('ul', undefined, 'notes');
    slots.forEach(slot => list.append(el('li', String(slot.field || 'a field') + ': ' + String(slot.reason || 'not stated')
      + (slot.task_id ? ' (task ' + String(slot.task_id) + ')' : ''))));
    box.append(list);
  }
  if (coverage.length) {
    coverage.forEach(entry => {
      const filters = entry.filters || {};
      const rows = [
        ['Search mode', String(entry.mode || 'not stated'), 'the retriever this turn used'],
        ['Candidates → returned', String(entry.candidates === undefined ? 'not stated' : entry.candidates) + ' → ' + String(entry.returned === undefined ? 'not stated' : entry.returned),
          entry.lexical_overlap_required ? 'a passage must share words with the question to be returned' : 'no lexical overlap required'],
        ['Product filters', [filters.family, filters.scope, filters.region].filter(Boolean).join(' · ') || 'none', 'family, scope and region as stored'],
        ['Whole document asked for', entry.whole_document ? 'yes' : 'no', 'a whole-edition read returns the document as a record'],
        ['Editions indexed for this product', String(entry.editions_indexed_for_this_product === undefined ? 'not stated' : entry.editions_indexed_for_this_product),
          'a single indexed edition cannot be compared with another']
      ];
      box.append(table(['Field', 'Value', 'Provenance'], rows));
    });
  }
  if (comparison) {
    box.append(el('p', 'Editions in the index', 'field-label'));
    box.append(table(['Field', 'Value', 'Provenance'], [
      ['Editions indexed', String(comparison.editions_indexed === undefined ? 'not stated' : comparison.editions_indexed), String(comparison.state || 'state not stated')],
      ['Newest printed issue', String(comparison.newest_issue || 'not stated'), 'read from the document, never from the retrieval instant'],
      ['Previous printed issue', String(comparison.previous_issue || 'none indexed'), 'differences are labelled and never ranked']
    ]));
  }
  if (editions.length) {
    box.append(el('p', 'Editions read', 'field-label'));
    box.append(table(['Edition', 'Region', 'Printed issue', 'Currency and age'], editions.map(item => [
      String(item.family_label || item.family || 'document') + ' (' + String(item.source_id || 'source not stated') + ')',
      [item.region, item.state].filter(Boolean).join(', ') || String(item.scope || 'not stated'),
      String(item.issue_date || 'not stated') + (item.issue_date && item.issue_date_basis ? ' (' + String(item.issue_date_basis) + ')' : ''),
      (CURRENCY_WORDS[item.currency] || String(item.currency || 'currency not stated')) +
        (item.age_days === undefined || item.age_days === null ? '' : ', ' + String(item.age_days) + ' day(s) old at retrieval')
    ])));
  }
  return box;
}
