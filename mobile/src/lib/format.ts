export function formatDistance(miles: number | null | undefined): string {
  if (miles == null) return '—';
  return `${miles.toFixed(1)}mi`;
}

export function formatPace(secondsPerMile: number | null | undefined): string {
  if (secondsPerMile == null) return '—';
  const m = Math.floor(secondsPerMile / 60);
  const s = Math.round(secondsPerMile % 60);
  return `${m}:${String(s).padStart(2, '0')}/mi`;
}

export function formatHrZone(low: number | null, high: number | null): string {
  if (low == null && high == null) return '—';
  if (low != null && high != null) return `${low}-${high} bpm`;
  return `${low ?? high} bpm`;
}

export function titleCase(s: string): string {
  return s.replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

const METERS_PER_MILE = 1609.344;

export function metersToMiles(m: number | string | null | undefined): number | null {
  if (m == null) return null;
  const num = typeof m === 'string' ? parseFloat(m) : m;
  if (Number.isNaN(num)) return null;
  return num / METERS_PER_MILE;
}

export function formatPaceSPerKm(secondsPerKm: number | null | undefined): string {
  if (secondsPerKm == null) return '—';
  const secondsPerMile = secondsPerKm * 1.609344;
  return formatPace(secondsPerMile);
}

export function formatPercent(decimal: number | string | null | undefined): string {
  if (decimal == null) return '—';
  const num = typeof decimal === 'string' ? parseFloat(decimal) : decimal;
  if (Number.isNaN(num)) return '—';
  return `${Math.round(num * 100)}%`;
}
