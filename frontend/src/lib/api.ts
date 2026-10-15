export const API_BASE =
  (import.meta.env?.VITE_API_URL as string | undefined) ?? "http://127.0.0.1:5000";

export interface Prevention {
  action: string;
  severity: string;
  status: string;
}

/**
 * What actually happened to this machine, as opposed to what the policy
 * recommended. Present only when an execution was attempted (i.e. the policy
 * said auto_action AND a Source IP was available), so `undefined` means
 * "nothing was attempted" and must never be rendered as "action taken".
 */
export interface Execution {
  executed: boolean;
  /**
   * True when the rule was already in force for this target - the engine
   * refuses to add the same rule twice, so a repeated attacker IP is NOT an
   * error and must not render as a failed execution.
   */
  already_active?: boolean;
  reason?: string;
  rule_name?: string;
  /** null for persistent actions (block_ip / isolate_host) that never expire. */
  auto_expires_in_seconds?: number | null;
  action?: string;
  target_ip?: string | null;
}

export interface PredictionResult {
  predicted_class: string;
  cert_in_category: string;
  confidence: number;
  probabilities: Record<string, number>;
  prevention: Prevention;
  execution?: Execution;
  low_confidence_class: boolean;
  window?: number;
}

export interface PreventionRuntime {
  execution_enabled: boolean;
  env_var: string;
  allowed_demo_ranges: string[];
  executable_actions: string[];
  simulated_only_actions: string[];
  source_ip_column?: string | null;
  actions_executed?: number;
  auto_actions_recommended?: number;
}

export interface CsvSummary {
  total_sequences: number;
  attacks: number;
  normal: number;
  attack_rate: number;
  class_counts: Record<string, number>;
  auto_actions: number;
  held_for_review: number;
  truncated: boolean;
  /** Recommended actions that were genuinely carried out. Never conflate with auto_actions. */
  actions_executed?: number;
}

export interface TimelinePoint {
  window: number;
  threats: number;
  normal: number;
}

export interface CsvAnalysisResponse {
  summary: CsvSummary;
  timeline: TimelinePoint[];
  results: PredictionResult[];
  prevention?: PreventionRuntime;
  /** Present only for /api/predict_pcap: how many flows the capture became. */
  flows?: number;
}

export interface ShapAttribution {
  feature: string;
  shap_value: number;
  abs_shap_value: number;
  raw_value_mean: number;
}

export interface ExplainResponse {
  predicted_class: string;
  confidence: number;
  base_value: number;
  f_x: number;
  attributions: ShapAttribution[];
  all_features: string[];
  window?: number;
  aggregation?: string;
  timesteps?: number;
  background_source?: string;
  /** SHAP local accuracy: base_value + sum(attributions) should equal model output. */
  local_accuracy?: {
    base_value: number;
    sum_all_attributions: number;
    model_output: number;
    reconstructed: number;
    abs_error: number;
  };
}

export interface ShapBackgroundInfo {
  source: string;
  sequences: number;
  real_traffic: boolean;
  path: string | null;
}

export interface HealthResponse {
  status: string;
  shap_ready: boolean;
  shap_background?: ShapBackgroundInfo;
  model: {
    accuracy: number;
    weighted_f1: number;
    macro_f1: number;
    version: string;
  };
  prevention?: PreventionRuntime;
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      // The prevention endpoints report refusals as `reason`, everything else
      // as `error` - surface either instead of the generic message.
      if (body?.error) msg = body.error;
      else if (body?.reason) msg = body.reason;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthResponse> {
  return handle(await fetch(`${API_BASE}/api/health`, { method: "GET" }));
}

export async function analyzeCsv(file: File): Promise<CsvAnalysisResponse> {
  const form = new FormData();
  form.append("file", file);
  return handle(await fetch(`${API_BASE}/api/predict_csv`, { method: "POST", body: form }));
}

/** A Wireshark capture: the backend converts it to flows, then analyses them. */
export function isPcapFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return name.endsWith(".pcap") || name.endsWith(".pcapng");
}

export async function analyzePcap(file: File): Promise<CsvAnalysisResponse> {
  const form = new FormData();
  form.append("file", file);
  return handle(await fetch(`${API_BASE}/api/predict_pcap`, { method: "POST", body: form }));
}

export async function explainWindow(window: number): Promise<ExplainResponse> {
  return handle(
    await fetch(`${API_BASE}/api/explain_window`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ window }),
    }),
  );
}

export interface StreamLoadResponse {
  total_windows: number;
  sequence_length: number;
  prevention?: PreventionRuntime;
}

export interface StreamNextResponse {
  done: boolean;
  total?: number;
  window?: number;
  result?: PredictionResult;
}

export async function streamLoad(file: File): Promise<StreamLoadResponse> {
  const form = new FormData();
  form.append("file", file);
  return handle(await fetch(`${API_BASE}/api/stream/load`, { method: "POST", body: form }));
}

export async function streamNext(): Promise<StreamNextResponse> {
  return handle(await fetch(`${API_BASE}/api/stream/next`, { method: "GET" }));
}

/* ------------------------------------------------------------------ *
 * Live capture (backend/live_capture.py contract)
 * ------------------------------------------------------------------ */

export interface LiveInterface {
  name: string;
  description: string;
  ip: string | null;
}

export interface LiveInterfacesResponse {
  interfaces: LiveInterface[];
  /** True while the capture engine is Person B's stub: the feed is demo data. */
  stub?: boolean;
  note?: string;
}

export interface LiveStartResponse {
  running: boolean;
  interface: string;
  stub?: boolean;
}

/** One live window: a normal prediction plus where/when it was captured. */
export interface LiveResult extends PredictionResult {
  window: number;
  source_ip: string | null;
  time: string;
}

export interface LivePollResponse {
  running: boolean;
  packets: number;
  flows: number;
  windows: number;
  results: LiveResult[];
  /** Windows the page never asked for (poll lagged behind the capture). */
  skipped?: number;
  /** Results produced but not handed out yet - > 0 means the next poll has more. */
  queue_depth?: number;
  /** Windows dropped by the engine because its buffer filled. */
  dropped?: number;
  stub?: boolean;
}

export async function getLiveInterfaces(): Promise<LiveInterfacesResponse> {
  return handle(await fetch(`${API_BASE}/api/live/interfaces`, { method: "GET" }));
}

export async function startLive(interfaceName: string): Promise<LiveStartResponse> {
  return handle(
    await fetch(`${API_BASE}/api/live/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ interface: interfaceName }),
    }),
  );
}

/**
 * Windows after `after` (exclusive), at most `limit` per call. Pass after=-1
 * before the first window has arrived; the server caps limit at 50.
 */
export async function pollLive(after: number, limit = 50): Promise<LivePollResponse> {
  return handle(
    await fetch(`${API_BASE}/api/live/poll?after=${after}&limit=${limit}`, { method: "GET" }),
  );
}

export async function stopLive(): Promise<LiveStartResponse> {
  return handle(await fetch(`${API_BASE}/api/live/stop`, { method: "POST" }));
}

/* ------------------------------------------------------------------ *
 * Prevention - what is actually in force on this machine
 * ------------------------------------------------------------------ */

export interface ActiveRule {
  rule_name?: string | null;
  action: string | null;
  target_ip: string | null;
  /** true = stays until revoked; false = the engine removes it on a timer. */
  persistent?: boolean | null;
  expires_in_seconds?: number | null;
  ttl_seconds?: number | null;
}

export interface ActiveRulesResponse {
  rules: ActiveRule[];
  /**
   * True once the engine exposes active_rules() itself. Until then the list
   * comes from the engine's in-process registry, so a rule created moments ago
   * still shows, but the source is not the engine's own reporting API.
   */
  engine_ready?: boolean;
}

export async function getActiveRules(): Promise<ActiveRulesResponse> {
  return handle(await fetch(`${API_BASE}/api/prevention/active`, { method: "GET" }));
}

export interface RevokeResponse {
  revoked: boolean;
  reason?: string;
  rule_name?: string;
  action?: string;
  target_ip?: string;
}

/** Lift a persistent block created by the execution engine. */
export async function revokePrevention(action: string, targetIp: string): Promise<RevokeResponse> {
  return handle(
    await fetch(`${API_BASE}/api/prevention/revoke`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, target_ip: targetIp }),
    }),
  );
}
