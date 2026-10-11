import type { DroneCatalogDesign } from "../lib/droneCatalog";

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

export function ParametricDronePreview({ design, construction }: { design: DroneCatalogDesign; construction?: { parts: number; massKg: number } }) {
  const config = design.configuration;
  const span = clamp(config.wingspan ?? 2, 0.7, 6);
  const length = clamp(config.fuselageLength ?? 1, 0.4, 2.8);
  const motors = Math.max(1, Math.round(config.motorCount ?? 1));
  const scaleX = 0.74 + (span / 6) * 0.26;
  const scaleY = 0.78 + (length / 2.8) * 0.22;
  const flyingWing = design.key === "fixed-wing";
  const vtol = design.key === "vtol";
  const aerostat = design.modelType === "aérostat";
  const ductedFan = design.modelType === "ducted-fan";
  const label = `${design.label}, aperçu de géométrie paramétrique, ${span.toFixed(1)} mètres d’envergure${construction ? `, ${construction.parts} éléments construits` : ""}`;

  return (
    <svg className="parametric-drone-preview" viewBox="0 0 320 174" role="img" aria-label={label}>
      <defs>
        <linearGradient id={`skin-${design.id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#d9faf4" />
          <stop offset="0.5" stopColor="#57b7ba" />
          <stop offset="1" stopColor="#143e4a" />
        </linearGradient>
        <filter id={`glow-${design.id}`} x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="2.2" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      <g opacity="0.35" stroke="#75e2dc" strokeWidth="0.6">
        {Array.from({ length: 8 }, (_, index) => <line key={`h-${index}`} x1="18" y1={28 + index * 16} x2="302" y2={28 + index * 16} />)}
        {Array.from({ length: 10 }, (_, index) => <line key={`v-${index}`} x1={20 + index * 31} y1="18" x2={20 + index * 31} y2="154" />)}
      </g>
      {aerostat ? (
        <g transform={`translate(160 86) scale(${scaleX} ${scaleY})`} filter={`url(#glow-${design.id})`}>
          <ellipse cx="0" cy="-4" rx="126" ry="37" fill={`url(#skin-${design.id})`} stroke="#c1fff2" strokeWidth="1.4" />
          <path d="M-100 -4 H100 M-82 -24 Q0 -42 82 -24 M-82 16 Q0 34 82 16" fill="none" stroke="#75e2dc" strokeWidth="1" opacity=".75" />
          <path d="M-30 25 L0 42 L30 25" fill="#1c3441" stroke="#8debe0" strokeWidth="1" />
          <circle cx="-20" cy="-4" r="5" fill="#b8fff2" /><circle cx="20" cy="-4" r="5" fill="#b8fff2" />
        </g>
      ) : flyingWing ? (
        <g transform={`translate(160 86) scale(${scaleX} ${scaleY})`} filter={`url(#glow-${design.id})`}>
          <path d="M0 -12 L-126 -66 L-151 -55 L-63 -4 L-147 43 L-126 54 L0 15 L126 54 L147 43 L63 -4 L151 -55 L126 -66 Z" fill={`url(#skin-${design.id})`} stroke="#c1fff2" strokeWidth="1.4" />
          <path d="M-126 -66 L-63 -4 L-147 43 M126 -66 L63 -4 L147 43" fill="none" stroke="#80dfdb" strokeWidth="1" opacity="0.7" />
          <path d="M-88 -43 L-48 -25 M88 -43 L48 -25 M-91 30 L-50 14 M91 30 L50 14" stroke="#142f3b" strokeWidth="2" opacity="0.9" />
          <path d="M-42 -14 L42 -14 L50 4 L0 14 L-50 4 Z" fill="#1c3441" stroke="#8debe0" strokeWidth="1" />
          <path d="M-17 -8 L17 -8 L11 4 L-11 4 Z" fill="#76c4c0" opacity="0.7" />
          <path d="M-22 -16 Q0 -31 22 -16" fill="none" stroke="#b8fff2" strokeWidth="2" />
          <circle cx="-3" cy="3" r="2" fill="#e9fffa" /><circle cx="3" cy="3" r="2" fill="#e9fffa" />
        </g>
      ) : vtol ? (
        <g transform={`translate(160 86) scale(${scaleX} ${scaleY})`} filter={`url(#glow-${design.id})`}>
          <path d="M0 -42 L35 -18 L70 -18 L78 -8 L70 2 L35 2 L13 14 L13 41 L-13 41 L-13 14 L-35 2 L-70 2 L-78 -8 L-70 -18 L-35 -18 Z" fill={`url(#skin-${design.id})`} stroke="#c1fff2" strokeWidth="1.2" />
          <path d="M-98 -28 L-25 -11 M98 -28 L25 -11 M-98 28 L-25 11 M98 28 L25 11" stroke="#75e2dc" strokeWidth="5" strokeLinecap="round" />
          {[-98, 98].map(x => [-28, 28].map(y => <circle key={`${x}-${y}`} cx={x} cy={y} r="13" fill="none" stroke="#75e2dc" strokeWidth="1.4" />))}
          <path d="M-15 -10 L15 -10 L23 4 L0 13 L-23 4 Z" fill="#1c3441" stroke="#8debe0" />
        </g>
      ) : (
        <g transform={`translate(160 86) scale(${scaleX} ${scaleY})`} filter={`url(#glow-${design.id})`}>
          <path d="M-16 -55 L16 -55 L16 55 L-16 55 Z" fill={`url(#skin-${design.id})`} stroke="#c1fff2" strokeWidth="1.3" />
          <path d="M-16 -4 L-112 -4 L-112 6 L-16 6 M16 -4 L112 -4 L112 6 L16 6" fill="#3d8f9a" stroke="#9cece4" strokeWidth="1" />
          {Array.from({ length: Math.min(8, motors) }, (_, index) => {
            const side = index % 2 === 0 ? -1 : 1;
            const row = Math.floor(index / 2);
            return <circle key={index} cx={side * (88 - row * 19)} cy={row * 9 - 19} r={ductedFan ? 13 : 10} fill={ductedFan ? "rgba(117,226,220,.12)" : "none"} stroke="#75e2dc" strokeWidth="1.5" />;
          })}
          <rect x="-10" y="-12" width="20" height="27" rx="4" fill="#1c3441" stroke="#8debe0" />
        </g>
      )}
      <text x="18" y="22" fill="#a8c9c6" fontSize="8" fontFamily="monospace" letterSpacing="1">PARAMETRIC GEOMETRY / TOP VIEW</text>
      <text x="18" y="158" fill="#75e2dc" fontSize="8" fontFamily="monospace">{design.modelType?.toUpperCase()} · SPAN {span.toFixed(2)} M · LENGTH {length.toFixed(2)} M · {motors} MOTORS</text>{construction && <text x="18" y="169" fill="#b8fff2" fontSize="7" fontFamily="monospace">STUDIO SYNC · {construction.parts} PARTS · {construction.massKg.toFixed(2)} KG</text>}
    </svg>
  );
}
