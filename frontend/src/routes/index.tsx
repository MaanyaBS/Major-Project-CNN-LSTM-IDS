import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Activity,
  Brain,
  Sparkles,
  Upload,
  Cpu,
  FileSearch,
  ArrowRight,
  Zap,
  Layers,
  Eye,
  Radio,
  ShieldCheck,
} from "lucide-react";
import { NetworkOrb } from "@/components/NetworkOrb";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "ThreatLens AI — CNN-LSTM Network Intrusion Detection" },
      { name: "description", content: "ThreatLens AI analyzes network traffic with a hybrid CNN-LSTM model to identify malicious activity in real time, paired with explainable AI insights." },
    ],
  }),
  component: Home,
});

const features = [
  { icon: Radio, title: "Real-Time Traffic Monitoring", desc: "Ingest live network flows and score them the moment they arrive at the sensor." },
  { icon: Brain, title: "AI Threat Detection", desc: "A hybrid CNN-LSTM model spots both spatial and temporal attack signatures." },
  { icon: Layers, title: "Multi-Class Attack Classification", desc: "Distinguish DDoS, DoS, port scans, brute force and web attacks — not just binary alerts." },
  { icon: Eye, title: "Explainable AI Insights", desc: "See which network features pushed the model's decision, ready for SHAP integration." },
];

const pipeline = [
  { icon: Upload, title: "Upload Network Traffic", desc: "Drop in a CSV of flow records from your capture pipeline." },
  { icon: Cpu, title: "Data Preprocessing", desc: "Normalisation, encoding and windowing into model tensors." },
  { icon: Brain, title: "CNN-LSTM Threat Detection", desc: "Hybrid model extracts patterns and classifies each flow." },
  { icon: FileSearch, title: "Threat Analysis & Explainability", desc: "Verdict, category, confidence and feature attribution." },
];

function Home() {
  return (
    <div className="relative">
      {/* HERO */}
      <section className="relative overflow-hidden min-h-[calc(100vh-6rem)] flex items-center">
        <div className="absolute inset-0 grid-pattern opacity-50" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-background/80" />
        <div className="absolute -top-40 -left-40 h-96 w-96 rounded-full bg-primary/15 blur-3xl" />
        <div className="absolute top-1/3 -right-40 h-96 w-96 rounded-full bg-[#8b5cf6]/15 blur-3xl" />

        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 w-full grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7 fade-up">
            <div className="flex items-center gap-4">
              <span className="h-px w-12 bg-primary" />
              <span className="text-[12px] uppercase tracking-[0.3em] font-bold text-primary font-mono">
                Neural Threat Intelligence
              </span>
            </div>

            <h1 className="mt-6 heading-hero">
              ThreatLens
              <br />
              <span className="bg-gradient-to-r from-primary via-[#8b5cf6] to-primary bg-clip-text text-transparent">
                AI.
              </span>
            </h1>

            <p className="mt-4 font-display text-xl sm:text-2xl text-foreground/90 max-w-2xl leading-tight">
              AI-Powered Network Threat Detection &amp; Analysis
            </p>

            <div className="mt-6 max-w-2xl">
              <p className="text-base text-muted-foreground leading-relaxed">
                ThreatLens AI is an intelligent intrusion detection platform that analyzes
                network traffic using a hybrid CNN-LSTM model to identify malicious activity in
                real time. The platform combines deep learning with explainable AI to provide
                accurate predictions and actionable cybersecurity insights.
              </p>
            </div>

            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link
                to="/dashboard"
                className="group relative inline-flex items-center gap-3 px-10 py-5 bg-primary text-primary-foreground font-bold tracking-tight uppercase shadow-[8px_8px_0px_#1e1e5a] transition-all duration-300 hover:bg-white hover:text-background hover:shadow-[4px_4px_0px_#8b5cf6] active:scale-95 overflow-hidden"
              >
                <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                <Zap className="h-4 w-4 relative" />
                <span className="relative">Start Analysis</span>
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1 relative" />
              </Link>
              <div className="h-12 w-px bg-border hidden sm:block" />
              <Link
                to="/about"
                className="group inline-flex items-center gap-2 px-6 py-5 text-foreground/80 font-medium tracking-wide hover:text-foreground transition-colors"
              >
                <Sparkles className="h-4 w-4 text-primary" />
                Learn More
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
            </div>
          </div>

          <div className="lg:col-span-5 relative flex items-center justify-center fade-up" style={{ animationDelay: "0.15s" }}>
            <NetworkOrb />
          </div>
        </div>

        <div className="absolute bottom-0 left-0 right-0 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex justify-between items-end text-[10px] text-muted-foreground/60 tracking-[0.4em] uppercase py-8 border-t border-border/30 font-mono">
          <span>Neural Grid · Alpha-7</span>
          <span>Sensor Uplink: 100%</span>
        </div>
      </section>

      {/* FEATURES */}
      <section className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-20">
        <SectionHeader
          eyebrow="Capabilities"
          title="A command centre for network defence"
          desc="Every module is designed for engineers who need actionable, explainable detections."
        />
        <div className="mt-12 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((f, i) => (
            <div
              key={f.title}
              className="group relative glass rounded-2xl p-5 fade-up transition-all duration-300 hover:-translate-y-1 hover:border-primary/50 hover:shadow-[0_20px_50px_-20px_rgba(139,92,246,0.4)]"
              style={{ animationDelay: `${i * 0.08}s` }}
            >
              <div className="absolute -top-px left-6 right-6 h-px bg-gradient-to-r from-transparent via-primary/60 to-transparent" />
              <div className="h-11 w-11 rounded-xl grid place-items-center bg-gradient-to-br from-primary/20 to-[#8b5cf6]/30 border border-primary/30 group-hover:from-primary/40 group-hover:to-[#8b5cf6]/50 transition-colors">
                <f.icon className="h-5 w-5 text-primary group-hover:text-white transition-colors" />
              </div>
              <h3 className="mt-4 heading-card">{f.title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* PIPELINE */}
      <section className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-20">
        <SectionHeader
          eyebrow="Workflow"
          title="How ThreatLens AI works"
          desc="Four stages, from raw capture file to human-readable verdict."
        />

        <div className="mt-12 relative">
          {/* Animated connecting line */}
          <div className="hidden lg:block absolute top-16 left-[10%] right-[10%] h-px overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/40 to-transparent" />
            <div
              className="absolute inset-y-0 w-24 bg-gradient-to-r from-transparent via-[#a78bfa] to-transparent"
              style={{ animation: "flowPulse 3s linear infinite" }}
            />
          </div>
          <style>{`@keyframes flowPulse { 0% { left: -20%; } 100% { left: 100%; } }`}</style>

          <ol className="grid lg:grid-cols-4 gap-6">
            {pipeline.map((step, i) => (
              <li
                key={step.title}
                className="relative glass rounded-2xl p-6 fade-up transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_20px_50px_-20px_rgba(79,70,229,0.5)]"
                style={{ animationDelay: `${i * 0.1}s` }}
              >
                <div className="flex items-center justify-between">
                  <div className="relative h-12 w-12 rounded-xl grid place-items-center bg-gradient-to-br from-primary to-[#8b5cf6] shadow-[0_0_24px_rgba(139,92,246,0.5)]">
                    <step.icon className="h-5 w-5 text-primary-foreground" />
                    <span className="absolute inset-0 rounded-xl ping-slow bg-primary/30" />
                  </div>
                  <span className="font-mono text-xs text-muted-foreground">
                    STEP · 0{i + 1}
                  </span>
                </div>
                <h3 className="mt-5 heading-card">{step.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{step.desc}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-20">
        <div className="relative overflow-hidden glass-strong rounded-3xl p-8 sm:p-12 text-center">
          <div className="absolute inset-0 grid-pattern opacity-40" />
          <div className="absolute -top-20 -left-20 h-64 w-64 rounded-full bg-primary/20 blur-3xl" />
          <div className="absolute -bottom-20 -right-20 h-64 w-64 rounded-full bg-[#8b5cf6]/30 blur-3xl" />
          <div className="relative">
            <div className="mx-auto h-14 w-14 grid place-items-center rounded-2xl bg-gradient-to-br from-primary/20 to-[#8b5cf6]/30 border border-primary/40">
              <ShieldCheck className="h-6 w-6 text-primary" />
            </div>
            <h2 className="mt-5 heading-section">
              Ready to inspect your first capture?
            </h2>
            <p className="mt-3 text-sm sm:text-base text-muted-foreground max-w-xl mx-auto">
              Load a CSV of flow records and watch ThreatLens AI flag anomalies in real time.
              Demo predictions are labelled clearly.
            </p>
            <Link
              to="/dashboard"
              className="mt-6 group inline-flex items-center gap-2 px-10 py-5 bg-primary text-primary-foreground font-bold tracking-tight uppercase shadow-[8px_8px_0px_#1e1e5a] transition-all duration-300 hover:bg-white hover:text-background hover:shadow-[4px_4px_0px_#8b5cf6] active:scale-95"
            >
              <Activity className="h-4 w-4" />
              Launch Analysis Dashboard
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

function SectionHeader({ eyebrow, title, desc }: { eyebrow: string; title: string; desc: string }) {
  return (
    <div className="max-w-2xl">
      <div className="inline-flex items-center gap-2 heading-kicker">
        <span className="h-px w-6 bg-primary" />
        {eyebrow}
      </div>
      <h2 className="mt-3 heading-section">{title}</h2>
      <p className="mt-3 text-sm sm:text-base text-muted-foreground">{desc}</p>
    </div>
  );
}
