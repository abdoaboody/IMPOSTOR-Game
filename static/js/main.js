// Shared helpers: DOM, escaping, toasts, socket + per-room session storage.
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

const socket = io();

function emit(ev, data = {}) {
  return new Promise(res => socket.timeout(8000).emit(ev, data,
    (err, r) => res(err ? {ok: false, error: 'انتهت مهلة الاتصال، حاول مجدداً.'} : r)));
}

const store = {
  get: c => { try { return localStorage.getItem('impostor:' + c); } catch { return null; } },
  set: (c, t) => { try { localStorage.setItem('impostor:' + c, t); } catch {} },
  del: c => { try { localStorage.removeItem('impostor:' + c); } catch {} },
};

function toast(text, kind = 'info') {
  const el = document.createElement('div');
  el.className = 'toast ' + kind;
  el.textContent = text;
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), 3500);
}
