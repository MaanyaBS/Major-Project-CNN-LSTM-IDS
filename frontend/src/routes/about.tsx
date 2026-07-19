import { createFileRoute } from "@tanstack/react-router";
import {
  Shield,
  Brain,
  Layers,
  Target,
  Zap,
  GitBranch,
  Database,
  Cpu,
  BarChart3,
  ShieldCheck,
  Eye,
  Gauge,
  Rocket,
  Server,
  Sparkles,
  Network,
  LineChart,
  Radio,
} from "lucide-react";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "About — ThreatLens AI · CNN-LSTM IDS" },
      { name: "description", content: "About ThreatLens AI — the CNN-LSTM based network intrusion detection system: architecture, objectives, technology stack and future scope." },
    ],
  }),
  component: About,
});

const concepts = [
  {
    icon: Shield,
    title: "Intrusion Detection System",
    body: "An IDS observes network flows in flight and raises alerts when patterns deviate from normal — the visibility layer above a firewall.",
  },
  {
    icon: Cpu,
    title: "CNN",
    body: "1D convolutions extract local spatial patterns from flow features: byte counts, packet lengths, flag distributions.",
  },
  {
    icon: Brain,
    title: "LSTM",
    body: "Recurrent layers model temporal behaviour — how packet bursts and session state evolve second by second.",
  },
  {
    icon: Network,
    title: "Why CNN + LSTM",
    body: "Attacks leave both structural fingerprints and time-based signatures; combining both gives the classifier a stereoscopic view.",
  },
  {
    icon: Eye,
    title: "Explainable AI (SHAP)",
    body: "Placeholder for SHAP-based attributions — surfacing which features pushed the model toward its verdict, so analysts can trust it.",
  },
  {
    icon: BarChart3,
    title: "Multi-Class Output",
    body: "A softmax head yields per-class probabilities across DDoS, DoS, port scan, brute force, web attack and normal.",
  },
];

const timeline = [
  { icon: Database, title: "Data Acquisition", desc: "Labelled flow datasets such as CIC-IDS 2017/2018 for training and evaluation." },
  { icon: GitBranch, title: "Preprocessing", desc: "Clean, encode categorical fields, normalise features and window flows for sequence modelling." },
  { icon: Cpu, title: "CNN Feature Extraction", desc: "1D convolutions capture local patterns across packet and flow features." },
  { icon: Brain, title: "LSTM Temporal Modelling", desc: "Recurrent layers learn how attacks unfold over time." },
  { icon: BarChart3, title: "Classification & Evaluation", desc: "Softmax head produces per-class probabilities; metrics: accuracy, precision, recall, F1." },
  { icon: ShieldCheck, title: "Deployment & Explanation", desc: "Serve predictions through this dashboard with feature attributions." },
];

const objectives = [
  { icon: Target, text: "Build a hybrid CNN-LSTM model that outperforms single-architecture baselines." },
  { icon: Layers, text: "Detect multiple attack categories, not just binary normal-vs-attack." },
  { icon: Zap, text: "Keep inference latency low enough for near real-time monitoring." },
  { icon: Eye, text: "Surface explanations so analysts trust and act on model output." },
  { icon: Gauge, text: "Provide a clean, presentable interface suitable for demonstrations." },
  { icon: Shield, text: "Document the pipeline end-to-end for reproducibility." },
];

const stack = [
  { label: "React", desc: "UI layer", tone: "primary" },
  { label: "TypeScript", desc: "Type safety", tone: "primary" },
  { label: "TanStack Start", desc: "Routing & SSR", tone: "primary" },
  { label: "Recharts", desc: "Data viz", tone: "primary" },
  { label: "Python", desc: "Model runtime", tone: "accent" },
  { label: "TensorFlow", desc: "CNN-LSTM engine", tone: "accent" },
  { label: "Flask", desc: "Inference API", tone: "accent" },
  { label: "SHAP", desc: "Explainability", tone: "accent" },
];

const architecture = [
  { icon: Radio, label: "Flow Capture", sub: "CSV / PCAP" },
  { icon: GitBranch, label: "Preprocess", sub: "Normalise · Window" },
  { icon: Cpu, label: "CNN", sub: "Spatial features" },
  { icon: Brain, label: "LSTM", sub: "Temporal features" },
  { icon: BarChart3, label: "Softmax", sub: "Multi-class" },
  { icon: Eye, label: "SHAP", sub: "Explainability" },
];

const future = [
  { icon: Radio, title: "Live Packet Streaming", desc: "Wire the pipeline to real-time packet sniffers instead of static captures." },
  { icon: Server, title: "Distributed Inference", desc: "Scale the Flask endpoint horizontally with a queue and model workers." },
  { icon: Sparkles, title: "Adaptive Retraining", desc: "Continuous learning as new attack variants emerge in the wild." },
  { icon: LineChart, title: "Full SHAP Explanations", desc: "Per-flow force plots and global feature importance surfaced in the UI." },
];

function About() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-16 space-y-20">
      {/* Intro */}
      <section className="relative fade-up">
        <div className="absolute -top-16 -left-16 h-64 w-64 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute top-10 right-0 h-64 w-64 rounded-full bg-[#8b5cf6]/10 blur-3xl" />
        <div className="relative">
          <div className="inline-flex items-center gap-2 heading-kicker">
            <span className="h-px w-6 bg-primary" />
            Project Brief
          </div>
          <h1 className="mt-3 heading-hero">
            About <br />
            <span className="bg-gradient-to-r from-primary via-[#a78bfa] to-primary bg-clip-text text-transparent">ThreatLens AI</span>
          </h1>
          <p className="mt-5 text-base sm:text-lg text-muted-foreground max-w-3xl leading-relaxed">
            A hybrid CNN-LSTM based Network Intrusion Detection System — engineered as a final-year
            project to demonstrate how deep learning and explainable AI can work together for
            real-time cyber defence.
          </p>
        </div>
      </section>

      {/* Concept cards */}
      <section className="fade-up">
        <div className="inline-flex items-center gap-2 heading-kicker">
          <span className="h-px w-6 bg-primary" />
          Core Concepts
        </div>
        <h2 className="mt-3 heading-section">The building blocks</h2>
        <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {concepts.map((c) => (
            <div key={c.title} className="glass rounded-2xl p-5 transition-all duration-300 hover:-translate-y-1 hover:border-primary/50 hover:shadow-[0_20px_50px_-20px_rgba(139,92,246,0.4)]">
              <div className="h-11 w-11 rounded-xl grid place-items-center bg-gradient-to-br from-primary/20 to-[#8b5cf6]/30 border border-primary/30">
                <c.icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mt-4 heading-card">{c.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{c.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Architecture diagram */}
      <section className="fade-up">
        <div className="inline-flex items-center gap-2 heading-kicker">
          <span className="h-px w-6 bg-primary" />
          Architecture
        </div>
        <h2 className="mt-3 heading-section">CNN-LSTM Workflow</h2>

        <div className="mt-8 glass-strong rounded-3xl p-6 sm:p-10 relative overflow-hidden">
          <div className="absolute inset-0 grid-pattern opacity-30 pointer-events-none" />
          <div className="relative flex flex-wrap items-center justify-center gap-3">
            {architecture.map((a, i) => (
              <div key={a.label} className="flex items-center gap-3">
                <div className="glass rounded-2xl px-4 py-4 min-w-[130px] text-center">
                  <div className="mx-auto h-10 w-10 rounded-xl grid place-items-center bg-gradient-to-br from-primary to-[#8b5cf6] shadow-[0_0_20px_rgba(139,92,246,0.5)]">
                    <a.icon className="h-4 w-4 text-primary-foreground" />
                  </div>
                  <div className="mt-2 font-display text-sm uppercase tracking-wide">{a.label}</div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mt-1">{a.sub}</div>
                </div>
                {i < architecture.length - 1 && (
                  <div className="hidden sm:flex flex-col items-center">
                    <div className="h-px w-6 bg-gradient-to-r from-primary/60 to-[#a78bfa]/60" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Timeline */}
      <section className="fade-up">
        <div className="inline-flex items-center gap-2 heading-kicker">
          <span className="h-px w-6 bg-primary" />
          Workflow
        </div>
        <h2 className="mt-3 heading-section">Project pipeline</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          From raw dataset to a live analyst-facing dashboard.
        </p>

        <ol className="mt-10 relative space-y-6 pl-8 sm:pl-10 before:absolute before:left-4 sm:before:left-5 before:top-2 before:bottom-2 before:w-px before:bg-gradient-to-b before:from-primary/60 before:via-[#8b5cf6]/40 before:to-transparent">
          {timeline.map((s, i) => (
            <li key={s.title} className="relative">
              <span className="absolute -left-8 sm:-left-10 top-0 grid place-items-center h-9 w-9 rounded-xl bg-gradient-to-br from-primary to-[#8b5cf6] shadow-[0_0_20px_rgba(139,92,246,0.4)]">
                <s.icon className="h-4 w-4 text-primary-foreground" />
              </span>
              <div className="glass rounded-2xl p-5 hover:border-primary/40 transition-colors">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                    Phase 0{i + 1}
                  </span>
                </div>
                <h3 className="mt-1 heading-card">{s.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground leading-relaxed">{s.desc}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* Objectives */}
      <section className="fade-up">
        <div className="inline-flex items-center gap-2 heading-kicker">
          <span className="h-px w-6 bg-primary" />
          Objectives
        </div>
        <h2 className="mt-3 heading-section">Project objectives</h2>

        <ul className="mt-8 grid sm:grid-cols-2 gap-4">
          {objectives.map((o) => (
            <li key={o.text} className="glass rounded-2xl p-5 flex items-start gap-4 transition-all hover:-translate-y-0.5 hover:border-primary/40">
              <div className="shrink-0 h-10 w-10 rounded-xl grid place-items-center bg-gradient-to-br from-primary/20 to-[#8b5cf6]/30 border border-primary/30">
                <o.icon className="h-4 w-4 text-primary" />
              </div>
              <p className="text-sm leading-relaxed">{o.text}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* Technology stack */}
      <section className="fade-up">
        <div className="inline-flex items-center gap-2 heading-kicker">
          <span className="h-px w-6 bg-primary" />
          Technology Stack
        </div>
        <h2 className="mt-3 heading-section">Built with</h2>
        <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-4">
          {stack.map((s) => (
            <div key={s.label} className="glass rounded-2xl p-5 text-center transition-all hover:-translate-y-1 hover:border-primary/50">
              <div className="font-display text-lg uppercase tracking-wide bg-gradient-to-r from-primary to-[#a78bfa] bg-clip-text text-transparent">
                {s.label}
              </div>
              <div className="mt-1 text-xs text-muted-foreground font-mono uppercase tracking-widest">
                {s.desc}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Future scope */}
      <section className="fade-up">
        <div className="inline-flex items-center gap-2 heading-kicker">
          <span className="h-px w-6 bg-primary" />
          Future Scope
        </div>
        <h2 className="mt-3 heading-section">What comes next</h2>
        <div className="mt-8 grid sm:grid-cols-2 gap-4">
          {future.map((f) => (
            <div key={f.title} className="glass rounded-2xl p-5 flex items-start gap-4 transition-all hover:-translate-y-0.5 hover:border-primary/40">
              <div className="shrink-0 h-11 w-11 rounded-xl grid place-items-center bg-gradient-to-br from-primary to-[#8b5cf6]">
                <f.icon className="h-5 w-5 text-primary-foreground" />
              </div>
              <div>
                <h3 className="heading-card">{f.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer CTA note */}
      <section className="fade-up">
        <div className="relative overflow-hidden glass-strong rounded-3xl p-8 text-center">
          <div className="absolute -top-20 -right-20 h-64 w-64 rounded-full bg-[#8b5cf6]/20 blur-3xl" />
          <Rocket className="h-8 w-8 text-primary mx-auto" />
          <h3 className="mt-3 heading-card">
            ThreatLens AI · Final Year Engineering Project
          </h3>
          <p className="mt-2 text-sm text-muted-foreground max-w-lg mx-auto">
            All predictions currently shown are demo data. The Flask + TensorFlow backend will
            replace the placeholders once wired in.
          </p>
        </div>
      </section>
    </div>
  );
}
