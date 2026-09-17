/* The top navigation: every registered surface placed in exactly one group.

   The groups follow what each surface reads, not what it is called. "What changed" compares stored forecast
   retrievals, so it sits under Forecast; "Today" is the national district warning picture, so it sits under
   the map and warnings menu. A group with one surface is a plain link; a group with several opens a menu. The routes
   are the registry's own ids, so every existing deep link keeps working. The order follows the reference bar:
   Dashboard, Forecast, Climate, Insights, AI Assistant, Map, More. */
import { VIEWS, type ViewId } from './views';

export type NavGroup = { id: string; label: string; views: ViewId[] };

export const NAV_GROUPS: NavGroup[] = [
  { id: 'dashboard', label: 'Dashboard', views: ['workspace'] },
  { id: 'forecast', label: 'Forecast', views: ['forecast', 'changes', 'ensemble', 'verification', 'compare'] },
  { id: 'climate', label: 'Climate', views: ['climate', 'marine'] },
  { id: 'insights', label: 'Insights', views: ['observations', 'air-quality', 'advisories', 'documents'] },
  { id: 'assistant', label: 'AI Assistant', views: ['assistant'] },
  { id: 'map', label: 'Map', views: ['map', 'warnings', 'overview'] },
  { id: 'more', label: 'More', views: ['aviation', 'briefcase', 'settings'] },
];

/* One line under each menu entry, stating what the surface reads. */
export const NAV_NOTES: Record<ViewId, string> = {
  assistant: 'Ask in your own words; answers keep their sources',
  workspace: 'Your place: now, next days, map, air and record',
  overview: 'The national district warning picture today',
  warnings: 'Published district-day warnings and alert briefs',
  map: 'India district warnings on the district geometry',
  forecast: 'Model series for one point, every parameter',
  observations: 'Station reports near a place',
  advisories: 'Published agromet advisories by district',
  'air-quality': 'Modelled pollutants and indices',
  changes: 'How stored forecast retrievals changed',
  climate: 'District rainfall record, 1901–2010',
  marine: 'Modelled waves and river discharge',
  aviation: 'METAR and TAF for an airport',
  ensemble: 'Member spread for a place',
  verification: 'Archived runs against reanalysis',
  compare: 'Two places side by side',
  documents: 'Indexed bulletins and advisories',
  briefcase: 'Briefs you kept on this machine',
  settings: 'Capabilities, sources and providers',
};

export function groupOf(id: string): NavGroup | undefined {
  return NAV_GROUPS.find(group => group.views.includes(id as ViewId));
}

export function viewsOf(group: NavGroup) {
  return group.views.map(id => VIEWS.find(view => view.id === id)!).filter(Boolean);
}
