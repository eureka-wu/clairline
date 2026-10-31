/**
 * 长龙航空会员手机短信直连认证 API 接口层 (多用户 Token 鉴权平台版)
 */

export const TOKEN_STORAGE_KEY = 'clairline_token';

export function getStoredToken() {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY) || '';
  } catch (e) {
    return '';
  }
}

export function setStoredToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch (e) {}
}

export function clearStoredToken() {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch (e) {}
}

export function getAuthHeaders() {
  const token = getStoredToken();
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

export async function fetchAuthStatus() {
  const res = await fetch('/api/auth/status', {
    headers: {
      ...getAuthHeaders()
    }
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function sendSmsCode(mobile, checkParam) {
  const res = await fetch('/api/auth/send-code', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    },
    body: JSON.stringify({ mobile, checkParam })
  });
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

export async function loginWithSmsCode(mobile, code, verifyId) {
  const res = await fetch('/api/auth/login-code', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    },
    body: JSON.stringify({ mobile, code, verifyId })
  });
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || `HTTP ${res.status}`);
  
  // 登录成功：持久化存储平台专属 Session Token 到本地浏览器
  if (data.token) {
    setStoredToken(data.token);
  }
  return data;
}

export async function resetAuth() {
  const res = await fetch('/api/auth/reset', {
    method: 'POST',
    headers: {
      ...getAuthHeaders()
    }
  });
  // 注销登出：清除本地浏览器持久化 Token
  clearStoredToken();
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}
