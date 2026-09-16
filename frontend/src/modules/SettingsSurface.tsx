/* Sources and settings: what the suite can answer, which sources it uses, who answers and in what
   order, and the state of the local store, the watch loop and the briefcase. Every provider row
   states its own availability, and a provider that is not configured says so in its own words. */
import { useQuery } from '@tanstack/react-query';
import { getJson } from '../api/client';
import type { Briefs, CapabilitiesData, Envelope, Health, WatchHealth } from '../api/types';
import { count, orNot } from '../lib/format';
import { istStamp } from '../lib/time';
import { viewById } from '../shell/views';
import { DataTable, Failure, Facts, NO_ROW, NOT_RECORDED, Reading, SurfaceShell } from './Evidence';

export const intents: string[] = (viewById('settings')?.intents ?? []).concat([
  'What is the state of the local store and the watch loop?', 'Which briefs are kept in the local briefcase?',
]);

function availability(value?: boolean): string {
  if (value === true) return 'available';
  if (value === false) return 'not available';
  return 'availability not recorded';
}

function providerState(row: { provider?: string; model?: string | null; models?: string[]; available?: boolean; reason?: string }): string[] {
  return [orNot(row.provider, 'provider not named'), availability(row.available),
          orNot(row.model || (row.models || []).join(', '), 'no model named') + (row.reason ? ' · ' + row.reason : ' · no reason returned')];
}

export function Surface(): JSX.Element {
  const capabilities = useQuery({
    queryKey: ['settings-capabilities'],
    queryFn: () => getJson<Envelope<CapabilitiesData>>('/api/settings/capabilities'),
    retry: false,
  });
  const health = useQuery({ queryKey: ['settings-health'], queryFn: () => getJson<Health>('/api/health'), retry: false });
  const watches = useQuery({ queryKey: ['settings-watch-health'], queryFn: () => getJson<WatchHealth>('/api/watch-health'), retry: false });
  const briefs = useQuery({ queryKey: ['settings-briefs'], queryFn: () => getJson<Briefs>('/api/briefs'), retry: false });

  const data = capabilities.data?.data;
  const provider = data?.provider;
  const tick = watches.data?.tick;

  return (
    <SurfaceShell
      title="Sources and settings"
      lead="What this suite can answer, which sources its adapters use, which model providers are configured, and the state of the local store, the watch loop and the briefcase. Nothing here is a serving approval."
      what="the capability and settings reads"
      envelope={capabilities.data}
      busy={capabilities.isPending}
      error={capabilities.error}
      onRetry={() => capabilities.refetch()}
    >
      <section className="module-section">
        <h2>What this suite can answer</h2>
        <p className="module-note">
          {count(data?.capabilities?.length, 'capability', 'capabilities')} this read returned · {orNot(data?.registered_sources)} registered sources ·{' '}
          {orNot(data?.connected_sources)} connected sources as this read counts them
        </p>
        <DataTable
          testId="settings-capabilities"
          caption="One row per capability the read returned."
          columns={['Tool', 'Kind', 'Operations', 'Stated purpose']}
          rows={(data?.capabilities || []).map(capability => [
            orNot(capability.tool),
            orNot(capability.kind),
            capability.operations?.length ? capability.operations.join(', ') : NOT_RECORDED,
            orNot(capability.purpose),
          ])}
        />
      </section>

      <section className="module-section">
        <h2>Sources in use</h2>
        <p className="module-note">
          The registry rows these capabilities name, not the provenance of this read: the read's own envelope attached no source row.
        </p>
        <DataTable
          testId="settings-sources"
          caption="One row per source used by a capability, as the registry records it."
          columns={['Source', 'Product', 'Integration status', 'User review', 'Usage terms']}
          rows={(data?.sources || []).map(source => [
            orNot(source.source_id),
            orNot(source.product),
            orNot(source.integration_status),
            orNot(source.user_review),
            orNot(source.usage_terms),
          ])}
        />
      </section>

      <section className="module-section">
        <h2>Model providers</h2>
        <p className="module-note">
          Each provider row states its own availability, and a provider that is not configured says so in its own words.
        </p>
        <DataTable
          testId="settings-providers"
          caption="Every provider the read returned, with the state it states for itself."
          columns={['Provider', 'State', 'Detail as returned']}
          rows={[
            ...(provider?.providers || []).map(providerState),
            ['Planner policy', orNot(provider?.planner_policy), 'the policy in force for this workspace'],
            ['Chat router', provider?.chat_router === undefined ? 'not recorded' : provider.chat_router ? 'on' : 'off', 'decides conversation or task before the planner runs'],
            ['Rules floor', availability(provider?.rules_floor?.available), orNot(provider?.rules_floor?.model) + ' · ' + orNot(provider?.rules_floor?.detail)],
            ['DeepSeek', provider?.deepseek?.configured === undefined ? 'not recorded' : provider.deepseek.configured ? 'configured' : 'not configured', orNot(provider?.deepseek?.note)],
            ['OpenRouter', provider?.openrouter?.configured === undefined ? 'not recorded' : provider.openrouter.configured ? 'configured' : 'not configured', orNot(provider?.openrouter?.note) + ' · key source: ' + orNot(provider?.openrouter?.key_source)],
            ['Policy in force', orNot(provider?.policy), 'the order the providers above are tried in'],
            ['Key handling', orNot(provider?.key_note), 'credentials stay in local configuration on this machine'],
            ['Probe command', orNot(provider?.probe_command), 'measures what the configured order can reach'],
          ]}
        />
        {(provider?.openrouter?.routing_order || []).length ? (
          <Facts rows={[['OpenRouter routing order', (provider?.openrouter?.routing_order || []).join(' → ')]]} />
        ) : (
          <p className="module-note">No routing order was returned by this read. {NO_ROW}.</p>
        )}
        {(provider?.openrouter?.refused || []).length ? (
          <DataTable
            caption="Ids the routing refused, as this read returned them."
            columns={['Id', 'Reason']}
            rows={(provider?.openrouter?.refused || []).map(item => (typeof item === 'string'
              ? [item, NOT_RECORDED]
              : [orNot((item as { model_id?: string }).model_id), orNot((item as { reason?: string }).reason)]))}
          />
        ) : null}
      </section>

      <section className="module-section">
        <h2>Local store and watch loop</h2>
        {health.isPending || watches.isPending ? <Reading what="the local store and watch loop" /> : null}
        {health.isError ? <Failure error={health.error} what="local store health" onRetry={() => health.refetch()} /> : null}
        {watches.isError ? <Failure error={watches.error} what="watch health" onRetry={() => watches.refetch()} /> : null}
        {health.data ? (
          <Facts
            testId="settings-health"
            rows={[
              ['Store available', String(health.data.available)],
              ['Total jobs', orNot(health.data.total_jobs)],
              ['Streams · active leases', orNot(health.data.streams) + ' · ' + orNot(health.data.active_leases)],
              ['Health note', orNot(health.data.note, 'no note returned')],
            ]}
          />
        ) : null}
        {watches.data ? (
          <Facts
            testId="settings-watches"
            rows={[
              ['Watch mode', orNot(watches.data.mode)],
              ['Last tick · fresh / age / reason', (tick?.fresh === undefined ? NOT_RECORDED : String(tick.fresh)) + ' · ' + (tick?.age_seconds === null || tick?.age_seconds === undefined ? NOT_RECORDED : tick.age_seconds + ' s') + ' · ' + orNot(tick?.reason, 'no reason returned')],
              ['Watches · total / active / expired', orNot(watches.data.watches?.total) + ' / ' + orNot(watches.data.watches?.active) + ' / ' + orNot(watches.data.watches?.expired)],
              ['Outbox undispatched', orNot(watches.data.outbox?.undispatched_depth)],
              ['Plan watcher running · interval', (watches.data.plan_watcher?.running === undefined ? NOT_RECORDED : String(watches.data.plan_watcher.running)) + ' · ' + orNot(watches.data.plan_watcher?.interval_seconds) + ' s'],
              ['Watch note', orNot(watches.data.note, 'no note returned')],
            ]}
          />
        ) : null}
        <DataTable
          caption="Collection products the store reports, one row per product."
          columns={['Product', 'Jobs', 'Newest commit']}
          rows={(health.data?.products || []).map(product => [
            orNot(product.product),
            orNot(product.jobs),
            product.newest_commit_utc ? istStamp(product.newest_commit_utc) : NOT_RECORDED,
          ])}
        />
      </section>

      <section className="module-section">
        <h2>Briefcase</h2>
        {briefs.isPending ? <Reading what="the local briefcase" /> : null}
        {briefs.isError ? <Failure error={briefs.error} what="local briefcase" onRetry={() => briefs.refetch()} /> : null}
        {briefs.data ? (
          <>
            <p className="module-note">
              {count(briefs.data.briefs.length, 'kept brief')} · delivery as returned: {orNot(briefs.data.delivery)} · {orNot(briefs.data.note, 'no note returned')}
            </p>
            <DataTable
              testId="settings-briefs"
              caption="Every kept brief this read returned."
              columns={['Brief', 'Kind', 'Saved', 'Status', 'Delivery']}
              rows={briefs.data.briefs.map(entry => [
                orNot(entry.title, entry.id),
                orNot(entry.kind),
                entry.saved_at ? istStamp(entry.saved_at) : NOT_RECORDED,
                orNot(entry.status),
                orNot(entry.delivery),
              ])}
            />
          </>
        ) : null}
      </section>
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
