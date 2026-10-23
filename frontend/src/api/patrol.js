/**
 * 巡检配置、定时调度与实时监控 API 接口层
 */

export async function fetchPatrolHotRoutes() {
  const res = await fetch('/api/patrol/hot-routes');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function savePatrolHotRoutes(routes) {
  const res = await fetch('/api/patrol/hot-routes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ routes })
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchPatrolConfig() {
  const res = await fetch('/api/patrol/config');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function savePatrolConfig(config) {
  const res = await fetch('/api/patrol/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ config })
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchPatrolTimes() {
  const res = await fetch('/api/patrol/times');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function savePatrolTimes(times) {
  const res = await fetch('/api/patrol/times', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ times })
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchPatrolSwitches() {
  const res = await fetch('/api/patrol/switches');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function savePatrolSwitches(hotEnabled, allEnabled) {
  const res = await fetch('/api/patrol/switches', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hot_enabled: hotEnabled, all_enabled: allEnabled })
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function triggerPatrol(mode) {
  const res = await fetch(`/api/patrol/trigger?mode=${encodeURIComponent(mode)}`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchPatrolStatus() {
  const res = await fetch('/api/patrol/status');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}
