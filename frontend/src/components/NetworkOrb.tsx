// Animated cybersecurity radar: concentric rings, spinning sweep, central orb.
// Pure SVG/CSS, no external libs.
export function NetworkOrb() {
  const nodes = [
    { x: 50, y: 20 }, { x: 82, y: 38 }, { x: 88, y: 72 }, { x: 62, y: 88 },
    { x: 28, y: 84 }, { x: 12, y: 60 }, { x: 18, y: 30 }, { x: 40, y: 50 },
    { x: 68, y: 55 }, { x: 55, y: 68 },
  ];
  const links: [number, number][] = [
    [0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 0],
    [7, 0], [7, 1], [7, 5], [7, 6], [8, 1], [8, 2], [8, 9],
    [9, 3], [9, 4], [7, 8],
  ];

  return (
    <div className="relative aspect-square w-full max-w-[520px] mx-auto">
      {/* ambient glow */}
      <div className="absolute inset-0 rounded-full bg-primary/10 blur-3xl" />

      {/* concentric structural rings */}
      <div className="absolute inset-0 grid place-items-center">
        {[1, 0.7, 0.45, 0.22].map((s, i) => (
          <div
            key={i}
            className="absolute rounded-full border border-primary/20"
            style={{ width: `${s * 100}%`, height: `${s * 100}%` }}
          />
        ))}

        {/* radar sweep */}
        <div className="absolute inset-0 rounded-full overflow-hidden radar-sweep">
          <div
            className="absolute left-1/2 top-1/2 h-1/2 w-1/2 origin-top-left"
            style={{
              background:
                "conic-gradient(from 0deg, transparent 0deg, rgba(79, 70, 229, 0.45) 60deg, transparent 120deg)",
              borderTopLeftRadius: "100%",
            }}
          />
        </div>

        {/* central orb */}
        <div className="relative h-16 w-16 rounded-full bg-[#141432] border border-primary/30 flex items-center justify-center overflow-hidden shadow-[0_0_100px_rgba(79,70,229,0.2)]">
          <div className="absolute inset-0 opacity-40 hex-noise" />
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary to-secondary blur-xl opacity-60 animate-pulse" />
          <span className="relative z-10 text-[8px] font-bold text-primary tracking-widest uppercase font-mono">Scan</span>
        </div>
      </div>

      {/* SVG network */}
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full">
        <defs>
          <linearGradient id="line" x1="0" x2="1">
            <stop offset="0" stopColor="#4f46e5" stopOpacity="0.1" />
            <stop offset="0.5" stopColor="#4f46e5" stopOpacity="0.9" />
            <stop offset="1" stopColor="#4f46e5" stopOpacity="0.1" />
          </linearGradient>
        </defs>
        {links.map(([a, b], i) => (
          <line
            key={i}
            x1={nodes[a].x} y1={nodes[a].y}
            x2={nodes[b].x} y2={nodes[b].y}
            stroke="url(#line)"
            strokeWidth="0.25"
            strokeDasharray="2 3"
            style={{ animation: `data-flow ${2 + (i % 4)}s ease-in-out ${i * 0.2}s infinite` }}
          />
        ))}
        {nodes.map((n, i) => (
          <g key={i}>
            <circle cx={n.x} cy={n.y} r="1.6" fill="#4f46e5" />
            <circle cx={n.x} cy={n.y} r="3" fill="rgba(79, 70, 229, 0.15)">
              <animate attributeName="r" values="2;5;2" dur={`${2 + (i % 3)}s`} repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.6;0;0.6" dur={`${2 + (i % 3)}s`} repeatCount="indefinite" />
            </circle>
          </g>
        ))}
      </svg>

      {/* floating data points */}
      <div className="absolute top-1/4 left-10 w-2 h-2 rounded-full bg-white shadow-[0_0_15px_white]" />
      <div className="absolute bottom-1/3 right-4 w-2 h-2 rounded-full bg-primary shadow-[0_0_15px_#4f46e5]" />
      <div className="absolute top-10 right-1/4 w-1 h-1 rounded-full bg-white/40" />
    </div>
  );
}
