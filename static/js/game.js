(() => {
const CODE = document.body.dataset.code;
const t = (...a) => I18N.t(...a);
const app = $('#app'), top = $('#top');
let S = null, role = null, question = null, lastPhase = null, lastRound = null;

// ---------------------------------------------------------------- connection
socket.on('connect', async () => {
  $('#conn').hidden = true;
  const token = store.get(CODE);
  if (!token) return renderJoin();
  const r = await emit('rejoin', {code: CODE, token});
  if (!r.ok) { store.del(CODE); S = null; renderJoin(r.error); }
});
socket.on('disconnect', () => $('#conn').hidden = false);
socket.on('notice', n => toast(n.text, n.kind));
socket.on('state', s => { S = s; render(); });
socket.on('kicked', () => { store.del(CODE); location.href = '/?kicked=1'; });
socket.on('impostor_lost', d => showModal(t('lost_title'), t('lost_text', {name: d.name})));
window.addEventListener('langchange', () => { if (S) render(); });

async function call(ev, data) {
  const r = await emit(ev, data);
  if (!r.ok) toast(r.error, 'err');
  return r;
}

// ------------------------------------------------------------------- helpers
const PHASES = () => [
  ['lobby', t('phase_lobby')], ['reveal', t('phase_reveal')],
  ['discussion', t('phase_discussion')], ['voting', t('phase_voting')],
  ['tally', t('phase_tally')], ['final', t('phase_final')],
];
const CATS = ['jobs', 'food', 'random'];
const CAT_ICON = {jobs: '💼', food: '🍔', random: '🎲'};
const cat = () => (S && S.settings ? S.settings.category : 'jobs');
const hue = n => [...n].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 360, 7);
const avatar = n => `<span class="av" style="--h:${hue(n)}" data-testid="player-avatar">${esc([...n][0] || '?')}</span>`;
const btn = (act, label, {cls = 'primary', ok = true, id = '', tid = ''} = {}) =>
  `<button class="btn ${cls}" data-act="${act}" ${id ? `data-id="${esc(id)}"` : ''} ${tid ? `data-testid="${tid}"` : ''} ${ok ? '' : 'disabled'}>${label}</button>`;
const chip = (on, yes, no) => `<span class="chip ${on ? 'yes' : ''}">${on ? yes : no}</span>`;
const isHost = () => S.me.is_host;
const connected = () => S.players.filter(p => p.connected);
const nameOf = id => (S.players.find(p => p.id === id) || {name: '؟'}).name;

function plist(status, {kick = false} = {}) {
  return `<ul class="plist" data-testid="player-list-container">${S.players.map(p => `
    <li class="${p.connected ? '' : 'off'}" data-testid="player-row">${avatar(p.name)}
      <span class="nm">${esc(p.name)}${p.id === S.me.id ? ` <small>${esc(t('you'))}</small>` : ''}${p.is_host ? ` <span class="crown" title="${esc(t('host_crown'))}">♛</span>` : ''}</span>
      ${p.connected ? (status ? status(p) : '') : `<span class="chip">${esc(t('offline'))}</span>`}
      ${kick && p.id !== S.me.id ? `<button class="kick" data-act="kick" data-id="${p.id}" title="${esc(t('kick'))}" aria-label="${esc(t('kick'))} ${esc(p.name)}" data-testid="kick-player-btn">✕</button>` : ''}
    </li>`).join('')}</ul>`;
}

function settingsPanel() {
  const st = S.settings;
  const hintsAvail = st.mode === 'blind' && st.category === 'random';
  if (!isHost()) {
    return `<div class="setsum" data-testid="settings-summary">
      <span class="tag">${CAT_ICON[st.category]} ${esc(t('cat_' + st.category))}</span>
      <span class="tag">${esc(t('mode_' + st.mode))}</span>
      ${hintsAvail ? `<span class="tag">${esc(t(st.hints ? 'hints_on' : 'hints_off'))}</span>` : ''}
    </div>`;
  }
  const opt = (key, val, label, sub, tid) =>
    `<button class="opt ${st[key] === val ? 'on' : ''}" data-act="set" data-id="${key}:${val}" data-testid="${tid}" aria-pressed="${st[key] === val}">
      <b>${label}</b>${sub ? `<small>${esc(sub)}</small>` : ''}</button>`;
  return `<div class="settings" data-testid="settings-panel">
    <p class="setlabel">${esc(t('set_category'))}</p>
    <div class="opts three">${CATS.map(c => opt('category', c, `${CAT_ICON[c]} ${esc(t('cat_' + c))}`, '', `category-${c}-btn`)).join('')}</div>
    <p class="setlabel">${esc(t('set_mode'))}</p>
    <div class="opts">${opt('mode', 'decoy', esc(t('mode_decoy')), t('mode_decoy_sub'), 'mode-decoy-btn')}${opt('mode', 'blind', esc(t('mode_blind')), t('mode_blind_sub'), 'mode-blind-btn')}</div>
    ${hintsAvail ? `<button class="switch ${st.hints ? 'on' : ''}" data-act="set" data-id="hints:${st.hints ? '0' : '1'}" role="switch" aria-checked="${st.hints}" data-testid="hints-toggle">
        <span class="knob"></span><span><b>${esc(t('hints_label'))}</b><small>${esc(t('hints_sub'))}</small></span></button>` : ''}
  </div>`;
}

function secretCard() {
  const title = t('secret_' + cat());
  if (role !== null) {
    const hide = btn('hide-role', S.phase === 'reveal' ? t('btn_hide_follow') : t('btn_hide'), {cls: 'ghost', tid: 'role-reveal-toggle-btn'});
    if (role.impostor) return `<div class="secret open imp" data-testid="role-reveal-card"><small>${esc(title)}</small>
      <strong data-testid="secret-word">${esc(t('you_impostor'))}</strong>
      ${role.hint ? `<p class="hint" data-testid="impostor-hint">💡 ${esc(t('hint_is'))}: <b>${esc(role.hint)}</b></p>` : `<p class="muted">${esc(t('no_hint'))}</p>`}
      ${hide}</div>`;
    return `<div class="secret open" data-testid="role-reveal-card"><small>${esc(title)}</small><strong data-testid="secret-word">${esc(role.word)}</strong>${hide}</div>`;
  }
  return `<div class="secret" data-testid="role-reveal-card"><p>${esc(t('secret_warn'))}</p>${btn('reveal-role', t('btn_show'), {tid: 'role-reveal-toggle-btn'})}</div>`;
}

// ----------------------------------------------------------------------- views
const VIEWS = {
  lobby() {
    const link = location.origin + '/?code=' + S.code;
    return `<section class="card enter" data-testid="lobby-panel"><h2>${esc(t('lobby_title'))}</h2>
      <div class="codebox"><div class="code" dir="ltr" data-testid="lobby-code-tiles">${[...S.code].map(c => `<b>${c}</b>`).join('')}</div>
        <button class="btn ghost" data-act="copy" data-id="${esc(link)}" data-testid="copy-invite-btn">${esc(t('copy_invite'))}</button></div>
      ${settingsPanel()}
      <p class="muted">${esc(t('players_count', {n: S.players.length, m: S.max_players, c: connected().length}))}</p>
      ${plist(null, {kick: isHost()})}
      ${isHost() ? btn('start_game', t('btn_start'), {ok: S.can_start, tid: 'start-game-btn'}) + (S.can_start ? '' : `<p class="muted">${esc(t('need_three'))}</p>`)
                 : `<p class="muted">${esc(t('wait_start'))}</p>`}
      ${btn('leave', t('btn_leave'), {cls: 'link', tid: 'leave-room-btn'})}
    </section>`;
  },
  reveal() {
    if (S.me.seen) return `<section class="card enter center"><h2>${esc(t('done'))}</h2><p class="muted">${esc(t('wait_others'))}</p>
      ${plist(p => chip(p.seen, t('seen_yes'), t('seen_no')))}</section>`;
    return `<section class="card enter center"><span class="tag">${CAT_ICON[cat()]} ${esc(t('cat_' + cat()))}</span><h2>${esc(t('secret_' + cat()))}</h2>${secretCard()}</section>`;
  },
  discussion() {
    return `<section class="card enter"><h2>${esc(t('disc_title'))}${S.vote_round > 1 ? ` <small class="muted">${esc(t('vote_round', {n: S.vote_round}))}</small>` : ''}</h2>
      <p class="muted">${esc(t('disc_hint'))}</p>
      ${secretCard()}
      <div class="qbox" data-testid="discussion-questions-box">${question ? `<p class="q" data-testid="suggested-question">${esc(question)}</p>` : `<p class="muted">${esc(t('q_hint'))}</p>`}
        ${btn('question', question ? t('btn_q2') : t('btn_q1'), {cls: 'ghost', tid: 'suggest-question-btn'})}</div>
      ${S.me.ready ? `<p class="ok">${esc(t('ready_ok'))}</p>` : btn('ready', t('btn_ready'), {tid: 'ready-btn'})}
      ${plist(p => chip(p.ready, t('ready_yes'), t('ready_no')))}
      ${isHost() ? btn('start_voting', t('btn_start_vote'), {ok: S.all_ready, tid: 'start-voting-btn'}) + (S.all_ready ? '' : `<p class="muted">${esc(t('wait_ready'))}</p>`) : ''}
    </section>`;
  },
  voting() {
    const head = `<h2>${esc(t('vote_title'))}${S.vote_round > 1 ? ` <small>${esc(t('vote_round', {n: S.vote_round}))}</small>` : ''}</h2>`;
    const body = S.me.voted
      ? `<p class="ok">${esc(t('voted_ok'))}</p>`
      : `<p class="muted">${esc(t('vote_hint'))}</p><div class="votes" data-testid="voting-grid">${
          S.players.filter(p => p.id !== S.me.id).map(p =>
            `<button class="vote" data-act="vote" data-id="${p.id}" data-testid="vote-player-btn">${avatar(p.name)}<span>${esc(p.name)}</span></button>`).join('')}</div>`;
    const voted = S.players.filter(p => p.connected && p.voted).length;
    return `<section class="card enter">${head}${body}
      <p class="muted">${esc(t('voted_count', {n: voted, m: connected().length}))}</p>
      ${isHost() ? btn('close_voting', t('btn_close'), {ok: S.all_voted, tid: 'close-voting-btn'}) : ''}</section>`;
  },
  tally() {
    const max = Math.max(1, ...Object.values(S.tally));
    const bars = [...S.players].sort((a, b) => S.tally[b.id] - S.tally[a.id]).map(p => `
      <div class="bar" data-testid="tally-row"><span>${esc(p.name)}</span><i style="--w:${S.tally[p.id] / max * 100}%"></i><b>${S.tally[p.id]}</b></div>`).join('');
    if (S.outcome === 'tie') return `<section class="card enter center tie" data-testid="tie-panel"><h2>${esc(t('tie_title'))}</h2>
      <p>${esc(t('tie_text'))}</p>
      <div class="bars">${bars}</div>
      ${isHost() ? btn('back_to_game', t('btn_back_game'), {tid: 'back-to-game-btn'}) : `<p class="muted">${esc(t('wait_host'))}</p>`}</section>`;
    return `<section class="card enter center"><p class="muted">${esc(t('suspect_label'))}</p>
      <div class="suspect">${avatar(nameOf(S.suspect))}<h2>${esc(nameOf(S.suspect))}</h2></div>
      <div class="bars">${bars}</div>
      ${isHost() ? btn('reveal', t('btn_reveal'), {tid: 'reveal-jobs-btn'}) : `<p class="muted">${esc(t('wait_reveal'))}</p>`}</section>`;
  },
  final() {
    const r = S.result, c = r.category || cat();
    return `<section class="card enter center ${r.correct ? 'win' : 'lose'}" data-testid="results-summary-card">
      <h2>${r.correct ? esc(t('win_title')) : esc(t('lose_title'))}</h2>
      <p>${esc(t('r_suspect'))}: <b>${esc(nameOf(r.suspect_id))}</b> · ${esc(t('r_impostor'))}: <b>${esc(r.impostor_name)}</b></p>
      <div class="jobs"><div><small>${esc(t('main_' + c))}</small><strong data-testid="result-main-word">${esc(r.main_job)}</strong></div>
        <div class="bad"><small>${esc(t('imp_' + c))}</small><strong data-testid="result-impostor-word">${r.impostor_job ? esc(r.impostor_job) : esc(t('imp_no_word'))}</strong></div></div>
      ${isHost() ? `<div class="row">${btn('new_round', t('btn_new_round'), {tid: 'play-again-btn'})}${btn('to_lobby', t('btn_back'), {cls: 'ghost', tid: 'back-to-lobby-btn'})}</div>`
                 : `<p class="muted">${esc(t('wait_decision'))}</p>`}</section>`;
  },
};

function renderJoin(err = '') {
  top.innerHTML = '';
  app.innerHTML = `<section class="card enter"><h2>${esc(t('join_title'))} <span class="codechip" dir="ltr">${esc(CODE)}</span></h2>
    <label><span>${esc(t('label_name'))}</span><input id="jn" maxlength="16" placeholder="${esc(t('ph_name_join'))}" data-testid="join-name-input"></label>
    <button class="btn primary" data-act="join" data-testid="join-submit-btn">${esc(t('btn_join'))}</button><p class="err" data-testid="join-error">${esc(err)}</p>
    <a class="link" href="/" data-testid="home-link">${esc(t('home_link'))}</a></section>`;
}

function render() {
  if (!S) return;
  if (S.round_no !== lastRound || S.phase === 'lobby') role = null;
  if (S.phase !== 'discussion') question = null;
  lastRound = S.round_no;
  const PH = PHASES();
  const idx = PH.findIndex(p => p[0] === S.phase);
  document.title = t('title_room', {code: S.code});
  top.innerHTML = `<div class="mini" dir="ltr" data-testid="topbar-code">${S.code}</div>
    <ol class="steps" data-testid="phase-stepper">${PH.map((p, i) => `<li class="${i === idx ? 'now' : i < idx ? 'done' : ''}">${p[1]}</li>`).join('')}</ol>
    <div class="who">${avatar(S.me.name)}<span>${esc(S.me.name)}</span></div>`;
  const changed = S.phase !== lastPhase;
  app.innerHTML = VIEWS[S.phase]();
  if (!changed) app.querySelector('.enter')?.classList.remove('enter');
  lastPhase = S.phase;
}

// ---------------------------------------------------------------- modal (stays until closed)
function showModal(title, text) {
  $('#modal')?.remove();
  const el = document.createElement('div');
  el.id = 'modal';
  el.className = 'modal-back';
  el.innerHTML = `<div class="modal" role="alertdialog" aria-modal="true" aria-labelledby="modal-title" data-testid="impostor-lost-modal">
    <div class="modal-icon" aria-hidden="true">📡</div>
    <h2 id="modal-title">${esc(title)}</h2><p data-testid="impostor-lost-text">${esc(text)}</p>
    <button class="btn primary" type="button" data-testid="modal-close-btn">${esc(t('close'))}</button></div>`;
  document.body.appendChild(el);
  el.querySelector('button').addEventListener('click', () => el.remove());
  el.querySelector('button').focus();
}

// -------------------------------------------------------------------- actions
const ACT = {
  async join() {
    const r = await call('join', {code: CODE, name: $('#jn').value});
    if (r.ok) store.set(CODE, r.token); else renderJoin(r.error);
  },
  async 'reveal-role'() {
    const r = await call('request_role');
    if (r.ok) { role = {word: r.job, impostor: !!r.impostor, hint: r.hint || null}; render(); }
  },
  async 'hide-role'() { role = null; render(); if (S.phase === 'reveal') await call('seen'); },
  async question() { const r = await call('question'); if (r.ok) { question = r.question; render(); } },
  async vote(id) { await call('vote', {target: id}); },
  async kick(id) { await call('kick', {target: id}); },
  async set(spec) {
    const [key, val] = spec.split(':');
    await call('settings', {[key]: key === 'hints' ? val === '1' : val});
  },
  async leave() { await call('leave'); store.del(CODE); location.href = '/'; },
  async copy(link) { try { await navigator.clipboard.writeText(link); toast(t('toast_copied'), 'good'); } catch { prompt(t('prompt_copy'), link); } },
};
app.addEventListener('click', e => {
  const b = e.target.closest('[data-act]');
  if (!b || b.disabled) return;
  const a = b.dataset.act;
  if (ACT[a]) ACT[a](b.dataset.id); else call(a);   // host/player actions map 1:1 to socket events
});
})();
