export async function checkSystemUpdate() {
  try {
    const res = await fetch('/api/system/check-update');
    return await res.json();
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

export async function fetchSystemInfo() {
  try {
    const res = await fetch('/api/system/info');
    return await res.json();
  } catch (e) {
    return { ok: false, version: 'v2.1.2' };
  }
}
