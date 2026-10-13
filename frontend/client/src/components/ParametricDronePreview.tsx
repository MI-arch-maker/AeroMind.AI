import type { DroneCatalogDesign } from "../lib/droneCatalog";

type Props = { design: DroneCatalogDesign; construction?: { parts: number; massKg: number } };
const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

function Rotor({ x, y, radius, index }: { x: number; y: number; radius: number; index: number }) {
  return <g className="legacy-svg-rotor" transform={`translate(${x} ${y})`}>
    <circle r={radius} className="legacy-svg-rotor-ring" />
    <g className="legacy-svg-rotor-blades"><path d={`M-${radius - 2} 0 Q-${radius / 2} -3 0 0 Q-${radius / 2} 3 -${radius - 2} 0`} /><path d={`M${radius - 2} 0 Q${radius / 2} 3 0 0 Q${radius / 2} -3 ${radius - 2} 0`} /></g>
    <circle r="2.4" className="legacy-svg-rotor-hub" /><title>Rotor {index + 1} en rotation simulée</title>
  </g>;
}

/** Le visuel de l’ancienne URL est une maquette SVG paramétrique, pas une photo raster. */
export function ParametricDronePreview({ design, construction }: Props) {
  const config = design.configuration;
  const span = clamp(config.wingspan ?? 2, 0.7, 6);
  const length = clamp(config.fuselageLength ?? 1, 0.4, 2.8);
  const motors = Math.max(1, Math.round(config.motorCount ?? 1));
  const fixedWing = design.key === "fixed-wing";
  const blendedPusher = design.modelType === "blended-pusher";
  const vtol = design.key === "vtol";
  const aerostat = design.modelType === "aérostat";
  const ducted = design.modelType === "ducted-fan";
  const scaleX = clamp(span / 4.8, 0.72, 1.18);
  const scaleY = clamp(length / 1.9, 0.82, 1.08);
  const uid = design.id.replace(/[^a-z0-9_-]/gi, "-");
  const skin = `legacy-skin-${uid}`;
  const glass = `legacy-glass-${uid}`;
  const shadow = `legacy-shadow-${uid}`;
  return <div className="physical-drone-preview legacy-url-drone-image">
    <svg className="parametric-drone-preview" viewBox="0 0 320 174" role="img" aria-label={`${design.label}, maquette physique paramétrique animée, ${span.toFixed(1)} mètres d’envergure`}>
      <defs>
        <linearGradient id={skin} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#effff9" /><stop offset="0.42" stopColor="#69c8c2" /><stop offset="1" stopColor="#183b47" /></linearGradient>
        <linearGradient id={glass} x1="0" y1="0" x2="1" y2="1"><stop stopColor="#eafff9" /><stop offset="1" stopColor="#398e9d" /></linearGradient>
        <filter id={shadow} x="-40%" y="-50%" width="180%" height="220%"><feGaussianBlur in="SourceAlpha" stdDeviation="4" result="blur" /><feOffset dy="7" /><feComponentTransfer><feFuncA type="linear" slope=".42" /></feComponentTransfer><feMerge><feMergeNode /><feMergeNode in="SourceGraphic" /></feMerge></filter>
      </defs>
      <ellipse cx="160" cy="137" rx="108" ry="10" className="legacy-svg-ground-shadow" />
      <g className="legacy-svg-body" transform={`translate(160 82) scale(${scaleX} ${scaleY})`} filter={`url(#${shadow})`}>
        {aerostat ? <g><ellipse cx="0" cy="-4" rx="126" ry="37" fill={`url(#${skin})`} stroke="#d7fff5" strokeWidth="1.8" /><path d="M-100 -4H100 M-82 -24Q0 -42 82 -24 M-82 16Q0 34 82 16" fill="none" stroke="#75e2dc" strokeWidth="1.2" opacity=".8" /><path d="M-30 25L0 42L30 25" fill="#172d3a" stroke="#a5f4e8" strokeWidth="1.4" /><circle cx="-20" cy="-4" r="5" fill="#f1fff9" /><circle cx="20" cy="-4" r="5" fill="#f1fff9" /></g> : blendedPusher ? <g><path d="M-138 -16Q-90 -37 -20 -25L56 -20L116 -8L132 2L112 13L54 17L-26 27Q-94 38 -142 15L-154 0Z" fill={`url(#${skin})`} stroke="#d7fff5" strokeWidth="1.8" /><path d="M-42 -3L-114 -50L-137 -47L-75 4L-133 48L-111 51L-38 10Z" fill="#4a9da2" stroke="#b7fff4" strokeWidth="1.4" /><path d="M58 -8L112 -50L124 -46L91 2L122 42L110 47L57 13Z" fill="#2b6873" stroke="#9ceee5" strokeWidth="1.4" /><path d="M-57 -17Q-23 -35 24 -20L43 -5L25 10L-28 12L-58 1Z" fill={`url(#${glass})`} stroke="#eafff9" strokeWidth="1.4" /><path d="M103 -4L136 -4M103 4L136 4" stroke="#d7fff5" strokeWidth="2" /><Rotor x={142} y={0} radius={15} index={0} /></g> : fixedWing ? <g><path d="M0 -12L-126 -66L-151 -55L-63 -4L-147 43L-126 54L0 15L126 54L147 43L63 -4L151 -55L126 -66Z" fill={`url(#${skin})`} stroke="#d7fff5" strokeWidth="1.8" /><path d="M-126 -66L-63 -4L-147 43M126 -66L63 -4L147 43" fill="none" stroke="#8debe0" strokeWidth="1.4" /><path d="M-42 -14L42 -14L50 4L0 14L-50 4Z" fill={`url(#${glass})`} stroke="#eafff9" strokeWidth="1.4" /><path d="M-22 -16Q0 -31 22 -16" fill="none" stroke="#f1fff9" strokeWidth="2" /><circle cx="-3" cy="3" r="2" fill="#fff" /><circle cx="3" cy="3" r="2" fill="#fff" /></g> : vtol ? <g><path d="M0 -42L35 -18H70L78 -8L70 2H35L13 14V41H-13V14L-35 2H-70L-78 -8L-70 -18H-35Z" fill={`url(#${skin})`} stroke="#d7fff5" strokeWidth="1.6" /><path d="M-98 -28L-25 -11M98 -28L25 -11M-98 28L-25 11M98 28L25 11" stroke="#75e2dc" strokeWidth="6" strokeLinecap="round" />{[-98, 98].flatMap((x, side) => [-28, 28].map((y, row) => <Rotor key={`${x}-${y}`} x={x} y={y} radius={13} index={side * 2 + row} />))}<path d="M-15 -10L15 -10L23 4L0 13L-23 4Z" fill={`url(#${glass})`} stroke="#eafff9" /></g> : <g><path d="M-16 -55Q-20 -30 -16 55H16Q20 -30 16 -55Z" fill={`url(#${skin})`} stroke="#d7fff5" strokeWidth="1.6" /><path d="M-16 -4L-112 -4L-112 6L-16 6M16 -4L112 -4L112 6L16 6" fill="#3e969e" stroke="#a5f4e8" strokeWidth="1.2" />{Array.from({ length: Math.min(8, motors) }, (_, index) => { const side = index % 2 === 0 ? -1 : 1; const row = Math.floor(index / 2); return <Rotor key={index} x={side * (88 - row * 19)} y={row * 9 - 19} radius={ducted ? 13 : 10} index={index} />; })}<rect x="-10" y="-12" width="20" height="27" rx="6" fill={`url(#${glass})`} stroke="#eafff9" /><path d="M-7 19Q0 27 7 19" fill="none" stroke="#c4fff4" strokeWidth="2" /></g>}
      </g>
      <text x="18" y="22" className="legacy-svg-label">AEROMIND / PHYSICAL PARAMETRIC MOCKUP</text>
      <text x="18" y="158" className="legacy-svg-spec">{design.modelType?.toUpperCase()} · SPAN {span.toFixed(2)} M · LENGTH {length.toFixed(2)} M · {motors} MOTORS</text>
      {construction && <text x="18" y="169" className="legacy-svg-build">STUDIO SYNC · {construction.parts} PARTS · {construction.massKg.toFixed(2)} KG</text>}
    </svg>
  </div>;
}
