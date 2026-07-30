import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useRef, useState } from "react";
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
  TrendingUp,
  Clock,
  Target,
  Brain,
  Lightbulb,
  ListOrdered,
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
  RadialBarChart,
  RadialBar,
  LineChart,
  Line,
  CartesianGrid,
  Area,
  AreaChart,
} from "recharts";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Threat Analysis Dashboard — ThreatLens AI" },
      { name: "description", content: "Upload network flow CSVs and inspect CNN-LSTM predictions with explainable, per-class results." },
    ],
  }),
  component: Dashboard,
});

type Result = {
  verdict: "attack" | "normal";
  category: string;
  confidence: number;
  risk: "Critical" | "High" | "Medium" | "Low";
  detectionTime: string;
  probs: Record<string, number>;
  features: { name: string; weight: number }[];
  stats: { total: number; normal: number; attacks: number; rate: number; accuracy: number };
  attackInfo: { description: string; severity: string; impact: string; action: string };
  timeline: { t: string; threats: number; normal: number }[];
};

const DEMO_RESULT: Result = {
  verdict: "attack",
  category: "DDoS",
  confidence: 0.947,
  risk: "Critical",
  detectionTime: "142 ms",
  probs: {
    Normal: 0.021,
    DDoS: 0.712,
    DoS: 0.148,
    "Port Scan": 0.062,
    "Brute Force": 0.038,
    "Web Attack": 0.019,
  },
  features: [
    { name: "Flow Bytes/s", weight: 0.28 },
    { name: "Packet Length Std", weight: 0.19 },
    { name: "Fwd IAT Mean", weight: 0.15 },
    { name: "SYN Flag Count", weight: 0.13 },
    { name: "Destination Port", weight: 0.09 },
    { name: "Flow Duration", weight: 0.08 },
  ],
  stats: { total: 12480, normal: 8412, attacks: 4068, rate: 0.326, accuracy: 0.982 },
  attackInfo: {
    description:
      "Distributed Denial-of-Service floods overwhelm a target with traffic from many compromised sources, exhausting bandwidth or session state.",
    severity: "Critical",
    impact:
      "Service unavailability, degraded latency for legitimate users, cascading failures on stateful backends.",
    action:
      "Enable upstream rate limiting, activate scrubbing at the edge, deploy SYN cookies and blackhole offending prefixes at the ISP border.",
  },
  timeline: [
    { t: "00:00", threats: 12, normal: 320 },
    { t: "00:05", threats: 28, normal: 305 },
    { t: "00:10", threats: 45, normal: 298 },
    { t: "00:15", threats: 82, normal: 271 },
    { t: "00:20", threats: 156, normal: 240 },
    { t: "00:25", threats: 210, normal: 225 },
    { t: "00:30", threats: 178, normal: 245 },
    { t: "00:35", threats: 96, normal: 290 },
    { t: "00:40", threats: 54, normal: 312 },
    { t: "00:45", threats: 31, normal: 328 },
  ],
};

const CATEGORY_COLORS: Record<string, string> = {
  Normal: "#10b981",
  DDoS: "#e5484d",
  DoS: "#f5a623",
  "Port Scan": "#4f46e5",
  "Brute Force": "#8b5cf6",
  "Web Attack": "#ec4899",
};

const CHART_BG = "#141432";
const CHART_TEXT = "#a0a0b8";
const CHART_GRID = "rgba(79, 70, 229, 0.15)";

function Dashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [status, setStatus] = useState<"idle" | "analyzing" | "done">("idle");
  const [result, setResult] = useState<Result | null>(null);
  const [progress, setProgress] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) setFile(f);
  }, []);

  const analyze = () => {
    setStatus("analyzing");
    setResult(null);
    setProgress(0);
    const start = Date.now();
    const tick = setInterval(() => {
      const p = Math.min(100, ((Date.now() - start) / 2200) * 100);
      setProgress(p);
      if (p >= 100) clearInterval(tick);
    }, 60);
    setTimeout(() => {
      setResult(DEMO_RESULT);
      setStatus("done");
      setProgress(100);
    }, 2200);
  };

  const reset = () => {
    setFile(null);
    setResult(null);
    setStatus("idle");
    setProgress(0);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 heading-kicker">
            <span className="h-px w-6 bg-primary" />
            Analysis Console
          </div>
          <h1 className="mt-3 heading-hero">
            Threat Analysis <span className="bg-gradient-to-r from-primary to-[#a78bfa] bg-clip-text text-transparent">Dashboard</span>
          </h1>
          <p className="mt-2 text-sm text-muted-foreground max-w-2xl">
            Upload a capture file and let the CNN-LSTM engine classify each flow.
          </p>
        </div>
        <DemoBadge />
      </div>

      {/* Upload */}
      <section
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
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
                Or click to browse. Expected: CIC-IDS style flow features.
              </p>

              {file ? (
                <div className="mt-4 glass rounded-xl p-3 flex items-center gap-3">
                  <FileText className="h-5 w-5 text-primary shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{file.name}</div>
                    <div className="text-xs text-muted-foreground font-mono">
                      {(file.size / 1024).toFixed(1)} KB · {file.type || "text/csv"} · Ready
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

        {status === "analyzing" && (
          <>
            <ScanOverlay />
            <div className="relative mt-4">
              <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
                <span>Progress</span>
                <span>{progress.toFixed(0)}%</span>
              </div>
              <div className="mt-1.5 h-1.5 rounded-full bg-white/5 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-primary to-[#a78bfa] transition-all duration-100"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          </>
        )}
      </section>

      {/* Results */}
      {result ? (
        <ResultView result={result} />
      ) : status !== "analyzing" ? (
        <EmptyState />
      ) : null}
    </div>
  );
}

function DemoBadge() {
  return (
    <div className="inline-flex items-center gap-2 rounded-full glass px-3 py-1.5 text-[11px] font-mono uppercase tracking-widest">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full rounded-full bg-warning opacity-75 animate-ping" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-warning" />
      </span>
      <span className="text-warning">Demo Mode</span>
      <span className="text-muted-foreground">· Model not connected</span>
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
      <div className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-primary/40 to-transparent"
           style={{ animation: "scanX 1.6s linear infinite" }} />
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
        Results, statistics and explanations will appear here after analysis.
      </p>
    </div>
  );
}

function ResultView({ result }: { result: Result }) {
  const probData = Object.entries(result.probs).map(([name, value]) => ({ name, value }));
  const statCards = [
    { label: "Total Flows", value: result.stats.total.toLocaleString(), icon: Activity, tone: "primary" },
    { label: "Normal Traffic", value: result.stats.normal.toLocaleString(), icon: ShieldCheck, tone: "success" },
    { label: "Attacks Detected", value: result.stats.attacks.toLocaleString(), icon: ShieldAlert, tone: "danger" },
    { label: "Detection Accuracy", value: `${(result.stats.accuracy * 100).toFixed(1)}%`, icon: Target, tone: "primary" },
    { label: "Detection Rate", value: `${(result.stats.rate * 100).toFixed(1)}%`, icon: TrendingUp, tone: "primary" },
  ] as const;

  const isAttack = result.verdict === "attack";

  return (
    <div className="space-y-6 fade-up">
      {/* Verdict + confidence radial */}
      <div className="grid lg:grid-cols-3 gap-6">
        <div className={`relative overflow-hidden glass-strong rounded-3xl p-6 lg:col-span-2 ${isAttack ? "border-destructive/40" : "border-success/40"}`}>
          <div className={`absolute -top-24 -right-24 h-64 w-64 rounded-full blur-3xl ${isAttack ? "bg-destructive/25" : "bg-success/20"}`} />
          <div className="relative flex flex-col sm:flex-row items-start sm:items-center gap-6">
            <div className={`relative h-24 w-24 shrink-0 grid place-items-center rounded-2xl ${isAttack ? "bg-destructive/15 border border-destructive/40" : "bg-success/15 border border-success/40"}`}>
              {isAttack ? (
                <ShieldAlert className="h-10 w-10 text-destructive" />
              ) : (
                <ShieldCheck className="h-10 w-10 text-success" />
              )}
              <span className={`absolute inset-0 rounded-2xl ping-slow ${isAttack ? "bg-destructive/30" : "bg-success/30"}`} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">
                Prediction Result · Demo
              </div>
              <div className="mt-1 flex flex-wrap items-baseline gap-3">
                <span className={`font-display text-3xl sm:text-4xl uppercase tracking-wide ${isAttack ? "text-destructive" : "text-success"}`}>
                  {isAttack ? "Attack Detected" : "Normal Traffic"}
                </span>
              </div>
              <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-4">
                <MetricInline label="Attack Category" value={result.category} tone={isAttack ? "danger" : "muted"} />
                <MetricInline label="Confidence" value={`${(result.confidence * 100).toFixed(1)}%`} />
                <MetricInline
                  label="Risk Level"
                  value={result.risk}
                  tone={result.risk === "Critical" ? "danger" : result.risk === "High" ? "warning" : "muted"}
                />
                <MetricInline label="Detection Time" value={result.detectionTime} icon={Clock} />
              </div>
            </div>
          </div>
        </div>

        <div className="glass rounded-3xl p-6">
          <div className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">
            Prediction Confidence
          </div>
          <div className="mt-2 h-48">
            <ResponsiveContainer>
              <RadialBarChart
                innerRadius="70%"
                outerRadius="100%"
                data={[{ name: "conf", value: result.confidence * 100, fill: "#4f46e5" }]}
                startAngle={210}
                endAngle={-30}
              >
                <RadialBar background={{ fill: CHART_BG }} dataKey="value" cornerRadius={20} />
              </RadialBarChart>
            </ResponsiveContainer>
          </div>
          <div className="-mt-32 relative text-center pointer-events-none">
            <div className="font-display text-4xl uppercase tracking-wide bg-gradient-to-r from-primary to-[#a78bfa] bg-clip-text text-transparent">
              {(result.confidence * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground font-mono uppercase tracking-widest mt-1">
              softmax
            </div>
          </div>
          <div className="mt-14" />
        </div>
      </div>

      {/* Network Statistics */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="heading-card">Network Statistics</h3>
          <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Demo Data</span>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {statCards.map((s) => (
            <div key={s.label} className="glass rounded-2xl p-5 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_15px_40px_-15px_rgba(79,70,229,0.4)]">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">
                  {s.label}
                </span>
                <s.icon
                  className={`h-4 w-4 ${
                    s.tone === "danger" ? "text-destructive"
                    : s.tone === "success" ? "text-success"
                    : "text-primary"
                  }`}
                />
              </div>
              <div className="mt-3 font-display text-2xl sm:text-3xl uppercase tracking-wide">{s.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-2 gap-6">
        <ChartCard title="Attack Distribution" subtitle="Per-class softmax output">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={probData} layout="vertical" margin={{ left: 20, right: 20 }}>
              <XAxis type="number" domain={[0, 1]} hide />
              <YAxis
                dataKey="name"
                type="category"
                axisLine={false}
                tickLine={false}
                width={90}
                tick={{ fill: CHART_TEXT, fontSize: 12 }}
              />
              <Tooltip
                cursor={{ fill: "rgba(79, 70, 229, 0.15)" }}
                contentStyle={{
                  background: CHART_BG,
                  border: `1px solid ${CHART_GRID}`,
                  borderRadius: 10,
                  fontSize: 12,
                }}
                formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
              />
              <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                {probData.map((d) => (
                  <Cell key={d.name} fill={CATEGORY_COLORS[d.name] || "#4f46e5"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Traffic Distribution" subtitle="Normal vs attack categories">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={probData}
                dataKey="value"
                nameKey="name"
                innerRadius={60}
                outerRadius={95}
                paddingAngle={3}
                stroke="#0a0a1a"
              >
                {probData.map((d) => (
                  <Cell key={d.name} fill={CATEGORY_COLORS[d.name] || "#4f46e5"} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: CHART_BG,
                  border: `1px solid ${CHART_GRID}`,
                  borderRadius: 10,
                  fontSize: 12,
                }}
                formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2 justify-center">
            {probData.map((d) => (
              <div key={d.name} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: CATEGORY_COLORS[d.name] }}
                />
                {d.name}
              </div>
            ))}
          </div>
        </ChartCard>

        <ChartCard title="Prediction Confidence Over Classes" subtitle="Softmax distribution line view">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={probData} margin={{ left: 0, right: 10, top: 10, bottom: 0 }}>
              <CartesianGrid stroke={CHART_GRID} strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fill: CHART_TEXT, fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: CHART_TEXT, fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
              <Tooltip
                contentStyle={{ background: CHART_BG, border: `1px solid ${CHART_GRID}`, borderRadius: 10, fontSize: 12 }}
                formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
              />
              <Line type="monotone" dataKey="value" stroke="#a78bfa" strokeWidth={2.5} dot={{ fill: "#4f46e5", r: 4 }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Threat Timeline" subtitle="Threats vs normal flows over capture window">
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={result.timeline} margin={{ left: 0, right: 10, top: 10, bottom: 0 }}>
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
              <YAxis tick={{ fill: CHART_TEXT, fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: CHART_BG, border: `1px solid ${CHART_GRID}`, borderRadius: 10, fontSize: 12 }} />
              <Area type="monotone" dataKey="normal" stroke="#4f46e5" fill="url(#areaNormal)" strokeWidth={2} />
              <Area type="monotone" dataKey="threats" stroke="#e5484d" fill="url(#areaThreat)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* AI Explanation — 3 placeholder cards */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="h-4 w-4 text-primary" />
          <h3 className="heading-card">AI Explanation</h3>
          <span className="ml-2 text-[10px] font-mono uppercase tracking-widest text-warning">SHAP · Placeholder</span>
        </div>
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="glass rounded-3xl p-6">
            <div className="flex items-center gap-2">
              <ListOrdered className="h-4 w-4 text-primary" />
              <h4 className="heading-card">Top Influencing Features</h4>
            </div>
            <ul className="mt-5 space-y-3">
              {result.features.slice(0, 4).map((f, i) => (
                <li key={f.name} className="flex items-center gap-3">
                  <span className="h-6 w-6 rounded-md grid place-items-center bg-primary/15 border border-primary/30 text-[10px] font-mono text-primary">
                    {i + 1}
                  </span>
                  <span className="font-mono text-sm">{f.name}</span>
                  <span className="ml-auto text-xs text-muted-foreground">{(f.weight * 100).toFixed(0)}%</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="glass rounded-3xl p-6">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-primary" />
              <h4 className="heading-card">Feature Importance</h4>
            </div>
            <ul className="mt-5 space-y-3">
              {result.features.map((f) => (
                <li key={f.name}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-mono text-xs">{f.name}</span>
                    <span className="text-muted-foreground text-xs">
                      {(f.weight * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="mt-1.5 h-1.5 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-primary to-[#a78bfa]"
                      style={{ width: `${f.weight * 100 * 3}%`, maxWidth: "100%" }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="glass rounded-3xl p-6">
            <div className="flex items-center gap-2">
              <Brain className="h-4 w-4 text-primary" />
              <h4 className="heading-card">Model Explanation</h4>
            </div>
            <p className="mt-4 text-sm text-muted-foreground leading-relaxed">
              The CNN layer extracted a burst pattern in <span className="text-foreground font-mono text-xs">Flow Bytes/s</span> and
              elevated <span className="text-foreground font-mono text-xs">SYN Flag Count</span>, while the LSTM captured a rapid
              sequential rise across sub-second windows. Combined, these patterns are characteristic of a volumetric flood.
            </p>
            <div className="mt-4 flex items-start gap-2 rounded-xl border border-primary/25 bg-primary/5 p-3">
              <Lightbulb className="h-4 w-4 text-primary mt-0.5 shrink-0" />
              <p className="text-xs text-muted-foreground">
                Full SHAP-based attributions will render here once the backend model is connected.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Attack Details */}
      <div className="glass rounded-3xl p-6">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-destructive" />
          <h3 className="heading-card">Attack Details</h3>
          <span className="ml-auto rounded-md bg-destructive/10 border border-destructive/30 px-2 py-0.5 text-xs font-mono text-destructive">
            Severity · {result.attackInfo.severity}
          </span>
        </div>
        <div className="mt-5 grid md:grid-cols-2 gap-6">
          <Detail label="Attack Description" value={result.attackInfo.description} />
          <Detail label="Severity" value={result.attackInfo.severity} />
          <Detail label="Possible Impact" value={result.attackInfo.impact} />
          <Detail label="Recommended Action" value={result.attackInfo.action} />
        </div>
      </div>

      {/* Download */}
      <div className="flex justify-end">
        <button
          onClick={() => alert("Demo mode — report download will be enabled once the backend is connected.")}
          className="group inline-flex items-center gap-2 rounded-xl glass px-5 py-3 text-sm font-semibold hover:bg-primary/10 hover:border-primary/40 transition-all"
        >
          <Download className="h-4 w-4 text-primary transition-transform group-hover:translate-y-0.5" />
          Download Analysis Report
        </button>
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
      <div className={`mt-1 font-display text-lg uppercase tracking-wide ${
        tone === "danger" ? "text-destructive" : tone === "warning" ? "text-warning" : "text-foreground"
      }`}>
        {value}
      </div>
    </div>
  );
}

function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="glass rounded-3xl p-6 transition-all duration-300 hover:shadow-[0_20px_60px_-30px_rgba(79,70,229,0.5)]">
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

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 text-sm leading-relaxed">{value}</dd>
    </div>
  );
}
