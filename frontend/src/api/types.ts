/* The engine's own contracts, written from captured payloads rather than from a wish list.

   Every field here exists in a response this workspace actually produced (the shapes are recorded in
   research/reviews/). Optional fields are optional because the engine omits them, not because a
   surface may invent them: a surface renders what arrived and says "not recorded" where it did not. */

export type AnswerStatus =
  | 'answered'
  | 'needs_selection'
  | 'needs_clarification'
  | 'unavailable'
  | 'outside_validity'
  | 'explanation'
  | 'conversation'
  | 'cancelled';

export type Fact = {
  id: string;
  parameter: string;
  label?: string;
  value: string;
  unit?: string | null;
  place?: string | null;
  entity_id?: string;
  observed_at?: string | null;
  start?: string | null;
  end?: string | null;
  sample_at?: string | null;
  source_id?: string;
  evidence_kind?: string;
  evidence_version?: string;
  citation_ids?: string[];
  source_locators?: { page?: number | string; row?: number | string; column?: string; prefix?: string; locator?: string }[];
  method?: string;
  task_id?: string;
};

export type Citation = {
  id: string;
  source_id: string;
  provider?: string;
  product?: string;
  url?: string;
  sha256?: string;
  retrieved_at_utc?: string;
  /* A citation names where inside the record the value came from: a printed page, a row or column of a
     published table, or the address the engine read. Any of them may be absent, and an absent one is stated
     as absent rather than filled with a guess. */
  page?: number | string;
  row?: number | string;
  column?: string;
  locator?: string;
  local_document_path?: string;
};

export type TaskResult = {
  id: string;
  request: {
    request_quote?: string;
    kind?: string;
    operation?: string;
    parameters?: string[];
    years?: number[];
    period?: string;
    start_local?: string;
    end_local?: string;
    place_indices?: number[];
  };
  status: string;
  answer?: string;
  fact_ids?: string[];
  passage_ids?: string[];
  note?: string;
};

export type RetrievalPlanEntry = {
  task_id: string;
  operation?: string;
  kind?: string;
  parameters?: string[];
  candidates?: { tool?: string; selected?: boolean; available?: boolean; reason?: string; sources?: string[] }[];
  status?: string;
  returned_source_ids?: string[];
};

export type ResolvedPoint = {
  selection_id?: string;
  id?: string;
  name?: string;
  label?: string;
  latitude?: number;
  longitude?: number;
  coordinates?: { latitude: number; longitude: number };
  feature?: string;
  admin1?: string;
  admin2?: string;
  distance_km?: number;
  name_match_basis?: string;
  state_match_basis?: string;
  match_type?: string;
  other_alias_matches?: number;
  accepted_because?: string;
  alternatives?: string[];
  administrative_mapping?: string;
  source_id?: string;
  citation?: Citation;
  for_place_name?: string;
};

/* A returned series point. The engine states the instant as `t` and the value as `v`; the historical-record
   charts state a `year` and an `x`, which is why both shapes are here rather than a guess in a component. */
export type ChartPoint = {
  t?: string | null;
  v?: number | string | null;
  value?: number | string | null;
  label?: string;
  x?: number;
  year?: number;
  evidence_id?: string;
  source_locator?: string;
};

export type Chart = {
  kind?: string;
  title?: string;
  unit?: string;
  axis_label?: string;
  points?: ChartPoint[];
  series?: { label?: string; points?: ChartPoint[] }[];
  source_id?: string;
  note?: string;
  [key: string]: unknown;
};

/* A value the engine computed from retrieved facts. `kind`/`operation` say what kind of computation it is;
   the method, interpretation, input ids and source ids are the engine's own words about how it was made. */
export type Calculation = {
  kind?: string;
  operation?: string;
  label?: string;
  value?: string | number;
  unit?: string | null;
  method?: string;
  expression?: string;
  interpretation?: string;
  input_ids?: string[];
  source_ids?: string[];
  sample_count?: number;
  task_id?: string;
  [key: string]: unknown;
};

/* An airport report the engine retrieved: the raw text as the source transmitted it, the kind this product
   read (metar is an observation with an observed time, taf is a forecast with a validity interval) and the
   instants the report carried. */
export type AirportReport = {
  station?: string;
  kind?: string;
  raw_report?: string;
  source_locator?: string;
  citation_ids?: string[];
  observed_at?: string | null;
  valid_start?: string | null;
  valid_end?: string | null;
  [key: string]: unknown;
};

/* One day of an IMD district warning product as the engine's parser states it. A day the product leaves
   unlabelled or uncoloured is absent here rather than defaulted by a surface. */
export type WarningDay = {
  day?: number;
  /* The district read states each day's own label as `label`; a payload that spells the same value
     `day_label` is read rather than shown as unlabelled. */
  label?: string;
  day_label?: string;
  colour?: string | null;
  colour_code?: number | null;
  quiet?: boolean;
  hazards?: string[];
  source_text?: string;
  starts_utc?: string | null;
  ends_utc?: string | null;
  [key: string]: unknown;
};

export type DistrictWarningEntry = {
  place?: string;
  district?: string;
  issued_at_utc?: string | null;
  days?: WarningDay[];
  [key: string]: unknown;
};

export type WarningEvidenceEntry = {
  records?: unknown[];
  latest_sent?: string | null;
  assessment?: { eligible_by_lifecycle?: number; all_clear?: boolean; [key: string]: unknown } | null;
  district_warnings?: DistrictWarningEntry[];
  stale_districts?: { place?: string; district?: string; issued_at_utc?: string | null }[];
  points_outside_districts?: string[];
  [key: string]: unknown;
};

export type Passage = {
  id?: string;
  text?: string;
  document?: string;
  family?: string;
  region?: string;
  page?: number;
  issue_date?: string;
  source_id?: string;
  [key: string]: unknown;
};

export type AnswerPacket = {
  schema_version?: string;
  conversation_id: string;
  question: string;
  status: AnswerStatus | string;
  answer: string;
  answer_basis?: string | null;
  facts?: Fact[];
  citations?: Citation[];
  notes?: string[];
  choices?: { label?: string; value?: string; selection_id?: string; place?: string; [key: string]: unknown }[];
  quick_replies?: { label: string; reply: string; basis?: string }[];
  follow_up?: string | null;
  operational_eligible?: boolean;
  answered_at_utc?: string | null;
  expires_at_utc?: string | null;
  plan?: Record<string, unknown> | null;
  plan_watch?: PlanRecord | null;
  trace?: Trace;
  task_results?: TaskResult[];
  task_coverage?: { requested: number; completed: number; incomplete_ids: string[] };
  retrieval_plan?: RetrievalPlanEntry[];
  retrieval_coverage?: unknown[];
  resolved_points?: Record<string, ResolvedPoint>;
  pending_slots?: { name?: string; question?: string; [key: string]: unknown }[];
  charts?: Chart[];
  calculations?: Calculation[];
  document_evidence?: Passage[];
  passages?: Passage[];
  airport_reports?: AirportReport[];
  warning_evidence?: WarningEvidenceEntry[];
  refresh?: { state?: string; job_id?: string; worker_state?: string; message?: string; [key: string]: unknown } | null;
  warnings?: unknown;
  [key: string]: unknown;
};

export type Trace = {
  planning?: {
    provider?: string;
    model?: string;
    model_calls?: number;
    planner_policy?: string;
    attempts?: number;
    latency_ms?: number;
    failover?: string[];
    planning_error?: string;
  };
  generation?: {
    provider?: string;
    model?: string;
    status?: string;
    reason?: string;
    validation?: string;
    evidence_ids?: string[];
    requested_language?: string;
    language_selection?: string;
    language_adherence?: string;
    written_by?: string;
    [key: string]: unknown;
  } | null;
  tools?: Record<string, unknown>[];
  provider?: string;
  duration_seconds?: number;
  context_resolution?: { action?: string; changed_fields?: string[]; inherited_fields?: string[] };
  language?: { requested?: string; selection?: string; adherence?: string; rendered?: boolean; detail?: string; [key: string]: unknown };
  [key: string]: unknown;
};

export type ChatProgress = {
  schema_version: string;
  state: 'idle' | 'working' | 'done' | string;
  stage: string | null;
  stage_label: string | null;
  stages_seen: string[];
  stage_since_utc?: string | null;
  stage_seconds?: number | null;
  turn_seconds?: number | null;
  queue: { waiting: number; active: number; capacity: number | null; wait_seconds_before_refusal: number | null };
  stage_note?: string;
  stages_are_facts_not_progress?: boolean;
  checked_at_utc?: string | null;
  turn_id?: string | null;
};

export type ChatPreview = {
  schema_version: string;
  provisional: boolean;
  note: string;
  reading?: {
    places?: { name?: string; kind?: string; basis?: string; label?: string }[];
    window?: { start_local?: string; end_local?: string; label?: string; explicit?: boolean } | null;
    products?: { kind?: string; label?: string; parameters?: string[] }[];
    planner?: string;
    inherited?: string[];
    changed?: string[];
  };
  [key: string]: unknown;
};

export type CancelResult = {
  request_id: string;
  state: 'cancel_requested' | 'not_running';
  stage?: string;
  stage_label?: string;
  detail: string;
};

export type Health = {
  schema_version: string;
  available: boolean;
  warm?: unknown;
  products?: { product: string; jobs: number; states: Record<string, number>; newest_commit_utc?: string }[];
  job_states?: Record<string, number>;
  total_jobs?: number;
  streams?: number;
  active_leases?: number;
  cooldowns?: unknown[];
  note?: string;
};

export type LanguageEntry = {
  code: string;
  sarvam_code?: string;
  english_name: string;
  native_name: string;
  script?: string;
  declared?: { hear?: boolean; write?: boolean; speak?: boolean };
  measured?: { hear?: string; write?: string; speak?: string };
  script_check_available?: boolean;
};

export type Languages = { schema_version: string; service_configured: boolean; note?: string; languages: LanguageEntry[] };

export type ConversationRow = { id: string; updated?: string; turns?: number; asked?: number; opening_question?: string };
export type Ledger = { schema_version: string; total: number; limit: number; conversations: ConversationRow[]; note?: string };

export type Persona = {
  id: string;
  label: string;
  who?: string;
  surfaces?: string[];
  evidence_first?: string[];
  starters?: string[];
  keeps_aside?: string[];
  note?: string;
};

export type Personas = { data?: { personas?: Persona[]; note?: string; default?: string | null }; limitations?: string[] };

export type SourceEntry = {
  source_id: string;
  product?: string;
  layer?: string | null;
  url?: string | null;
  retrieved_at_utc?: string | null;
  sha256_prefix?: string;
  integration_status?: string;
  usage_terms?: string;
  user_review?: string;
};

export type Envelope<T> = {
  schema_version: string;
  generated_at_utc?: string;
  view?: string;
  status?: string;
  data: T;
  sources?: SourceEntry[];
  coverage?: Record<string, number | string | null | undefined>;
  limitations?: string[];
  not_established?: string[];
};

export type Capability = { tool: string; kind: string; operations?: string[]; parameters?: string[]; purpose?: string };

export type CapabilitiesData = {
  capabilities: Capability[];
  sources: SourceEntry[];
  registered_sources?: number;
  connected_sources?: number;
  provider?: {
    policy?: string;
    planner_policy?: string;
    chat_router?: boolean;
    providers?: { provider: string; model?: string | null; models?: string[]; available?: boolean; reason?: string }[];
    last_failure?: unknown;
    rules_floor?: { model?: string; available?: boolean; detail?: string };
    deepseek?: { configured?: boolean; model?: string; note?: string };
    openrouter?: { configured?: boolean; key_source?: string; routing_order?: string[]; refused?: string[]; note?: string };
    set_key_command?: string;
    set_deepseek_key_command?: string;
    probe_command?: string;
    key_note?: string;
  };
};

export type PlanRecord = {
  id?: string;
  question?: string;
  place?: Record<string, unknown>;
  window?: Record<string, unknown>;
  status?: string;
  channels?: string[];
  [key: string]: unknown;
};

export type WatchHealth = {
  schema_version: string;
  mode: string;
  note?: string;
  heartbeat?: unknown;
  tick?: { fresh?: boolean; age_seconds?: number | null; reason?: string };
  outbox?: { counts?: Record<string, number>; undispatched_depth?: number; oldest_undispatched_created_at?: string | null };
  watches?: { total?: number; active?: number; expired?: number };
  plan_watcher?: { running?: boolean; interval_seconds?: number; last_result?: unknown };
};

export type Briefs = { schema_version?: string; delivery?: string; note?: string; briefs: BriefRecord[] };
export type BriefRecord = {
  id: string;
  saved_at?: string;
  kind?: string;
  title?: string;
  place?: { district?: string; state?: string; label?: string; latitude?: number | null; longitude?: number | null };
  window?: { starts_utc?: string; ends_utc?: string; label?: string; day?: number };
  content_sha256?: string;
  sources?: string[];
  status?: string;
  /* The kept-brief route states source identifiers, not registry rows: the recorded payloads carry plain ids
     such as "S63", so the type says so rather than promising a row the read does not return. */
  evidence?: { sources?: (SourceEntry | string)[]; not_established?: string[]; why?: string | null; notes?: string[] };
  delivery?: string;
};

export type NowReading = {
  schema_version: string;
  generated_at_utc?: string;
  point?: { latitude: number; longitude: number; label?: string | null };
  observed?: {
    status?: string;
    stations?: {
      kind?: string; name?: string; station_code?: string; latitude?: number; longitude?: number;
      observed_at_utc?: string; parameters?: { name?: string; value?: number | string; unit?: string }[];
      source_id?: string; distance_km?: number; age_minutes?: number; stale?: boolean; network?: string;
    }[];
    rows_in_radius?: number;
    sources?: string[];
    coverage?: Record<string, number>;
    limitations?: string[];
  };
  in_force?: {
    district?: string; state?: string; day?: number; day_label?: string; starts_utc?: string; ends_utc?: string;
    colour?: string; colour_code?: number; hazards?: string[]; quiet?: boolean; status_line?: string;
    wording?: string; issued_at_utc?: string; source_id?: string; source_locator?: string; status?: string;
  };
  next_hours?: {
    status?: string;
    rows?: { at?: string; temperature_2m?: number; precipitation_probability?: number; precipitation?: number; wind_speed_10m?: number }[];
    starts?: string; ends?: string; source_id?: string; model?: string; unit?: Record<string, string>;
  };
  not_connected?: string[];
  not_established?: string[];
  limitations?: string[];
  status?: string;
  summary?: string;
};

export type DistrictWarningDay = {
  date?: string; day_label?: string; colour?: string; colour_code?: number; hazards?: string[]; wording?: string;
};

export type DistrictWarning = {
  key?: string; district?: string; state?: string; bulletin_date?: string; issued_at_utc?: string;
  updated_at?: string; days?: DistrictWarningDay[];
};
