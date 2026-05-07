export const colors = {
  // page + panels
  bg: '#0e1320',          // slightly more navy-blue (was #0d0d12)
  bgPanel: '#1a1f33',     // lifted ~10% from page bg, gives elevation w/o shadow
  bgPanelAlt: '#222a44',  // alternating rows / nested panels
  bgCard: '#1a1f33',      // alias kept for backward compat with existing consumers
  bgElev: '#1a1f33',      // alias

  // ink
  ink: '#e8e8d8',         // warmer cream (was #f4f4ec)
  inkDim: '#8b9bb3',      // cooler, leans cyan-tinted (was #9a9aab)
  inkMute: '#5a6478',     // dim slate (was #5a5a6b)

  // borders
  line: '#2a3045',        // soft slate, NOT pure black anymore (was #000000)
  lineHard: '#000000',    // available for the rare element that still wants pure black

  // accents
  accentRun: '#22d36a',     // phosphor green (was #5cd86c) — primary CTA, on-plan, brand
  accentCyan: '#7ec8c8',    // NEW — section headers, secondary icons (replaces accentRest in chrome)
  accentStrength: '#e8593a',// shifted toward red-orange for badge pop (was #e8a23a)
  accentBadgePurple: '#7c5cd8', // NEW — second badge tier (matches NES/SNES pill duality)
  accentRest: '#5b8cff',    // kept as a third accent for rest/cross day chips
  accentDanger: '#e84a4a',  // unchanged
  accentHi: '#f7d51d',      // unchanged — current week / peak markers
} as const;

export const spacing = {
  xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32,
} as const;

export const radius = {
  sm: 4,    // pills, badges
  md: 6,    // primary buttons, cards
  lg: 8,    // sheets, large surfaces
  xl: 10,
} as const;

export type WorkoutFamily = 'running' | 'strength' | 'other';

export const familyColor: Record<WorkoutFamily, string> = {
  running: colors.accentRun,
  strength: colors.accentStrength,
  other: colors.accentRest,
};

export const fonts = {
  pixel: 'PressStart2P',
  body: 'VT323',
  mono: 'JetBrainsMono',
  monoBold: 'JetBrainsMono-Bold',
} as const;
