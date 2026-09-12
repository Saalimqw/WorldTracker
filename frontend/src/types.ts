/**
 * AntiGravity — Shared TypeScript Interfaces
 */

export interface TelemetryEvent {
  id: number;
  title: string;
  category: string;
  layer: string;      // SEISMIC | CONFLICT | MILITARY | DISASTER | POLITICAL | NUCLEAR | HEALTH
  source: string;     // USGS | GDELT | UCDP | ReliefWeb
  latitude: number;
  longitude: number;
  magnitude: number | null;
  ai_summary: string;
  url: string;
  timestamp: string;
}

export interface GlobePoint {
  lat: number;
  lng: number;
  altitude: number;
  color: string;
  size: number;
  event: TelemetryEvent;
}

export type ConnectionStatus = 'connecting' | 'live' | 'offline';

export interface LayerConfig {
  id: string;
  label: string;
  icon: string;
  color: string;
  enabled: boolean;
}

export const LAYER_CONFIGS: LayerConfig[] = [
  // Core Layers
  { id: 'SEISMIC',   label: 'Seismic',    icon: '🌋', color: '#00ff9d', enabled: true  },
  { id: 'CONFLICT',  label: 'Conflicts',  icon: '⚔️', color: '#ff2244', enabled: true  },
  { id: 'MILITARY',  label: 'Military',   icon: '🎯', color: '#ff6600', enabled: true  },
  { id: 'DISASTER',  label: 'Disasters',  icon: '🌊', color: '#00aaff', enabled: true  },
  { id: 'POLITICAL', label: 'Unrest',     icon: '✊', color: '#ffaa00', enabled: true  },
  { id: 'NUCLEAR',   label: 'Nuclear',    icon: '☢️', color: '#aa00ff', enabled: true  },
  { id: 'HEALTH',    label: 'Health',     icon: '🦠', color: '#ff44aa', enabled: true  },
  { id: 'BLAST',     label: 'Blast',      icon: '💥', color: '#ff8800', enabled: true  },
  { id: 'ANOMALY',   label: 'Anomaly',    icon: '❓', color: '#888888', enabled: false },

  // New Requested Layers
  { id: 'INTEL_HOTSPOTS',       label: 'Intel Hotspots',        icon: '🎯', color: '#ff0055', enabled: true },
  { id: 'CONFLICT_ZONES',       label: 'Conflict Zones',        icon: '⚔️', color: '#ff2244', enabled: true },
  { id: 'MILITARY_BASES',       label: 'Military Bases',        icon: '🏛️', color: '#a0a0a0', enabled: true },
  { id: 'NUCLEAR_SITES',        label: 'Nuclear Sites',         icon: '☢️', color: '#aa00ff', enabled: true },
  { id: 'GAMMA_IRRADIATORS',    label: 'Gamma Irradiators',     icon: '⚠️', color: '#ffaa00', enabled: true },
  { id: 'RADIATION_WATCH',      label: 'Radiation Watch',       icon: '☢️', color: '#ff00aa', enabled: false },
  { id: 'SPACEPORTS',           label: 'Spaceports',            icon: '🚀', color: '#00ccff', enabled: false },
  { id: 'UNDERSEA_CABLES',      label: 'Undersea Cables',       icon: '🔌', color: '#0066ff', enabled: false },
  { id: 'PIPELINES',            label: 'Pipelines',             icon: '🛢️', color: '#ff8800', enabled: false },
  { id: 'AI_DATA_CENTERS',      label: 'AI Data Centers',       icon: '🖥️', color: '#00ffcc', enabled: false },
  { id: 'MILITARY_ACTIVITY',    label: 'Military Activity',     icon: '✈️', color: '#ff4400', enabled: false },
  { id: 'SHIP_TRAFFIC',         label: 'Ship Traffic',          icon: '🚢', color: '#0088ff', enabled: false },
  { id: 'TRADE_ROUTES',         label: 'Trade Routes',          icon: '⚓', color: '#00aaff', enabled: false },
  { id: 'AVIATION',             label: 'Aviation',              icon: '✈️', color: '#00ddff', enabled: false },
  { id: 'PROTESTS',             label: 'Protests',              icon: '📢', color: '#ffcc00', enabled: false },
  { id: 'ARMED_CONFLICT',       label: 'Armed Conflict Events', icon: '⚔️', color: '#ff0022', enabled: false },
  { id: 'DISPLACEMENT_FLOWS',   label: 'Displacement Flows',    icon: '👥', color: '#aaff00', enabled: false },
  { id: 'CLIMATE_ANOMALIES',    label: 'Climate Anomalies',     icon: '🌫️', color: '#88ccff', enabled: false },
  { id: 'SEVERE_WEATHER',       label: 'Severe Weather Alerts', icon: '⛈️', color: '#0055ff', enabled: false },
  { id: 'INTERNET_DISRUPTIONS', label: 'Internet Disruptions',  icon: '📡', color: '#ff0000', enabled: false },
  { id: 'CYBER_THREATS',        label: 'Cyber Threats',         icon: '🛡️', color: '#ff00ff', enabled: false },
  { id: 'NATURAL_EVENTS',       label: 'Natural Events',        icon: '🌋', color: '#ff8800', enabled: false },
  { id: 'FIRES',                label: 'Fires',                 icon: '🔥', color: '#ff4400', enabled: false },
  { id: 'CHOKEPOINTS',          label: 'Chokepoints',           icon: '⚓', color: '#ffcc00', enabled: false },
  { id: 'ECONOMIC_CENTERS',     label: 'Economic Centers',      icon: '💰', color: '#00ff00', enabled: false },
  { id: 'CRITICAL_MINERALS',    label: 'Critical Minerals',     icon: '💎', color: '#aa00ff', enabled: false },
  { id: 'GPS_JAMMING',          label: 'GPS JAMMING',           icon: '📡', color: '#ff2222', enabled: false },
  { id: 'ORBITAL_SURVEILLANCE', label: 'Orbital Surveillance',  icon: '🛰️', color: '#cccccc', enabled: false },
  { id: 'CII_INSTABILITY',      label: 'CII Instability',       icon: '🌎', color: '#ff8800', enabled: false },
  { id: 'LIVE_WEBCAMS',         label: 'Live Webcams',          icon: '📷', color: '#ffffff', enabled: false },
];
