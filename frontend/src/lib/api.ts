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
      if (body?.error) msg = body.error;
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
