/**
 * AntiGravity — HUD Heads-Up Display Controller (hud.ts)
 * Manages status indicator, event counter, last-sync timestamp, and banner.
 */

import type { ConnectionStatus } from './types';

// ─── DOM References ───────────────────────────────────────────────────────────
const statusIndicator = document.getElementById('status-indicator')!;
const statusText      = document.getElementById('status-text')!;
const counterValue    = document.getElementById('counter-value')!;
const updatedValue    = document.getElementById('updated-value')!;
const reconnectBanner = document.getElementById('reconnect-banner')!;

// ─── HUD Update API ──────────────────────────────────────────────────────────

export function setStatus(status: ConnectionStatus): void {
  statusIndicator.className = ''; // clear all classes
  statusIndicator.classList.add(status);

  switch (status) {
    case 'live':
      statusText.textContent = 'LIVE';
      reconnectBanner.classList.add('hidden');
      break;
    case 'offline':
      statusText.textContent = 'OFFLINE';
      reconnectBanner.classList.remove('hidden');
      break;
    case 'connecting':
      statusText.textContent = 'CONNECTING';
      reconnectBanner.classList.add('hidden');
      break;
  }
}

export function setEventCount(count: number): void {
  counterValue.textContent = count.toLocaleString();
}

export function setLastUpdated(): void {
  const now = new Date();
  updatedValue.textContent = now.toLocaleTimeString('en-US', {
    hour12:  false,
    hour:    '2-digit',
    minute:  '2-digit',
    second:  '2-digit',
  });
}
