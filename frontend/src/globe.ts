/**
 * AntiGravity — Procedural WebGL Globe Engine (globe.ts)
 */

import Globe from 'globe.gl';
import type { TelemetryEvent, GlobePoint } from './types';
import { LAYER_CONFIGS } from './types';

const GlobeFactory = Globe as unknown as () => (el: HTMLElement) => InstanceType<typeof Globe>;

const tooltipEl   = document.getElementById('event-tooltip')!;
const ttCategory  = document.getElementById('tooltip-category')!;
const ttTitle     = document.getElementById('tooltip-title')!;
const ttMagnitude = document.getElementById('tooltip-magnitude')!;
const ttAI        = document.getElementById('tooltip-ai')!;
const ttTime      = document.getElementById('tooltip-time')!;

let _mouseX = 0;
let _mouseY = 0;
document.addEventListener('mousemove', (e) => {
  _mouseX = e.clientX;
  _mouseY = e.clientY;
});

let globeInstance: InstanceType<typeof Globe> | null = null;

// ── Severity/Layer colour scale ─────────────────────────────────────────────────────
export function magnitudeColor(mag: number | null): string {
  const m = mag ?? 0;
  if (m >= 6) return '#ff2244';
  if (m >= 4) return '#ff8800';
  if (m >= 2) return '#ffe600';
  return '#00ff9d';
}

function magnitudeAltitude(mag: number | null): number {
  const m = Math.max(0, mag ?? 0);
  return 0.005 + m * 0.008;
}

function magnitudeSize(mag: number | null): number {
  const m = Math.max(0, mag ?? 0);
  return 0.3 + m * 0.25;
}

// ── Tooltip ───────────────────────────────────────────────────────────────────
function showTooltip(event: TelemetryEvent, mouseX: number, mouseY: number): void {
  const cfg = LAYER_CONFIGS.find(l => l.id === event.layer) || { icon: '📍', color: magnitudeColor(event.magnitude) };
  
  const magStr = event.magnitude != null
    ? `M ${event.magnitude.toFixed(1)}`
    : '';

  ttCategory.textContent  = `${cfg.icon} ${event.layer || event.category}`;
  ttCategory.style.color  = cfg.color;
  ttTitle.textContent     = event.title;
  ttMagnitude.textContent = magStr;
  ttAI.textContent        = event.ai_summary || '[ awaiting AI analysis ]';
  ttTime.textContent      = new Date(event.timestamp).toLocaleString('en-US', {
    dateStyle: 'medium', timeStyle: 'short', hour12: false,
  });

  tooltipEl.style.borderColor = cfg.color;
  tooltipEl.style.boxShadow   =
    `0 0 0 1px ${cfg.color}33,` +
    `0 8px 32px rgba(0,0,0,0.6),` +
    `inset 0 1px 0 rgba(0,230,255,0.08)`;

  const pad = 16, tw = 310, th = 180;
  let x = mouseX + 18;
  let y = mouseY + 18;
  if (x + tw > window.innerWidth  - pad) x = mouseX - tw - 18;
  if (y + th > window.innerHeight - pad) y = mouseY - th - 18;

  tooltipEl.style.left = `${x}px`;
  tooltipEl.style.top  = `${y}px`;
  tooltipEl.classList.remove('hidden');
}

function hideTooltip(): void {
  tooltipEl.classList.add('hidden');
}

// ── Atmosphere glow ───────────────────────────────────────────────────────────
function injectAtmosphereGlow(container: HTMLElement): void {
  const inner = document.createElement('div');
  inner.id = 'atmosphere-inner';
  Object.assign(inner.style, {
    position:     'absolute',
    top:          '50%',
    left:         '50%',
    transform:    'translate(-50%, -50%)',
    width:        'min(65vw, 65vh)',
    height:       'min(65vw, 65vh)',
    borderRadius: '50%',
    pointerEvents:'none',
    zIndex:       '1',
    background:   'transparent',
    boxShadow:
      '0 0 60px 20px rgba(0,160,255,0.08),' +
      '0 0 120px 50px rgba(0,100,200,0.06),' +
      '0 0 200px 80px rgba(0,60,140,0.04)',
  });
  container.style.position = 'relative';
  container.appendChild(inner);
}

// ── Countries GeoJSON ─────────────────────────────────────────────────────────
// Use a much lighter-weight (~800KB vs ~23MB) TopoJSON-derived dataset
const COUNTRIES_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

async function loadCountriesGeoJSON(): Promise<any[]> {
  try {
    const resp = await fetch(COUNTRIES_URL, { signal: AbortSignal.timeout(8000) });
    const topo = await resp.json();
    // Convert TopoJSON → GeoJSON features using inline conversion
    const { feature } = await import('topojson-client');
    const objectKey = Object.keys(topo.objects)[0];
    const geojson = feature(topo, topo.objects[objectKey]);
    return (geojson as any).features;
  } catch (e) {
    console.warn('[AntiGravity] Could not load world boundaries:', e);
    return [];
  }
}

function calculateCentroid(coords: any[]): [number, number] {
  let minLng = Infinity, maxLng = -Infinity, minLat = Infinity, maxLat = -Infinity;
  const processPoint = (pt: number[]) => {
    if (pt[0] < minLng) minLng = pt[0];
    if (pt[0] > maxLng) maxLng = pt[0];
    if (pt[1] < minLat) minLat = pt[1];
    if (pt[1] > maxLat) maxLat = pt[1];
  };
  const processRing = (ring: any[]) => ring.forEach(processPoint);
  const processPolygon = (poly: any[]) => poly.forEach(processRing);
  
  if (typeof coords[0][0][0] === 'number') {
    processPolygon(coords);
  } else {
    coords.forEach(processPolygon);
  }
  return [minLng + (maxLng - minLng) / 2, minLat + (maxLat - minLat) / 2];
}

// ── Globe initializer ─────────────────────────────────────────────────────────
export async function initGlobe(containerId: string): Promise<void> {
  const container = document.getElementById(containerId);
  if (!container) throw new Error(`Container #${containerId} not found`);

  injectAtmosphereGlow(container);

  const countries     = await loadCountriesGeoJSON();
  
  // Calculate labels data for countries
  const labelsData = countries.map(f => {
    const [lng, lat] = calculateCentroid(f.geometry.coordinates);
    return {
      lat, lng,
      name: f.properties.ADMIN || f.properties.name || '',
      iso: f.properties.ISO_A3 || f.properties.ISO_A2 || ''
    };
  }).filter(l => l.name);

  const globe = GlobeFactory()(container)
    .backgroundColor('#040810')
    .globeImageUrl('')

    // Country polygons (lightweight 110m dataset)
    .polygonsData(countries)
    .polygonCapColor(() => 'rgba(10, 20, 45, 0.85)')
    .polygonSideColor(() => 'rgba(0, 180, 220, 0.05)')
    .polygonStrokeColor(() => 'rgba(0, 210, 255, 0.35)')
    .polygonAltitude(0.001)
    .polygonsTransitionDuration(0)

    // Country Labels
    .labelsData(labelsData)
    .labelLat((d: any) => d.lat)
    .labelLng((d: any) => d.lng)
    .labelText((d: any) => d.name)
    .labelSize(0.8)
    .labelDotRadius(0.2)
    .labelColor(() => 'rgba(255, 255, 255, 0.6)')
    .labelResolution(1)
    .labelAltitude(0.01)

    // Event points
    .pointsData([])
    .pointLat((d: any) => (d as GlobePoint).lat)
    .pointLng((d: any) => (d as GlobePoint).lng)
    .pointAltitude((d: any) => (d as GlobePoint).altitude)
    .pointColor((d: any) => (d as GlobePoint).color)
    .pointRadius((d: any) => (d as GlobePoint).size)
    .pointsMerge(false)
    .pointsTransitionDuration(300)

    .onPointHover((point: any, _prev: any) => {
      if (point) {
        container.style.cursor = 'crosshair';
        showTooltip((point as GlobePoint).event, _mouseX, _mouseY);
      } else {
        container.style.cursor = 'grab';
        hideTooltip();
      }
    })

    .onPointClick((point: any) => {
      if (point) {
        const gp = point as GlobePoint;
        globe.pointOfView({ lat: gp.lat, lng: gp.lng, altitude: 1.5 }, 600);
      }
    })
    
    .onPolygonClick((polygon: any) => {
        if(polygon) {
            const [lng, lat] = calculateCentroid(polygon.geometry.coordinates);
            globe.pointOfView({ lat, lng, altitude: 1.2 }, 800);
        }
    })

    .pointOfView({ lat: 20, lng: 0, altitude: 2.2 }, 0)
    .enablePointerInteraction(true);

  globe.width(container.offsetWidth);
  globe.height(container.offsetHeight);

  setTimeout(() => {
    try {
      // Cap pixel ratio to avoid rendering millions of extra pixels on HiDPI
      const renderer: any = globe.renderer();
      if (renderer) {
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
      }

      const scene: any = globe.scene();
      scene.traverse((obj: any) => {
        if (obj.isMesh && obj.geometry?.type === 'SphereGeometry') {
          obj.material.color?.setStyle('#061022');
          obj.material.emissive?.setStyle('#020810');
          obj.material.roughness = 1;
          obj.material.metalness = 0;
          obj.material.needsUpdate = true;
        }
      });
    } catch (_) { }
  }, 200);

  setTimeout(() => {
    const controls = globe.controls();
    if (controls) {
      controls.autoRotate      = true;
      controls.autoRotateSpeed = 0.35;
      controls.enableDamping   = true;
      controls.dampingFactor   = 0.08;
      controls.minDistance     = 100;
      controls.maxDistance     = 700;
      // Stop auto-rotation if the user clicks/drags the globe
      controls.addEventListener('start', () => {
          controls.autoRotate = false;
      });
      // Removed zoom-based label hiding to show country names at all times
    }
  }, 100);

  const ro = new ResizeObserver(() => {
    globe.width(container.offsetWidth);
    globe.height(container.offsetHeight);
  });
  ro.observe(container);

  globeInstance = globe;
}

export function flyTo(lat: number, lng: number, altitude = 1.5) {
    if (globeInstance) {
        globeInstance.pointOfView({ lat, lng, altitude }, 800);
    }
}

export function updateGlobePoints(events: TelemetryEvent[]): void {
  if (!globeInstance) return;

  const points: GlobePoint[] = events.map(ev => {
    const cfg = LAYER_CONFIGS.find(l => l.id === ev.layer) || { color: magnitudeColor(ev.magnitude) };
    return {
      lat:      ev.latitude,
      lng:      ev.longitude,
      altitude: magnitudeAltitude(ev.magnitude),
      color:    cfg.color + 'aa', // add alpha channel for translucency
      size:     magnitudeSize(ev.magnitude),
      event:    ev,
    };
  });

  (globeInstance as any).pointsData(points);
}
