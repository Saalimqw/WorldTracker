/**
 * AntiGravity — Main Application Bootstrap (main.ts)
 *
 * Orchestrates:
 *  - Globe initialization
 *  - Backend polling (/api/events)
 *  - Layer toggle filtering
 *  - Time range filtering
 *  - HUD + event feed updates
 */

import './style.css';
import { initGlobe, updateGlobePoints, flyTo } from './globe';
import { setStatus, setEventCount, setLastUpdated } from './hud';
import { initFeed, updateFeed } from './feed';
import type { TelemetryEvent } from './types';
import { LAYER_CONFIGS } from './types';

// ─── Config ───────────────────────────────────────────────────────────────────
const POLL_INTERVAL = 20_000;   // 20 seconds
const BACKOFF_BASE = 2_000;
const BACKOFF_MAX = 60_000;

// ─── State ────────────────────────────────────────────────────────────────────
let failureCount = 0;
let pollingTimer: ReturnType<typeof setTimeout> | null = null;
let allEvents: TelemetryEvent[] = [];
let activeHours = 0;          // 0 = ALL
let activeLayers = new Set(LAYER_CONFIGS.filter(l => l.enabled).map(l => l.id));

// ─── Filter ───────────────────────────────────────────────────────────────────
function getFilteredEvents(): TelemetryEvent[] {
  let evs = allEvents;

  if (activeHours > 0) {
    const cutoff = Date.now() - activeHours * 3_600_000;
    evs = evs.filter(e => new Date(e.timestamp).getTime() >= cutoff);
  }

  if (activeLayers.size < LAYER_CONFIGS.length) {
    evs = evs.filter(e => {
      const layer = e.layer || e.category;
      return activeLayers.has(layer);
    });
  }

  return evs;
}

function applyFilters(): void {
  const filtered = getFilteredEvents();
  updateGlobePoints(filtered);
  updateFeed(filtered);
  setEventCount(filtered.length);
}

// ─── Fetch ────────────────────────────────────────────────────────────────────
async function fetchEvents(): Promise<TelemetryEvent[]> {
  const resp = await fetch('/api/events', { signal: AbortSignal.timeout(10_000) });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json() as Promise<TelemetryEvent[]>;
}

// ─── Poll Cycle ───────────────────────────────────────────────────────────────
async function pollCycle(): Promise<void> {
  try {
    const events = await fetchEvents();
    failureCount = 0;
    setStatus('live');
    setLastUpdated();

    allEvents = events;
    applyFilters();

    pollingTimer = setTimeout(pollCycle, POLL_INTERVAL);
  } catch (err) {
    failureCount++;
    const delay = Math.min(BACKOFF_BASE * Math.pow(2, failureCount - 1), BACKOFF_MAX);
    console.warn(`[AntiGravity] Fetch failed (attempt ${failureCount}). Retry in ${delay / 1000}s`, err);
    setStatus('offline');
    pollingTimer = setTimeout(pollCycle, delay);
  }
}

// ─── Layer Sidebar ────────────────────────────────────────────────────────────
function buildLayerSidebar(): void {
  const container = document.getElementById('layer-toggles');
  if (!container) return;

  container.innerHTML = LAYER_CONFIGS.map(cfg => `
    <button
      class="layer-btn ${cfg.enabled ? 'active' : ''}"
      data-layer="${cfg.id}"
      style="--layer-color: ${cfg.color}"
      title="${cfg.label}"
    >
      <span class="layer-icon">${cfg.icon}</span>
      <span class="layer-label">${cfg.label}</span>
      <span class="layer-dot" style="background:${cfg.color}"></span>
    </button>
  `).join('');

  container.querySelectorAll<HTMLButtonElement>('.layer-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const layer = btn.dataset.layer!;
      if (activeLayers.has(layer)) {
        activeLayers.delete(layer);
        btn.classList.remove('active');
      } else {
        activeLayers.add(layer);
        btn.classList.add('active');
      }
      applyFilters();
    });
  });
}

// ─── Time Filter ──────────────────────────────────────────────────────────────
function buildTimeFilter(): void {
  const buttons = document.querySelectorAll<HTMLButtonElement>('[data-hours]');
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeHours = parseInt(btn.dataset.hours || '0', 10);
      applyFilters();
    });
  });
}

// ─── Boot ─────────────────────────────────────────────────────────────────────
async function boot(): Promise<void> {
  console.info('[AntiGravity] Initializing Event Horizon Telemetry Node...');
  setStatus('connecting');

  // Build UI
  buildLayerSidebar();
  buildTimeFilter();

  // Init event feed with click-to-fly
  initFeed((ev: TelemetryEvent) => {
    flyTo(ev.latitude, ev.longitude);
  });

  // Start polling IMMEDIATELY — do NOT wait for globe
  pollCycle();

  // Init globe in the background — won't block data loading
  initGlobe('globe-container')
    .then(() => console.info('[AntiGravity] Globe initialized.'))
    .catch(err => console.error('[AntiGravity] Globe init failed (data still showing):', err));
}

document.addEventListener('DOMContentLoaded', boot);
