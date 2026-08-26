import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Upload,
  FileText,
  X,
  Play,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  Activity,
  AlertTriangle,
  Download,
  Radar,
  Sparkles,
  Target,
  Brain,
  Lightbulb,
  ListOrdered,
  Gavel,
  Eye,
  Wifi,
  WifiOff,
  ChevronRight,
  Info,
} from "lucide-react";
import {
  BarChart,
  Bar,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  PieChart,
  Pie,
  CartesianGrid,
  Area,
  AreaChart,
  ReferenceLine,
  PolarAngleAxis,
  RadialBarChart,
  RadialBar,
} from "recharts";
import {
  analyzeCsv,
  explainWindow,
  getHealth,
  type CsvAnalysisResponse,
  type ExplainResponse,
  type HealthResponse,
  type PredictionResult,
} from "@/lib/api";
import { LiveFeed } from "@/components/LiveFeed";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Threat Analysis Dashboard — ThreatLens AI" },
      {
        name: "description",
        content:
          "Upload network flow CSVs and inspect CNN-LSTM predictions with SHAP-explained, per-class results.",
      },
    ],
  }),
  component: Dashboard,
});

const CHART_BG = "#141432";
const CHART_TEXT = "#a0a0b8";
const CHART_GRID = "rgba(79, 70, 229, 0.15)";

const CATEGORY_COLORS: Record<string, string> = {
  Normal: "#10b981",
  BENIGN: "#10b981",
  DDoS: "#e5484d",
  DoS: "#f5a623",
  PortScan: "#4f46e5",
  "Port Scan": "#4f46e5",
  "Brute Force": "#8b5cf6",
  "Web Attack": "#ec4899",
  Botnet: "#f97316",
  Bot: "#f97316",
  Exploit: "#14b8a6",
  Infiltration: "#ef4444",
};

const FALLBACK_COLORS = ["#38bdf8", "#c084fc", "#fb7185", "#34d399", "#fbbf24"];

function classColor(name: string): string {
  if (CATEGORY_COLORS[name]) return CATEGORY_COLORS[name];
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return FALLBACK_COLORS[h % FALLBACK_COLORS.length];
}

function severityTone(severity: string): "danger" | "warning" | "muted" {
  if (severity === "critical") return "danger";
  if (severity === "high") return "warning";
  return "muted";
}

function Dashboard() {
  const [mode, setMode] = useState<"batch" | "live">("batch");
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [status, setStatus] = useState<"idle" | "analyzing" | "done">("idle");
  const [analysis, setAnalysis] = useState<CsvAnalysisResponse | null>(null);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [explanation, setExplanation] = useState<ExplainResponse | null>(null);
  const [explainState, setExplainState] = useState<"idle" | "loading" | "error">("idle");
  const [explainError, setExplainError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const selectSequence = useCallback(
    (idx: number) => {
      setSelectedIdx(idx);
      setExplainState("loading");
      setExplainError(null);
      explainWindow(idx)
        .then((exp) => {
          setExplanation(exp);
          setExplainState("idle");
        })
        .catch((e: Error) => {
          setExplanation(null);
          setExplainError(e.message);
          setExplainState("error");
        });
    },
    []
  );

  const analyze = async () => {
    if (!file) return;
    setStatus("analyzing");
    setError(null);
    setAnalysis(null);
    setExplanation(null);
    try {
      const res = await analyzeCsv(file);
      setAnalysis(res);
      setStatus("done");
      const firstAttack = res.results.findIndex((r) => r.predicted_class !== "BENIGN");
      selectSequence(firstAttack >= 0 ? firstAttack : 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
      setStatus("idle");
    }
  };

  const reset = () => {
    setFile(null);
    setAnalysis(null);
    setExplanation(null);
    setStatus("idle");
    setError(null);
    setSelectedIdx(0);
    if (inputRef.current) inputRef.current.value = "";
  };

  const backendLive = health?.status === "ok";

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 heading-kicker">
            <span className="h-px w-6 bg-primary" />
            Analysis Console
          </div>
          <h1 className="mt-3 heading-hero">
            Threat Analysis{" "}
            <span className="bg-gradient-to-r from-primary to-[#a78bfa] bg-clip-text text-transparent">
              Dashboard
            </span>
          </h1>
          <p className="mt-2 text-sm text-muted-foreground max-w-2xl">
            Upload a capture file and let the CNN-LSTM engine classify each flow — every prediction comes with a SHAP explanation.
          </p>
        </div>
        <div className="flex flex-col items-start sm:items-end gap-2">
          <BackendBadge live={backendLive} shapReady={health?.shap_ready ?? false} />
          {health && (
            <div className="text-[10px] font-mono text-muted-foreground tracking-wider uppercase">
              {health.model.version} · acc {(health.model.accuracy * 100).toFixed(2)}% · wF1{" "}
              {(health.model.weighted_f1 * 100).toFixed(2)}%
            </div>
          )}
        </div>
      </div>

      {!backendLive && (
        <div className="glass rounded-2xl border border-warning/40 p-4 flex items-center gap-3">
          <Info className="h-5 w-5 text-warning shrink-0" />
          <p className="text-sm text-muted-foreground">
            Backend not reachable at <span className="font-mono text-foreground">127.0.0.1:5000</span>. Start it with{" "}
            <span className="font-mono text-primary">python app.py</span> inside{" "}
            <span className="font-mono text-primary">backend/</span> to run live analysis.
          </p>
        </div>
      )}

      <div className="inline-flex rounded-xl glass p-1 gap-1 w-fit">
        {(["batch", "live"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`relative px-5 py-2 rounded-lg text-xs font-bold uppercase tracking-widest transition-all ${
              mode === m
                ? "bg-primary text-primary-foreground shadow-[4px_4px_0px_#1e1e5a]"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {m === "batch" ? "Batch Analysis" : "Live Feed"}
          </button>
        ))}
      </div>

      {mode === "live" ? (
        <LiveFeed />
      ) : (
        <>
        <section
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f) setFile(f);
        }}
        className={`relative overflow-hidden glass-strong rounded-3xl p-6 sm:p-10 transition-colors ${
          dragOver ? "border-primary/60 bg-primary/5" : ""
        }`}
      >
        <div className="absolute inset-0 grid-pattern opacity-40 pointer-events-none" />
        <div className="relative grid lg:grid-cols-[1fr_auto] gap-6 items-center">
          <div className="flex items-start gap-5">
            <div className="relative shrink-0 h-14 w-14 grid place-items-center rounded-2xl bg-gradient-to-br from-primary to-[#8b5cf6]">
              <Upload className="h-6 w-6 text-primary-foreground" />
              <span className="absolute inset-0 rounded-2xl ping-slow bg-primary/40" />
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="heading-card">Drag &amp; Drop Network Traffic CSV</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Must include the 20 model feature columns · windows of 10 flows per prediction.
              </p>

              {file ? (
                <div className="mt-4 glass rounded-xl p-3 flex items-center gap-3">
                  <FileText className="h-5 w-5 text-primary shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{file.name}</div>
                    <div className="text-xs text-muted-foreground font-mono">
                      {(file.size / 1024).toFixed(1)} KB · Ready
                    </div>
                  </div>
                  <span className="h-2 w-2 rounded-full bg-success animate-pulse" />
                  <button
                    onClick={reset}
                    className="ml-1 rounded-md p-1.5 hover:bg-white/5"
                    aria-label="Remove file"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => inputRef.current?.click()}
                  className="mt-4 w-full sm:w-auto inline-flex items-center gap-2 rounded-xl glass px-4 py-2.5 text-sm font-medium hover:bg-white/5 transition-colors"
                >
                  <FileText className="h-4 w-4 text-primary" />
                  Browse CSV
                </button>
              )}
              <input
                ref={inputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>
          </div>

          <button
            onClick={analyze}
            disabled={!file || status === "analyzing"}
            className="group relative inline-flex items-center justify-center gap-2 px-8 py-4 bg-primary text-sm font-bold uppercase tracking-tight text-primary-foreground shadow-[8px_8px_0px_#1e1e5a] disabled:opacity-40 disabled:cursor-not-allowed hover:enabled:bg-white hover:enabled:text-background hover:enabled:shadow-[4px_4px_0px_#8b5cf6] active:enabled:scale-95 transition-all duration-300 overflow-hidden"
          >
            <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:enabled:translate-x-full transition-transform duration-700" />
            {status === "analyzing" ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin relative" />
                <span className="relative">Scanning...</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4 relative" />
                <span className="relative">Analyse Network Traffic</span>
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="relative mt-4 rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {status === "analyzing" && (
          <>
            <ScanOverlay />
            <div className="relative mt-4 rounded-xl border border-warning/30 bg-warning/5 p-3 flex items-center gap-2 text-xs text-warning font-mono">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Running CNN-LSTM inference on server — this can take a minute for large files.
            </div>
          </>
        )}
      </section>

      {analysis && (
        <ResultView
          analysis={analysis}
          selectedIdx={selectedIdx}
          onSelect={selectSequence}
          explanation={explanation}
          explainState={explainState}
          explainError={explainError}
        />
      )}

      {!analysis && status !== "analyzing" && <EmptyState />}
        </>
      )}
    </div>
  );
}

function BackendBadge({ live, shapReady }: { live: boolean; shapReady: boolean }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full glass px-3 py-1.5 text-[11px] font-mono uppercase tracking-widest">
      {live ? (
        <>
          <Wifi className="h-3.5 w-3.5 text-success" />
          <span className="text-success">Model Connected</span>
          <span className="text-muted-foreground">· SHAP {shapReady ? "ready" : "loading"}</span>
        </>
      ) : (
        <>
          <WifiOff className="h-3.5 w-3.5 text-warning" />
          <span className="text-warning">Backend Offline</span>
        </>
      )}
    </div>
  );
}

function ScanOverlay() {
  return (
    <div className="relative mt-6 h-24 overflow-hidden rounded-xl border border-primary/30 bg-black/40">
      <div className="absolute inset-0 grid-pattern opacity-60" />
      <style>{`
        @keyframes scanX { 0% { left: -33%; } 100% { left: 100%; } }
      `}</style>
      <div
        className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-primary/40 to-transparent"
        style={{ animation: "scanX 1.6s linear infinite" }}
      />
      <div className="relative h-full grid place-items-center">
        <div className="flex items-center gap-3 font-mono text-xs text-primary tracking-widest uppercase">
          <Radar className="h-4 w-4 animate-pulse" />
          Analysing flows · CNN → LSTM → Softmax
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="glass rounded-3xl p-12 text-center">
      <div className="mx-auto h-14 w-14 rounded-2xl grid place-items-center bg-gradient-to-br from-primary/20 to-[#8b5cf6]/40 border border-primary/30">
        <Activity className="h-6 w-6 text-primary" />
      </div>
      <h3 className="mt-4 heading-card">Awaiting network capture</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Results, statistics and SHAP explanations will appear here after analysis.
      </p>
    </div>
  );
}

interface ResultViewProps {
  analysis: CsvAnalysisResponse;
  selectedIdx: number;
  onSelect: (idx: number) => void;
  explanation: ExplainResponse | null;
  explainState: "idle" | "loading" | "error";
  explainError: string | null;
}

function ResultView({ analysis, selectedIdx, onSelect, explanation, explainState, explainError }: ResultViewProps) {
  const { summary, timeline, results } = analysis;
  const selected: PredictionResult | undefined = results[selectedIdx];
  const isAttackOverview = summary.attacks > 0;

  const classCountsData = Object.entries(summary.class_counts)
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => ({ name, count }));

  const pieData = [
    { name: "Normal", value: summary.normal },
    ...Object.entries(summary.class_counts)
      .filter(([name]) => name !== "BENIGN")
      .map(([name, value]) => ({ name, value })),
  ];

  const statCards = [
    { label: "Sequences", value: summary.total_sequences.toLocaleString(), icon: Activity, tone: "primary" },
    { label: "Normal", value: summary.normal.toLocaleString(), icon: ShieldCheck, tone: "success" },
    { label: "Attacks", value: summary.attacks.toLocaleString(), icon: ShieldAlert, tone: "danger" },
    { label: "Auto Actions", value: summary.auto_actions.toLocaleString(), icon: Gavel, tone: "danger" },
    { label: "Held for Review", value: summary.held_for_review.toLocaleString(), icon: Eye, tone: "warning" },
  ] as const;

  const downloadReport = () => {
    const blob = new Blob([JSON.stringify({ summary, timeline, results }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "threatlens-report.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 fade-up">
      <div className="grid lg:grid-cols-3 gap-6">
        <div
          className={`relative overflow-hidden glass-strong rounded-3xl p-6 lg:col-span-2 ${
            isAttackOverview ? "border-destructive/40" : "border-success/40"
          }`}
        >
          <div
            className={`absolute -top-24 -right-24 h-64 w-64 rounded-full blur-3xl ${
              isAttackOverview ? "bg-destructive/25" : "bg-success/20"
            }`}
          />
          <div className="relative flex flex-col sm:flex-row items-start sm:items-center gap-6">
            <div
              className={`relative h-24 w-24 shrink-0 grid place-items-center rounded-2xl ${
                isAttackOverview
                  ? "bg-destructive/15 border border-destructive/40"
                  : "bg-success/15 border border-success/40"
              }`}
            >
              {isAttackOverview ? (
                <ShieldAlert className="h-10 w-10 text-destructive" />
              ) : (
                <ShieldCheck className="h-10 w-10 text-success" />
              )}
              <span
                className={`absolute inset-0 rounded-2xl ping-slow ${
                  isAttackOverview ? "bg-destructive/30" : "bg-success/30"
                }`}
              />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">
                Batch Verdict · Live Model
              </div>
              <div className="mt-1 flex flex-wrap items-baseline gap-3">
                <span
                  className={`font-display text-3xl sm:text-4xl uppercase tracking-wide ${
                    isAttackOverview ? "text-destructive" : "text-success"
                  }`}
                >
                  {isAttackOverview ? "Attacks Detected" : "All Clear"}
                </span>
              </div>
              <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-4">
                <MetricInline label="Attack Rate" value={`${(summary.attack_rate * 100).toFixed(1)}%`} tone={isAttackOverview ? "danger" : "muted"} icon={Target} />
                <MetricInline label="Top Threat" value={classCountsData.find((d) => d.name !== "BENIGN")?.name ?? "None"} tone="warning" />
                <MetricInline label="Classes Seen" value={String(classCountsData.length)} />
                <MetricInline label="Truncated" value={summary.truncated ? "Yes (>2000 win)" : "No"} />
              </div>
            </div>
          </div>
        </div>

        <div className="glass rounded-3xl p-6">
          <div className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">
            Attack Ratio
          </div>
          <div className="mt-2 h-48">
            <ResponsiveContainer>
              <RadialGauge value={summary.attack_rate * 100} />
            </ResponsiveContainer>
          </div>
          <div className="-mt-32 relative text-center pointer-events-none">
            <div className="font-display text-4xl uppercase tracking-wide bg-gradient-to-r from-primary to-[#a78bfa] bg-clip-text text-transparent">
              {(summary.attack_rate * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground font-mono uppercase tracking-widest mt-1">
              malicious
            </div>
          </div>
          <div className="mt-14" />
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="heading-card">Network Statistics</h3>
          <button
            onClick={downloadReport}
            className="inline-flex items-center gap-2 rounded-lg glass px-3 py-1.5 text-xs font-semibold hover:bg-primary/10 hover:border-primary/40 transition-all"
          >
            <Download className="h-3.5 w-3.5 text-primary" />
            Export Report
          </button>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {statCards.map((s) => (
            <div
              key={s.label}
              className="glass rounded-2xl p-5 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_15px_40px_-15px_rgba(79,70,229,0.4)]"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">{s.label}</span>
                <s.icon
                  className={`h-4 w-4 ${
                    s.tone === "danger" ? "text-destructive" : s.tone === "success" ? "text-success" : s.tone === "warning" ? "text-warning" : "text-primary"
                  }`}
                />
              </div>
              <div className="mt-3 font-display text-2xl sm:text-3xl uppercase tracking-wide">{s.value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <ChartCard title="Detected Class Distribution" subtitle="Sequences per predicted class">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={classCountsData} layout="vertical" margin={{ left: 20, right: 20 }}>
              <XAxis type="number" hide />
              <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} width={120} tick={{ fill: CHART_TEXT, fontSize: 11 }} />
              <Tooltip
                cursor={{ fill: "rgba(79, 70, 229, 0.15)" }}
                contentStyle={{ background: CHART_BG, border: `1px solid ${CHART_GRID}`, borderRadius: 10, fontSize: 12 }}
              />
              <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                {classCountsData.map((d) => (
                  <Cell key={d.name} fill={classColor(d.name)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Traffic Composition" subtitle="Normal vs attack categories">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={95} paddingAngle={3} stroke="#0a0a1a">
                {pieData.map((d) => (
                  <Cell key={d.name} fill={classColor(d.name)} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: CHART_BG, border: `1px solid ${CHART_GRID}`, borderRadius: 10, fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2 justify-center">
            {pieData.map((d) => (
              <div key={d.name} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: classColor(d.name) }} />
                {d.name}
              </div>
            ))}
          </div>
        </ChartCard>

        <ChartCard title="Threat Timeline" subtitle="Threats vs normal across sequence windows" className="lg:col-span-2">
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={timeline.map((t) => ({ ...t, t: `#${t.window}` }))}>
              <defs>
                <linearGradient id="areaThreat" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#e5484d" stopOpacity={0.6} />
                  <stop offset="100%" stopColor="#e5484d" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="areaNormal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="#4f46e5" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={CHART_GRID} strokeDasharray="3 3" />
              <XAxis dataKey="t" tick={{ fill: CHART_TEXT, fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: CHART_TEXT, fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip contentStyle={{ background: CHART_BG, border: `1px solid ${CHART_GRID}`, borderRadius: 10, fontSize: 12 }} />
              <Area type="monotone" dataKey="normal" stroke="#4f46e5" fill="url(#areaNormal)" strokeWidth={2} />
              <Area type="monotone" dataKey="threats" stroke="#e5484d" fill="url(#areaThreat)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid xl:grid-cols-[380px_1fr] gap-6 items-start">
        <div className="glass rounded-3xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <ListOrdered className="h-4 w-4 text-primary" />
            <h3 className="heading-card">Sequence Results</h3>
            <span className="ml-auto text-[10px] font-mono text-muted-foreground">click to explain</span>
          </div>
          <div className="max-h-[520px] overflow-y-auto pr-1 space-y-1.5">
            {results.slice(0, 200).map((r, idx) => {
              const isSel = idx === selectedIdx;
              const atk = r.predicted_class !== "BENIGN";
              return (
                <button
                  key={idx}
                  onClick={() => onSelect(idx)}
                  className={`w-full text-left rounded-xl px-3 py-2.5 border transition-all ${
                    isSel
                      ? "border-primary/50 bg-primary/10"
                      : "border-transparent hover:bg-white/5"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-muted-foreground w-8">#{idx}</span>
                    <span className={`text-xs font-semibold ${atk ? "text-destructive" : "text-success"}`}>
                      {r.predicted_class}
                    </span>
                    <span className="ml-auto text-[10px] font-mono text-muted-foreground">
                      {(r.confidence * 100).toFixed(1)}%
                    </span>
                    <ChevronRight className={`h-3.5 w-3.5 ${isSel ? "text-primary" : "text-muted-foreground/40"}`} />
                  </div>
                  <div className="mt-1 flex items-center gap-2 pl-10">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                      {r.cert_in_category}
                    </span>
                    <StatusChip status={r.prevention.status} severity={r.prevention.severity} />
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="space-y-6">
          {selected && (
            <div className="glass rounded-3xl p-6">
              <div className="flex flex-wrap items-center gap-3">
                <div
                  className={`inline-flex items-center gap-2 rounded-xl px-3 py-1.5 border ${
                    selected.predicted_class !== "BENIGN"
                      ? "border-destructive/40 bg-destructive/10 text-destructive"
                      : "border-success/40 bg-success/10 text-success"
                  }`}
                >
                  {selected.predicted_class !== "BENIGN" ? (
                    <ShieldAlert className="h-4 w-4" />
                  ) : (
                    <ShieldCheck className="h-4 w-4" />
                  )}
                  <span className="font-display text-sm uppercase tracking-wide">
                    Window #{selectedIdx} · {selected.predicted_class}
                  </span>
                </div>
                {selected.low_confidence_class && (
                  <span className="inline-flex items-center gap-1.5 rounded-lg border border-warning/40 bg-warning/10 px-2.5 py-1 text-[11px] font-mono uppercase tracking-wider text-warning">
                    <AlertTriangle className="h-3 w-3" />
                    Low-confidence class
                  </span>
                )}
                <span className="ml-auto text-xs font-mono text-muted-foreground">
                  confidence {(selected.confidence * 100).toFixed(1)}%
                </span>
              </div>

              <div className="mt-5 grid md:grid-cols-3 gap-4">
                <MetricInline label="CERT-In Category" value={selected.cert_in_category} tone={selected.predicted_class !== "BENIGN" ? "danger" : "muted"} />
                <MetricInline label="Severity" value={selected.prevention.severity.toUpperCase()} tone={severityTone(selected.prevention.severity)} />
                <MetricInline label="Policy Action" value={selected.prevention.action.replace(/_/g, " ")} />
              </div>

              <div className={`mt-5 rounded-xl border p-4 flex items-start gap-3 ${
                selected.prevention.status === "auto_action"
                  ? "border-destructive/40 bg-destructive/5"
                  : selected.prevention.status === "held_for_review"
                  ? "border-warning/40 bg-warning/5"
                  : "border-success/40 bg-success/5"
              }`}>
                <Gavel className={`h-5 w-5 mt-0.5 shrink-0 ${
                  selected.prevention.status === "auto_action"
                    ? "text-destructive"
                    : selected.prevention.status === "held_for_review"
                    ? "text-warning"
                    : "text-success"
                }`} />
                <div>
                  <div className="text-sm font-semibold">
                    {selected.prevention.status === "auto_action"
                      ? "Automated response executed"
                      : selected.prevention.status === "held_for_review"
                      ? "Flagged for analyst review"
                      : "No action required"}
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    Policy: <span className="font-mono">{selected.prevention.action}</span> · threshold logic calibrated per-class from baseline F1 scores.
                    {selected.low_confidence_class &&
                      " Note: this class has known poor recall — treat confidence as indicative only."}
                  </div>
                </div>
              </div>

              <div className="mt-6">
                <div className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground mb-3">
                  Class Probability Breakdown
                </div>
                <ProbabilityBreakdown probabilities={selected.probabilities} />
              </div>
            </div>
          )}

          <ShapPanel
            explanation={explanation}
            state={explainState}
            error={explainError}
            selectedClass={selected?.predicted_class ?? ""}
          />
        </div>
      </div>
    </div>
  );
}

function RadialGauge({ value }: { value: number }) {
  return (
    <RadialBarChart innerRadius="70%" outerRadius="100%" startAngle={210} endAngle={-30}>
      <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
      <RadialBar background={{ fill: CHART_BG }} dataKey="value" cornerRadius={20} fill="#e5484d" data={[{ value }]} />
    </RadialBarChart>
  );
}

function StatusChip({ status, severity }: { status: string; severity: string }) {
  if (status === "no_action_needed")
    return (
      <span className="rounded-md bg-success/10 border border-success/30 px-1.5 py-0.5 text-[9px] font-mono uppercase text-success">
        clear
      </span>
    );
  if (status === "auto_action")
    return (
      <span className="rounded-md bg-destructive/10 border border-destructive/30 px-1.5 py-0.5 text-[9px] font-mono uppercase text-destructive">
        auto · {severity}
      </span>
    );
  return (
    <span className="rounded-md bg-warning/10 border border-warning/30 px-1.5 py-0.5 text-[9px] font-mono uppercase text-warning">
      review
    </span>
  );
}

function ProbabilityBreakdown({ probabilities }: { probabilities: Record<string, number> }) {
  const entries = Object.entries(probabilities).sort((a, b) => b[1] - a[1]);
  const max = entries[0]?.[1] || 1;
  return (
    <div className="space-y-2">
      {entries.map(([name, v]) => (
        <div key={name} className="flex items-center gap-3">
          <span className="w-44 shrink-0 truncate font-mono text-xs text-muted-foreground">{name}</span>
          <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${(v / max) * 100}%`,
                backgroundColor: classColor(name),
                opacity: 0.85,
              }}
            />
          </div>
          <span className="w-14 text-right text-xs font-mono">{(v * 100).toFixed(2)}%</span>
        </div>
      ))}
    </div>
  );
}

function ShapPanel({
  explanation,
  state,
  error,
  selectedClass,
}: {
  explanation: ExplainResponse | null;
  state: "idle" | "loading" | "error";
  error: string | null;
  selectedClass: string;
}) {
  if (state === "loading") {
    return (
      <div className="glass rounded-3xl p-6">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <h3 className="heading-card">SHAP Explanation</h3>
        </div>
        <div className="mt-8 flex flex-col items-center gap-3 pb-8">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <p className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
            GradientExplainer · computing attributions...
          </p>
        </div>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="glass rounded-3xl p-6 border-destructive/40">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-destructive" />
          <h3 className="heading-card">SHAP Explanation unavailable</h3>
        </div>
        <p className="mt-3 text-sm text-destructive/90">{error}</p>
      </div>
    );
  }

  if (!explanation) return null;

  const attrs = explanation.attributions;
  const chartData = attrs.map((a) => ({
    name: a.feature,
    shap: a.shap_value,
    abs: Math.abs(a.shap_value),
  }));
  const maxAbs = Math.max(...chartData.map((d) => d.abs), 1e-9);

  const narrativeTop = attrs.slice(0, 3);
  const narrative = `The model leaned on ${narrativeTop
    .map(
      (a) =>
        `${a.feature} (${a.shap_value >= 0 ? "+" : ""}${a.shap_value.toFixed(3)}, pushing toward ${selectedClass})`
    )
    .join(", ")}. Features shown in red increased the ${selectedClass} score from the baseline of ${explanation.base_value.toFixed(
    3
  )} up to ${explanation.f_x.toFixed(3)}; blue features argued against it.`;

  return (
    <div className="space-y-6 fade-up">
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="h-4 w-4 text-primary" />
          <h3 className="heading-card">SHAP Explanation</h3>
          <span className="ml-2 text-[10px] font-mono uppercase tracking-widest text-success">
            GradientExplainer · Window #{explanation.window}
          </span>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          <ChartCard title="Feature Attributions" subtitle={`Contribution toward "${explanation.predicted_class}" · red pushes up, blue pulls down`}>
            <ResponsiveContainer width="100%" height={Math.max(260, attrs.length * 26)}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 20 }}>
                <XAxis type="number" domain={[-maxAbs, maxAbs]} hide />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} width={150} tick={{ fill: CHART_TEXT, fontSize: 10 }} />
                <Tooltip
                  cursor={{ fill: "rgba(79, 70, 229, 0.15)" }}
                  contentStyle={{ background: CHART_BG, border: `1px solid ${CHART_GRID}`, borderRadius: 10, fontSize: 12 }}
                  formatter={(v: number) => v.toFixed(4)}
                />
                <ReferenceLine x={0} stroke={CHART_GRID} />
                <Bar dataKey="shap" radius={[4, 4, 4, 4]}>
                  {chartData.map((d) => (
                    <Cell key={d.name} fill={d.shap >= 0 ? "#e5484d" : "#4f46e5"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <div className="space-y-6">
            <div className="glass rounded-3xl p-6">
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-primary" />
                <h4 className="heading-card">What the model saw</h4>
              </div>
              <p className="mt-4 text-sm text-muted-foreground leading-relaxed">{narrative}</p>
              <div className="mt-4 grid grid-cols-3 gap-3 text-center">
                <MiniStat label="Base rate" value={explanation.base_value.toFixed(3)} />
                <MiniStat label="Model output" value={explanation.f_x.toFixed(3)} highlight />
                <MiniStat label="Confidence" value={`${(explanation.confidence * 100).toFixed(1)}%`} />
              </div>
              <div className="mt-4 flex items-start gap-2 rounded-xl border border-primary/25 bg-primary/5 p-3">
                <Lightbulb className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                <p className="text-xs text-muted-foreground">
                  SHAP values decompose the softmax score for the predicted class into per-feature contributions, averaged over the 10 timesteps of the sequence window.
                </p>
              </div>
            </div>

            <div className="glass rounded-3xl p-6">
              <div className="flex items-center gap-2">
                <ListOrdered className="h-4 w-4 text-primary" />
                <h4 className="heading-card">Waterfall — Top Contributors</h4>
              </div>
              <div className="mt-4 space-y-2.5">
                {attrs.slice(0, 6).map((a, i) => (
                  <div key={a.feature} className="flex items-center gap-3">
                    <span className="h-6 w-6 shrink-0 rounded-md grid place-items-center bg-primary/15 border border-primary/30 text-[10px] font-mono text-primary">
                      {i + 1}
                    </span>
                    <span className="font-mono text-xs truncate flex-1">{a.feature}</span>
                    <div className="w-28 h-1.5 rounded-full bg-white/5 overflow-hidden shrink-0">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${(Math.abs(a.shap_value) / maxAbs) * 100}%`,
                          backgroundColor: a.shap_value >= 0 ? "#e5484d" : "#4f46e5",
                        }}
                      />
                    </div>
                    <span
                      className={`w-16 text-right text-[11px] font-mono ${
                        a.shap_value >= 0 ? "text-destructive" : "text-primary"
                      }`}
                    >
                      {a.shap_value >= 0 ? "+" : ""}
                      {a.shap_value.toFixed(3)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MiniStat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.03] p-3">
      <div className="text-[9px] font-mono uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className={`mt-1 font-display text-xl ${highlight ? "bg-gradient-to-r from-primary to-[#a78bfa] bg-clip-text text-transparent" : ""}`}>
        {value}
      </div>
    </div>
  );
}

function MetricInline({
  label,
  value,
  tone,
  icon: Icon,
}: {
  label: string;
  value: string;
  tone?: "danger" | "warning" | "muted";
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div>
      <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground flex items-center gap-1">
        {Icon && <Icon className="h-3 w-3" />}
        {label}
      </div>
      <div
        className={`mt-1 font-display text-lg uppercase tracking-wide truncate ${
          tone === "danger" ? "text-destructive" : tone === "warning" ? "text-warning" : "text-foreground"
        }`}
      >
        {value}
      </div>
    </div>
  );
}

function ChartCard({
  title,
  subtitle,
  children,
  className,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`glass rounded-3xl p-6 transition-all duration-300 hover:shadow-[0_20px_60px_-30px_rgba(79,70,229,0.5)] ${className ?? ""}`}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="heading-card">{title}</h3>
          {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}
