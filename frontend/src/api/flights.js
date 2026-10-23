/**
 * 航线、日历与实时席位 API 接口层
 */

export async function fetchAvailableRoutes() {
  const res = await fetch('/api/available-routes');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function queryLiveFlights(fromCity, toCity, dateStr, forceRefresh = false) {
  const url = `/api/flights?from=${encodeURIComponent(fromCity)}&to=${encodeURIComponent(toCity)}&date=${dateStr}${forceRefresh ? '&refresh=1' : ''}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function refreshRouteCalendar(fromCity, toCity) {
  const url = `/api/calendar?from=${encodeURIComponent(fromCity)}&to=${encodeURIComponent(toCity)}&refresh=1`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchSeatCacheFromDb() {
  const res = await fetch('/api/flights/cache');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}
