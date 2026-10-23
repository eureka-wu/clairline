/**
 * 航线、日历与实时席位 API 接口层 (支持三字母机场代码与中文名双向通信)
 */
import { CITY_METADATA } from '../data/city-meta.js';

function toAirportCode(cityName) {
  if (!cityName) return '';
  return CITY_METADATA[cityName]?.code || cityName;
}

/**
 * 封装带超时与友好错误解析的 fetch
 */
async function fetchWithTimeout(url, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(id);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data.error || `HTTP ${res.status}`);
      err.response = data;
      throw err;
    }
    return data;
  } catch (err) {
    clearTimeout(id);
    if (err.name === 'AbortError') {
      throw new Error('长龙官方接口响应超时 (15s)，请稍后重试');
    }
    throw err;
  }
}

/**
 * 获取全网直飞航线大盘与最新机位缓存
 */
export async function fetchAvailableRoutes() {
  return await fetchWithTimeout('/api/available-routes', {}, 10000);
}

/**
 * 查询某航线单日长龙官方实际余量
 * 支持三字码 (如 HGH -> KRY) 或中文名
 */
export async function queryLiveFlights(fromCity, toCity, dateStr, forceRefresh = false) {
  const fc = toAirportCode(fromCity);
  const tc = toAirportCode(toCity);
  const url = `/api/flights?from=${encodeURIComponent(fc)}&to=${encodeURIComponent(tc)}&date=${dateStr}${forceRefresh ? '&refresh=1' : ''}`;
  return await fetchWithTimeout(url, {}, 15000);
}

/**
 * 实时联网向长龙官方刷新本航线 60 天放票日历
 * 采用机场三字代码 (如 HGH ➔ KRY) 发起请求
 */
export async function refreshRouteCalendar(fromCity, toCity) {
  const fc = toAirportCode(fromCity);
  const tc = toAirportCode(toCity);
  const url = `/api/calendar?from=${encodeURIComponent(fc)}&to=${encodeURIComponent(tc)}&refresh=1`;
  return await fetchWithTimeout(url, {}, 18000);
}

/**
 * 获取数据库持久化的所有查验机位缓存
 */
export async function fetchSeatCacheFromDb() {
  return await fetchWithTimeout('/api/flights/cache', {}, 8000);
}
