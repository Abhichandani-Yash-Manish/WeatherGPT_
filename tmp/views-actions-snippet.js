
/* The point an answer was resolved to, if it has one: the drawers need coordinates, never a guess. */
function resolvedPlace(packet) {
  const points = packet.resolved_points || {};
  const names = Object.keys(points);
  if (!names.length) return null;
  const entry = points[names[0]] || {};
  const coordinates = entry.coordinates || {};
  if (coordinates.latitude === undefined || coordinates.longitude === undefined) return null;
  return { label: entry.label || names[0], latitude: coordinates.latitude, longitude: coordinates.longitude };
}
/* The published advisory this turn read, as the route that composes a brief wants it. */
function advisoryBriefParams(packet) {
  const tasks = ((packet.plan || {}).tasks) || [];
  const task = tasks.filter(item => item.kind === 'agriculture' && item.document_request)[0]
    || ((packet.task_results || []).filter(item => (item.request || {}).document_request)[0] || {}).request;
  if (!task || !task.document_request) return null;
  const request = task.document_request;
  const passage = (packet.passages || [])[0] || {};
  const evidence = (packet.document_evidence || [])[0] || {};
  const region = passage.district || evidence.district || '';
  if (!region) return null;
  return { region: region, state: passage.state || evidence.state || '', crop: request.crop || '',
           stage: request.growth_stage || '', topic: request.topic || 'general',
           mode: request.mode || 'source_lookup', day: 1 };
}
