// ThreatLens AI logo — an AI-powered digital lens / neural iris.
// Concentric aperture rings with a scanning pupil and neural node accents.
export function ThreatLensLogo({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="tl-iris" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#a78bfa" />
          <stop offset="1" stopColor="#4f46e5" />
        </linearGradient>
        <radialGradient id="tl-pupil" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.95" />
          <stop offset="0.6" stopColor="#a78bfa" stopOpacity="0.6" />
          <stop offset="1" stopColor="#4f46e5" stopOpacity="0" />
        </radialGradient>
      </defs>
      {/* outer aperture */}
      <circle cx="16" cy="16" r="13" fill="none" stroke="url(#tl-iris)" strokeWidth="1.5" />
      {/* iris tick marks */}
      {Array.from({ length: 8 }).map((_, i) => {
        const a = (i * Math.PI) / 4;
        const x1 = 16 + Math.cos(a) * 10;
        const y1 = 16 + Math.sin(a) * 10;
        const x2 = 16 + Math.cos(a) * 12.5;
        const y2 = 16 + Math.sin(a) * 12.5;
        return (
          <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
            stroke="url(#tl-iris)" strokeWidth="1.2" strokeLinecap="round" opacity={0.85} />
        );
      })}
      {/* neural nodes on ring */}
      <circle cx="16" cy="3" r="1.4" fill="#a78bfa" />
      <circle cx="29" cy="16" r="1.4" fill="#4f46e5" />
      <circle cx="16" cy="29" r="1.4" fill="#a78bfa" />
      <circle cx="3" cy="16" r="1.4" fill="#4f46e5" />
      {/* inner iris */}
      <circle cx="16" cy="16" r="7" fill="none" stroke="url(#tl-iris)" strokeWidth="1" opacity="0.7" />
      {/* pupil glow */}
      <circle cx="16" cy="16" r="6" fill="url(#tl-pupil)" />
      {/* pupil */}
      <circle cx="16" cy="16" r="2.6" fill="#0a0a1a" stroke="#a78bfa" strokeWidth="0.8" />
      <circle cx="16.7" cy="15.3" r="0.7" fill="#ffffff" />
    </svg>
  );
}
