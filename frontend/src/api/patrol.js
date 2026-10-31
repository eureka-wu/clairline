/**
 * 巡检配置、定时调度与实时监控 API 接口层 (多用户 Token 鉴权平台版)
 */
import { getAuthHeaders } from './auth.js';

export async function fetchPatrolHotRoutes() {
  const res = await fetch('/api/patrol/hot-routes', {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function savePatrolHotRoutes(routes, interval) {
  const res = await fetch('/api/patrol/hot-routes', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    },
    body: JSON.stringify({ routes, interval })
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchPatrolConfig() {
  const res = await fetch('/api/patrol/config', {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function savePatrolConfig(config) {
  const res = await fetch('/api/patrol/config', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    },
    body: JSON.stringify({ config })
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchPatrolTimes() {
  const res = await fetch('/api/patrol/times', {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function savePatrolTimes(times) {
  const res = await fetch('/api/patrol/times', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    },
    body: JSON.stringify({ times })
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchPatrolSwitches() {
  const res = await fetch('/api/patrol/switches', {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function savePatrolSwitches(hotEnabled, allEnabled) {
  const res = await fetch('/api/patrol/switches', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    },
    body: JSON.stringify({ hot_enabled: hotEnabled, all_enabled: allEnabled })
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function triggerPatrol(mode) {
  const res = await fetch(`/api/patrol/trigger?mode=${encodeURIComponent(mode)}`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    },
    body: JSON.stringify({ mode })
  });
  if (!res.ok) {
    let errDetail = `请求未成功 (HTTP ${res.status})`;
    try {
      const data = await res.json();
      if (data && data.error) errDetail = data.error;
    } catch (_) {}
    throw new Error(errDetail);
  }
  return await res.json();
}

export async function fetchPatrolStatus() {
  const res = await fetch('/api/patrol/status', {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}
