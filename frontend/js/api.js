/**
 * 前端与本地后端 RESTful API 通信层
 */
export const API_BASE = ''; // 同源访问

export async function getBackendStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/status`);
    return await res.json();
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

export async function queryLiveFlights(fromCity, toCity, dateStr, forceRefresh = false) {
  try {
    const url = `${API_BASE}/api/flights?from=${encodeURIComponent(fromCity)}&to=${encodeURIComponent(toCity)}&date=${dateStr}${forceRefresh ? '&refresh=1' : ''}`;
    const res = await fetch(url);
    return await res.json();
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

export async function fetchSeatCacheFromDb(fromCity = '', toCity = '') {
  try {
    let url = `${API_BASE}/api/seat-cache`;
    if (fromCity && toCity) {
      url += `?from=${encodeURIComponent(fromCity)}&to=${encodeURIComponent(toCity)}`;
    }
    const res = await fetch(url);
    return await res.json();
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

export async function queryRouteCalendar(fromCity, toCity) {
  try {
    const res = await fetch(`${API_BASE}/api/calendar?from=${encodeURIComponent(fromCity)}&to=${encodeURIComponent(toCity)}`);
    return await res.json();
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

export async function getMonitorTasks() {
  try {
    const res = await fetch(`${API_BASE}/api/monitor/tasks`);
    return await res.json();
  } catch (err) {
    return { ok: false, error: err.message, tasks: [] };
  }
}

export async function addMonitorTask(fromCity, toCity, dateStr) {
  try {
    const res = await fetch(`${API_BASE}/api/monitor/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: fromCity, to: toCity, date: dateStr })
    });
    return await res.json();
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

export async function deleteMonitorTask(taskId) {
  try {
    const res = await fetch(`${API_BASE}/api/monitor/tasks?id=${encodeURIComponent(taskId)}`, {
      method: 'DELETE'
    });
    return await res.json();
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

export async function triggerImmediateSync() {
  try {
    const res = await fetch(`${API_BASE}/api/monitor/sync`, { method: 'POST' });
    return await res.json();
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

export async function getSyncHistory() {
  try {
    const res = await fetch(`${API_BASE}/api/monitor/history`);
    return await res.json();
  } catch (err) {
    return { ok: false, error: err.message, history: [] };
  }
}
