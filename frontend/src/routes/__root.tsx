import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";
import { Activity, Info, Home, Github, BookOpen } from "lucide-react";
import { ThreatLensLogo } from "@/components/ThreatLensLogo";



import appCss from "../styles.css?url";
import { reportLovableError } from "../lib/lovable-error-reporting";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="max-w-md text-center glass rounded-2xl p-10">
        <h1 className="font-display text-8xl uppercase tracking-tight text-gradient">404</h1>
        <h2 className="mt-4 font-display text-2xl uppercase tracking-wide">Signal lost</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          This endpoint is not on the network map.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Return to base
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="max-w-md text-center glass rounded-2xl p-10">
        <h1 className="font-display text-xl uppercase tracking-wide">Anomaly detected</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          The interface encountered an unexpected error.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => { router.invalidate(); reset(); }}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            Retry scan
          </button>
          <a
            href="/"
            className="rounded-md border border-input px-4 py-2 text-sm font-medium"
          >
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "ThreatLens AI — CNN-LSTM Network Intrusion Detection" },
      { name: "description", content: "ThreatLens AI is an intelligent intrusion detection platform using a hybrid CNN-LSTM model with explainable AI to identify malicious network activity in real time." },
      { name: "author", content: "ThreatLens AI" },
      { property: "og:title", content: "ThreatLens AI — CNN-LSTM Network Intrusion Detection" },
      { property: "og:description", content: "AI-powered network threat detection & analysis with a hybrid CNN-LSTM model and explainable insights." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});


function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function NavBar() {
  const links = [
    { to: "/", label: "Home", icon: Home },
    { to: "/dashboard", label: "Analysis", icon: Activity },
    { to: "/about", label: "About", icon: Info },
  ] as const;

  return (
    <header className="sticky top-0 z-50 w-full">
      <div className="mx-auto max-w-7xl px-4 pt-4">
        <nav className="glass rounded-2xl px-4 py-3 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="relative h-10 w-10 grid place-items-center rounded-xl bg-gradient-to-br from-primary/20 to-[#8b5cf6]/20 border border-primary/30 shadow-[0_0_24px_rgba(79,70,229,0.35)] transition-transform group-hover:scale-105">
              <ThreatLensLogo className="h-6 w-6" />
              <span className="absolute inset-0 rounded-xl ping-slow bg-primary/25" />
            </div>
            <div className="flex flex-col leading-none">
              <span className="font-display text-[1.15rem] font-bold tracking-tight text-foreground">
                ThreatLens <span className="text-primary">AI</span>
              </span>
              <span className="text-[9px] uppercase tracking-[0.25em] text-muted-foreground font-mono mt-0.5">
                CNN · LSTM · IDS
              </span>
            </div>
          </Link>
          <div className="flex items-center gap-1">
            {links.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className="group flex items-center gap-2 rounded-lg px-3 py-2 text-xs sm:text-sm font-medium text-muted-foreground transition-colors hover:text-foreground hover:bg-white/5"
                activeProps={{ className: "text-foreground bg-white/[0.06]" }}
                activeOptions={{ exact: true }}
              >
                <Icon className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">{label}</span>
              </Link>
            ))}
          </div>
        </nav>
      </div>
    </header>
  );
}

function Footer() {
  const stack = ["React", "TypeScript", "Flask", "TensorFlow", "Python", "SHAP"];
  return (
    <footer className="mt-24 border-t border-border/40">
      <div className="absolute left-0 right-0 pointer-events-none">
        <div className="mx-auto max-w-7xl h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />
      </div>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-14">
        <div className="grid gap-10 md:grid-cols-3">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="relative h-10 w-10 grid place-items-center rounded-xl bg-gradient-to-br from-primary/20 to-[#8b5cf6]/20 border border-primary/30">
                <ThreatLensLogo className="h-6 w-6" />
              </div>
              <div className="leading-none">
                <div className="font-display text-lg font-bold tracking-tight">
                  ThreatLens <span className="text-primary">AI</span>
                </div>
                <div className="text-[10px] uppercase tracking-[0.25em] text-muted-foreground font-mono mt-1">
                  Neural Threat Intelligence
                </div>
              </div>
            </div>
            <p className="mt-4 text-sm text-muted-foreground leading-relaxed max-w-sm">
              CNN-LSTM Based Network Intrusion Detection System — a final year engineering project
              exploring hybrid deep learning for real-time cyber defence.
            </p>
          </div>

          <div>
            <div className="heading-kicker">Technologies</div>
            <div className="mt-4 flex flex-wrap gap-2">
              {stack.map((t) => (
                <span
                  key={t}
                  className="rounded-md border border-primary/25 bg-primary/5 px-2.5 py-1 text-xs font-mono text-foreground/80 hover:border-primary/50 transition-colors"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>

          <div>
            <div className="heading-kicker">Resources</div>
            <div className="mt-4 flex flex-col gap-2 text-sm">
              <a
                href="#"
                onClick={(e) => e.preventDefault()}
                className="inline-flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors w-fit"
              >
                <Github className="h-4 w-4" /> GitHub Repository
                <span className="text-[9px] font-mono uppercase tracking-widest text-warning ml-1">soon</span>
              </a>
              <a
                href="#"
                onClick={(e) => e.preventDefault()}
                className="inline-flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors w-fit"
              >
                <BookOpen className="h-4 w-4" /> Documentation
                <span className="text-[9px] font-mono uppercase tracking-widest text-warning ml-1">soon</span>
              </a>
            </div>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-border/40 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-success animate-pulse" />
            <span className="font-mono uppercase tracking-widest">System Online — Demo Mode</span>
          </div>
          <div className="font-mono">© {new Date().getFullYear()} ThreatLens AI · Final Year Engineering Project</div>
        </div>
      </div>
    </footer>
  );
}


function RootComponent() {
  const { queryClient } = Route.useRouteContext();

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen flex flex-col">
        <NavBar />
        <main className="flex-1">
          <Outlet />
        </main>
        <Footer />
      </div>
    </QueryClientProvider>
  );
}
