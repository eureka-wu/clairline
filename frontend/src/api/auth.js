/**
 * 长龙航空会员手机短信直连认证 API 接口层 (纯免抓包版)
 */

export async function fetchAuthStatus() {
  const res = await fetch('/api/auth/status');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function sendSmsCode(mobile, checkParam) {
  const res = await fetch('/api/auth/send-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mobile, checkParam })
  });
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

export async function loginWithSmsCode(mobile, code, verifyId) {
  const res = await fetch('/api/auth/login-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mobile, code, verifyId })
  });
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

export async function resetAuth() {
  const res = await fetch('/api/auth/reset', {
    method: 'POST'
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}
