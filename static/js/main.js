// Shared helpers: DOM, escaping, toasts, socket + per-room session storage.
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

const socket = io();

function emit(ev, data = {}) {
  return new Promise(res => socket.timeout(8000).emit(ev, data,
    (err, r) => {
      if (err) return res({ok: false, error: I18N.t('timeout_err')});
      // server errors carry an Italian translation: show the player's language
      if (r && !r.ok && I18N.lang === 'it' && r.error_it) r = {...r, error: r.error_it};
      res(r);
    }));
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

// Credit card: a small icon expands the "created by" card with a pop animation;
// clicking the icon again collapses it back.
(() => {
  const credit = document.querySelector('.credit');
  if (!credit) return;
  const toggle = credit.querySelector('.credit-toggle');
  const body = credit.querySelector('.credit-body');
  toggle.addEventListener('click', () => {
    const open = credit.classList.toggle('open');
    body.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
  });
})();
