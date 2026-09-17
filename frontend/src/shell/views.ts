/* The surface registry. The vanilla frontend keeps the same ids in WG.VIEWS, so every existing deep
   link (#/warnings, ...) keeps working after the port; R3 replaces each placeholder with the real module.
   The order is the rail order, and the shortcut numbers are the ones the rail prints. */
export type ViewId =
  | 'assistant' | 'workspace' | 'overview' | 'warnings' | 'map' | 'forecast' | 'observations'
  | 'changes' | 'climate' | 'advisories' | 'air-quality' | 'aviation' | 'ensemble' | 'verification'
  | 'compare' | 'marine' | 'documents' | 'briefcase' | 'settings';

export type ViewEntry = {
  id: ViewId;
  label: string;
  group: 'start' | 'weather' | 'more';
  shortcut?: number;
  /** What a reader can ask the conversation that this module answers. R1 shows them; R2 sends them. */
  intents: string[];
  /** Which module will fill this surface, and at which stage. Recorded so a placeholder cannot pass as done. */
  portedIn: 'R1' | 'R2' | 'R3' | 'R4' | 'R5';
};

export const VIEWS: ViewEntry[] = [
  { id: 'assistant', label: 'Ask', group: 'start', shortcut: 1, portedIn: 'R2',
    intents: ['hello', 'what can you do?', 'Will it rain in Surat tomorrow morning?'] },
  { id: 'workspace', label: 'Dashboard', group: 'start', portedIn: 'R3',
    intents: ['What is it like right now in Ahmedabad?'] },
  { id: 'overview', label: 'Today', group: 'start', shortcut: 2, portedIn: 'R3',
    intents: ['What is the national warning picture today?'] },
  { id: 'warnings', label: 'Warnings', group: 'weather', shortcut: 3, portedIn: 'R3',
    intents: ['Is any warning in force for Patna, Bihar today?'] },
  { id: 'map', label: 'Map', group: 'weather', shortcut: 4, portedIn: 'R3',
    intents: ['Which districts are under a warning on the map?'] },
  { id: 'forecast', label: 'Forecast', group: 'weather', shortcut: 5, portedIn: 'R3',
    intents: ['Show me the hourly forecast for Kochi tomorrow.'] },
  { id: 'observations', label: 'Observations', group: 'weather', shortcut: 7, portedIn: 'R3',
    intents: ['Which station reported the latest observation near Patna?'] },
  { id: 'advisories', label: 'Farm advisories', group: 'weather', shortcut: 8, portedIn: 'R3',
    intents: ['What does the district agromet advisory say for cotton in Ahmedabad this week?'] },
  { id: 'air-quality', label: 'Air quality', group: 'weather', portedIn: 'R3',
    intents: ['What is the modelled air quality in Delhi today?'] },
  { id: 'changes', label: 'What changed', group: 'more', shortcut: 6, portedIn: 'R3',
    intents: ['What changed between the last two editions of the district warning?'] },
  { id: 'climate', label: 'Climate records', group: 'more', shortcut: 9, portedIn: 'R3',
    intents: ['Show the annual rainfall trend for Ahmedabad district.'] },
  { id: 'marine', label: 'Sea and rivers', group: 'more', portedIn: 'R4',
    intents: ['What is the sea like near Kochi tomorrow?'] },
  { id: 'aviation', label: 'Aviation', group: 'more', portedIn: 'R3',
    intents: ['What is the current weather at VOBL?'] },
  { id: 'ensemble', label: 'Ensemble spread', group: 'more', portedIn: 'R4',
    intents: ['How much spread does the ensemble show for Kochi tomorrow?'] },
  { id: 'verification', label: 'Forecast verification', group: 'more', portedIn: 'R4',
    intents: ['How accurate was the forecast for Ahmedabad last week?'] },
  { id: 'compare', label: 'Compare places', group: 'more', portedIn: 'R3',
    intents: ['Compare the forecast for Surat and Vadodara tomorrow morning.'] },
  { id: 'documents', label: 'Published documents', group: 'more', portedIn: 'R3',
    intents: ['What does the latest national bulletin say about heavy rain?'] },
  { id: 'briefcase', label: 'Briefcase', group: 'more', portedIn: 'R3',
    intents: ['Save this answer to the briefcase.'] },
  { id: 'settings', label: 'Sources and settings', group: 'more', portedIn: 'R3',
    intents: ['Which model providers are configured?'] },
];

export const viewById = (id: string): ViewEntry | undefined => VIEWS.find(view => view.id === id);
export const shortcutView = (number: number): ViewEntry | undefined => VIEWS.find(view => view.shortcut === number);
