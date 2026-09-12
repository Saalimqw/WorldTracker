/**
 * AntiGravity — Live Event Feed Panel (feed.ts)
 * Right sidebar showing real-time events with source badges and click-to-fly.
 */

import type { TelemetryEvent } from './types';
import { LAYER_CONFIGS } from './types';

let onEventClick: ((event: TelemetryEvent) => void) | null = null;

export function initFeed(clickCallback: (event: TelemetryEvent) => void): void {
  onEventClick = clickCallback;
}

export function updateFeed(events: TelemetryEvent[]): void {
  const container = document.getElementById('feed-list');
  if (!container) return;

  // Sort by timestamp descending, take top 50
  const sorted = [...events]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 50);

  container.innerHTML = sorted.map(ev => {
    const cfg = LAYER_CONFIGS.find(l => l.id === ev.layer)
      || { icon: '📍', color: '#888', label: ev.layer };
    const timeAgo = formatTimeAgo(ev.timestamp);
    const mag = ev.magnitude != null ? `M${ev.magnitude.toFixed(1)}` : '';
    const title = ev.title.length > 60 ? ev.title.slice(0, 57) + '...' : ev.title;

    return `
      <div class="feed-item" data-id="${ev.id}" style="border-left-color: ${cfg.color}">
        <div class="feed-item-header">
          <span class="feed-icon">${cfg.icon}</span>
          <span class="feed-layer" style="color:${cfg.color}">${ev.layer}</span>
          ${mag ? `<span class="feed-mag">${mag}</span>` : ''}
          <span class="feed-source">${ev.source}</span>
        </div>
        <div class="feed-title">${title}</div>
        <div class="feed-footer">
          <span class="feed-time">${timeAgo}</span>
          ${ev.ai_summary && ev.ai_summary !== '[pending]' && !ev.ai_summary.startsWith('[')
            ? `<span class="feed-ai">⚡ ${ev.ai_summary.slice(0, 40)}...</span>`
            : ''}
        </div>
      </div>
    `;
  }).join('');

  // Attach click listeners
  container.querySelectorAll<HTMLElement>('.feed-item').forEach(el => {
    el.addEventListener('click', () => {
      const id = parseInt(el.dataset.id || '0', 10);
      const ev = events.find(e => e.id === id);
      if (ev && onEventClick) onEventClick(ev);
    });
  });

  // Update counter
  const countEl = document.getElementById('feed-count');
  if (countEl) countEl.textContent = events.length.toLocaleString();
}

function formatTimeAgo(timestamp: string): string {
  const now  = Date.now();
  const then = new Date(timestamp).getTime();
  const diff = Math.floor((now - then) / 1000);

  if (diff < 60)   return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}
