import { useCallback, useEffect, useRef, useState } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  Upload,
  ShieldAlert,
  ShieldCheck,
  Radio,
  FileText,
  X,
  Gavel,
  Eye,
} from "lucide-react";
import {
  BarChart,
  Bar,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";
import { streamLoad, streamNext, type PredictionResult } from "@/lib/api";

const CHART_BG = "#141432";
const CHART_GRID = "rgba(79, 70, 229, 0.15)";
const CHART_TEXT = "#a0a0b8";
const POLL_MS = 1200;
const FEED_CAP = 60;

type Phase = "idle" | "loading" | "running" | "paused" | "done" | "error";

interface FeedEntry {
  window: number;
  predicted_class: string;
  cert_in_category: string;
  confidence: number;
  status: string;
}

export function LiveFeed() {
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [total, setTotal] = useState(0);
  const [cursor, setCursor] = useState(0);
  const [current, setCurrent] = useState<PredictionResult | null>(null);
  const [feed, setFeed] = useState<FeedEntry[]>([]);
  const [counts, setCounts] = useState({ threats: 0, normal: 0 });
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<number | null>(null);

  const stopTimer = () => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  useEffect(() => stopTimer, []);

  const tick = useCallback(async () => {
    try {
      const res = await streamNext();
      if (res.done || !res.result) {
        stopTimer();
        setPhase("done");
        return;
      }
      const r = res.result;
      setCurrent(r);
      setCursor((r.window ?? 0) + 1);
      setCounts((c) =>
        r.predicted_class === "BENIGN"
          ? { ...c, normal: c.normal + 1 }
          : { ...c, threats: c.threats + 1 }
      );
      setFeed((f) =>
        [
          {
            window: r.window ?? 0,
            predicted_class: r.predicted_class,
            cert_in_category: r.cert_in_category,
            confidence: r.confidence,
            status: r.prevention.status,
          },
          ...f,
        ].slice(0, FEED_CAP)
      );
    } catch (e) {
      stopTimer();
      setError(e instanceof Error ? e.message : "Stream failed");
      setPhase("error");
    }
  }, []);

  useEffect(() => {
    if (phase === "running") {
      stopTimer();
      timerRef.current = window.setInterval(tick, POLL_MS);
      return stopTimer;
    }
  }, [phase, tick]);

  const start = async () => {
    if (!file) return;
    setPhase("loading");
    setError(null);
    setFeed([]);
    setCurrent(null);
    setCounts({ threats: 0, normal: 0 });
    try {
      const res = await streamLoad(file);
      setTotal(res.total_windows);
      setPhase("running");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load stream");
      setPhase("error");
    }
  };

  const reset = () => {
    stopTimer();
    setPhase("idle");
    setFile(null);
    setFeed([]);
    setCurrent(null);
    setTotal(0);
    setCursor(0);
    setCounts({ threats: 0, normal: 0 });
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const isAttack = current && current.predicted_class !== "BENIGN";
  const chartData = [...feed]
    .reverse()
    .map((f) => ({
      w: `#${f.window}`,
      threatScore: f.predicted_class === "BENIGN" ? 0 : Math.round(f.confidence * 100),
    }));

  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden glass-strong rounded-3xl p-6 sm:p-10">
        <div className="absolute inset-0 grid-pattern opacity-40 pointer-events-none" />
        <div className="relative grid lg:grid-cols-[1fr_auto] gap-6 items-center">
          <div className="flex items-start gap-5">
            <div className="relative shrink-0 h-14 w-14 grid place-items-center rounded-2xl bg-gradient-to-br from-destructive/70 to-primary">
              <Radio className="h-6 w-6 text-white" />
              <span className="absolute inset-0 rounded-2xl ping-slow bg-destructive/40" />
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="heading-card">Live Traffic Replay</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Streams a stored capture window-by-window — one prediction every{" "}
                {POLL_MS / 1000}s, like real-time monitoring.
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
                  disabled={phase === "running" || phase === "paused"}
                  className="mt-4 w-full sm:w-auto inline-flex items-center gap-2 rounded-xl glass px-4 py-2.5 text-sm font-medium hover:bg-white/5 transition-colors disabled:opacity-40"
                >
                  <Upload className="h-4 w-4 text-primary" />
                  Choose capture CSV
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

          <div className="flex flex-col gap-3 items-stretch sm:items-end">
            {phase === "idle" || phase === "done" || phase === "error" ? (
              <button
                onClick={start}
                disabled={!file}
                className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-primary text-sm font-bold uppercase tracking-tight text-primary-foreground shadow-[8px_8px_0px_#1e1e5a] disabled:opacity-40 hover:enabled:bg-white hover:enabled:text-background active:enabled:scale-95 transition-all duration-300"
              >
                <Play className="h-4 w-4" /> Start Live Stream
              </button>
            ) : (
              <div className="flex gap-2">
                <button
                  onClick={() => setPhase(phase === "running" ? "paused" : "running")}
                  className="inline-flex items-center justify-center gap-2 px-6 py-4 bg-primary text-sm font-bold uppercase tracking-tight text-primary-foreground shadow-[8px_8px_0px_#1e1e5a] hover:bg-white hover:text-background transition-all duration-300"
                >
                  {phase === "running" ? (
                    <>
                      <Pause className="h-4 w-4" /> Pause
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4" /> Resume
                    </>
                  )}
                </button>
                <button
                  onClick={reset}
                  className="inline-flex items-center justify-center gap-2 px-5 py-4 glass rounded-none text-sm font-bold uppercase tracking-tight hover:bg-white/10 transition-all duration-300"
                >
                  <RotateCcw className="h-4 w-4" /> Stop
                </button>
              </div>
            )}
            {(phase === "running" || phase === "paused") && (
              <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-widest">
                {phase === "running" ? (
                  <>
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="absolute inline-flex h-full w-full rounded-full bg-destructive opacity-75 animate-ping" />
                      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-destructive" />
                    </span>
                    <span className="text-destructive">Streaming</span>
                  </>
                ) : (
                  <span className="text-warning">Paused</span>
                )}
                <span className="text-muted-foreground ml-2">
                  window {cursor} / {total}
                </span>
              </div>
            )}
          </div>
        </div>

        {error && (
          <div className="relative mt-4 rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {phase === "done" && (
          <div className="relative mt-4 rounded-xl border border-success/40 bg-success/10 p-4 text-sm text-success font-mono">
            Stream complete — replayed {total} windows.
          </div>
        )}
      </div>

      {(phase === "running" || phase === "paused" || phase === "done") && (
        <div className="grid xl:grid-cols-[380px_1fr] gap-6 items-start">
          <div className="space-y-6">
            <div
              className={`glass-strong rounded-3xl p-6 border ${
                !current ? "" : isAttack ? "border-destructive/40" : "border-success/40"
              }`}
            >
              <div className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">
                Latest Detection {current ? `· Window #${current.window}` : ""}
              </div>
              {!current ? (
                <p className="mt-6 text-sm text-muted-foreground">Waiting for first window...</p>
              ) : (
                <>
                  <div className="mt-3 flex items-center gap-4">
                    <div
                      className={`h-16 w-16 shrink-0 grid place-items-center rounded-2xl border ${
                        isAttack
                          ? "bg-destructive/15 border-destructive/40"
                          : "bg-success/15 border-success/40"
                      }`}
                    >
                      {isAttack ? (
                        <ShieldAlert className="h-8 w-8 text-destructive" />
                      ) : (
                        <ShieldCheck className="h-8 w-8 text-success" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <div
                        className={`font-display text-2xl uppercase tracking-wide truncate ${
                          isAttack ? "text-destructive" : "text-success"
                        }`}
                      >
                        {current.predicted_class}
                      </div>
                      <div className="text-xs text-muted-foreground font-mono mt-0.5">
                        {current.cert_in_category} · {(current.confidence * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 h-2 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        isAttack ? "bg-destructive" : "bg-success"
                      }`}
                      style={{ width: `${current.confidence * 100}%` }}
                    />
                  </div>

                  <div className="mt-4 flex items-center gap-2 text-xs">
                    {current.prevention.status === "auto_action" ? (
                      <span className="inline-flex items-center gap-1.5 rounded-lg border border-destructive/40 bg-destructive/10 px-2.5 py-1 font-mono uppercase text-destructive">
                        <Gavel className="h-3 w-3" /> {current.prevention.action.replace(/_/g, " ")}
                      </span>
                    ) : current.prevention.status === "held_for_review" ? (
                      <span className="inline-flex items-center gap-1.5 rounded-lg border border-warning/40 bg-warning/10 px-2.5 py-1 font-mono uppercase text-warning">
                        <Eye className="h-3 w-3" /> held for review
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 rounded-lg border border-success/40 bg-success/10 px-2.5 py-1 font-mono uppercase text-success">
                        no action needed
                      </span>
                    )}
                  </div>
                </>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="glass rounded-2xl p-5">
                <div className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">
                  Threats
                </div>
                <div className="mt-2 font-display text-3xl text-destructive">{counts.threats}</div>
              </div>
              <div className="glass rounded-2xl p-5">
                <div className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">
                  Normal
                </div>
                <div className="mt-2 font-display text-3xl text-success">{counts.normal}</div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="glass rounded-3xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="heading-card">Threat Confidence Stream</h3>
                <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
                  last {chartData.length} windows
                </span>
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData}>
                  <XAxis dataKey="w" hide />
                  <YAxis domain={[0, 100]} tick={{ fill: CHART_TEXT, fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ background: CHART_BG, border: `1px solid ${CHART_GRID}`, borderRadius: 10, fontSize: 12 }}
                    formatter={(v: number) => [`${v}%`, "confidence"]}
                  />
                  <Bar dataKey="threatScore" radius={[4, 4, 0, 0]}>
                    {chartData.map((d) => (
                      <Cell key={d.w} fill={d.threatScore >= 50 ? "#e5484d" : "#4f46e5"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="glass rounded-3xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="heading-card">Detection Log</h3>
                <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
                  newest first
                </span>
              </div>
              <div className="max-h-[320px] overflow-y-auto pr-1 space-y-1">
                {feed.length === 0 && (
                  <p className="text-sm text-muted-foreground">No detections yet.</p>
                )}
                {feed.map((f) => {
                  const atk = f.predicted_class !== "BENIGN";
                  return (
                    <div
                      key={f.window}
                      className={`rounded-xl px-3 py-2 border flex items-center gap-3 ${
                        atk ? "border-destructive/30 bg-destructive/5" : "border-transparent bg-white/[0.02]"
                      }`}
                    >
                      <span className="text-[10px] font-mono text-muted-foreground w-12 shrink-0">
                        #{f.window}
                      </span>
                      <span className={`text-xs font-semibold ${atk ? "text-destructive" : "text-success"}`}>
                        {f.predicted_class}
                      </span>
                      <span className="text-[10px] font-mono uppercase text-muted-foreground hidden sm:inline">
                        {f.cert_in_category}
                      </span>
                      <span className="ml-auto text-[11px] font-mono text-muted-foreground">
                        {(f.confidence * 100).toFixed(1)}%
                      </span>
                      {atk && f.status === "auto_action" && (
                        <Gavel className="h-3.5 w-3.5 text-destructive shrink-0" />
                      )}
                      {atk && f.status === "held_for_review" && (
                        <Eye className="h-3.5 w-3.5 text-warning shrink-0" />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
