
// 0. The retrieval account: coverage, pending slots and the editions read are rendered from the
//    tool's own record. A bare `table(...)` call here threw 'table is not defined' in the page on
//    15 September 2026 and stopped the whole turn from rendering, so this check exists.
(function () {
  const packet = {
    status: 'answered', answer: 'A passage was returned.', facts: [], citations: [], notes: [], choices: [],
    plan: { language: 'en' }, task_results: [], task_coverage: { incomplete_ids: [] },
    pending_slots: [{ field: 'growth_stage', reason: 'Crop growth stage is not yet supplied', task_id: 't1' }],
    retrieval_coverage: [{ mode: 'whole_document_bm25_plus_dense_rrf', candidates: 48, returned: 10,
                           whole_document: false, editions_indexed_for_this_product: 1,
                           lexical_overlap_required: true, filters: { family: 'national_bulletin', scope: 'national', region: null } }],
    edition_comparison: { editions_indexed: 1, newest_issue: '2026-09-14', previous_issue: null, state: 'single_edition_indexed' },
    document_evidence: [{ family_label: 'All India Weather Summary and Forecast Bulletin', source_id: 'S64',
                          scope: 'national', issue_date: '2026-09-14', issue_date_basis: 'printed',
                          currency: 'printed_issue_matches_retrieval_date', age_days: 0 }]
  };
  const card = context.renderTurn(packet, {});
  const text = textOf(card);
  assert.ok(text.indexOf('What was retrieved, and what is missing') >= 0, 'the account is rendered');
  assert.ok(text.indexOf('growth_stage: Crop growth stage is not yet supplied') >= 0, 'a pending slot is named with its reason');
  assert.ok(text.indexOf('48 -> 10') >= 0, 'candidates and returned passages are both shown');
  assert.ok(text.indexOf('single_edition_indexed') >= 0, 'the edition-comparison state is shown');
  assert.ok(text.indexOf('the printed issue date is the retrieval date') >= 0, 'currency is shown in words');
})();
