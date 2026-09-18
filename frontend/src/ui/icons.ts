/* The icon each surface and each recurring idea is drawn with. One map, so the rail, the command
   palette and a surface header cannot disagree about what a thing looks like. */
import {
  Activity, AlertTriangle, BarChart3, BookOpen, Boxes, Briefcase, CalendarClock, ClipboardList,
  CloudSun, Compass, Cpu, Database, Droplets, FileText, Gauge, GitCompare, History, LayoutDashboard,
  LineChart, Map as MapIcon, MessageSquare, Notebook, Plane, Radar, Server, Settings2, ShieldAlert,
  SlidersHorizontal, Sparkles, Thermometer, Waves, Wind, Wrench, type LucideIcon,
} from 'lucide-react';

export const SURFACE_ICONS: Record<string, LucideIcon> = {
  assistant: MessageSquare,
  workspace: Wrench,
  overview: LayoutDashboard,
  warnings: ShieldAlert,
  map: MapIcon,
  forecast: CloudSun,
  observations: Radar,
  changes: GitCompare,
  climate: History,
  advisories: Boxes,
  'air-quality': Wind,
  aviation: Plane,
  ensemble: Activity,
  verification: Gauge,
  compare: GitCompare,
  marine: Waves,
  documents: BookOpen,
  briefcase: Briefcase,
  settings: Settings2,
};

export const IDEA_ICONS: Record<string, LucideIcon> = {
  rain: Droplets,
  temperature: Thermometer,
  wind: Wind,
  station: Radar,
  warning: AlertTriangle,
  history: History,
  chart: LineChart,
  compare: GitCompare,
  documents: FileText,
  brief: ClipboardList,
  plan: CalendarClock,
  panel: SlidersHorizontal,
  engine: Cpu,
  source: Database,
  server: Server,
  sparkle: Sparkles,
  compass: Compass,
  notebook: Notebook,
  gauge: BarChart3,
};

export type { LucideIcon };
