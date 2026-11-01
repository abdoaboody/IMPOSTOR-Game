(() => {
const CODE = document.body.dataset.code;
const PHASES = [['lobby','الانتظار'],['reveal','المهنة'],['discussion','النقاش'],['voting','التصويت'],['tally','النتيجة'],['final','الكشف']];
const app = $('#app'), top = $('#top');
let S = null, job = null, question = null, lastPhase = null, lastRound = null;

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

async function call(ev, data) {
  const r = await emit(ev, data);
  if (!r.ok) toast(r.error, 'err');
  return r;
}

// ------------------------------------------------------------------- helpers
const hue = n => [...n].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 360, 7);
const avatar = n => `<span class="av" style="--h:${hue(n)}">${esc([...n][0] || '?')}</span>`;
const btn = (act, label, {cls = 'primary', ok = true, id = ''} = {}) =>
  `<button class="btn ${cls}" data-act="${act}" ${id ? `data-id="${id}"` : ''} ${ok ? '' : 'disabled'}>${label}</button>`;
const chip = (on, yes, no) => `<span class="chip ${on ? 'yes' : ''}">${on ? yes : no}</span>`;
const isHost = () => S.me.is_host;
const connected = () => S.players.filter(p => p.connected);
const nameOf = id => (S.players.find(p => p.id === id) || {name: '؟'}).name;

function plist(status) {
  return `<ul class="plist">${S.players.map(p => `
    <li class="${p.connected ? '' : 'off'}">${avatar(p.name)}
      <span class="nm">${esc(p.name)}${p.id === S.me.id ? ' <small>(أنت)</small>' : ''}${p.is_host ? ' <span class="crown" title="المضيف">♛</span>' : ''}</span>
      ${p.connected ? (status ? status(p) : '') : '<span class="chip">غير متصل</span>'}
    </li>`).join('')}</ul>`;
}

function secretCard() {
  if (job !== null) return `<div class="secret open"><small>مهنتك السرية</small><strong>${esc(job)}</strong>
    ${btn('hide-role', S.phase === 'reveal' ? 'إخفاء ومتابعة' : 'إخفاء', {cls: 'ghost'})}</div>`;
  return `<div class="secret"><p>تأكد أن لا أحد ينظر إلى شاشتك</p>${btn('reveal-role', 'اضغط لإظهار مهنتك')}</div>`;
}

// ----------------------------------------------------------------------- views
const VIEWS = {
  lobby() {
    const link = location.origin + '/?code=' + S.code;
    return `<section class="card enter"><h2>غرفة الانتظار</h2>
      <div class="codebox"><div class="code" dir="ltr">${[...S.code].map(c => `<b>${c}</b>`).join('')}</div>
        <button class="btn ghost" data-act="copy" data-id="${esc(link)}">نسخ رابط الدعوة</button></div>
      <p class="muted">${S.players.length} / ${S.max_players} لاعبين · ${connected().length} متصلون</p>
      ${plist()}
      ${isHost() ? btn('start_game', 'ابدأ اللعبة', {ok: S.can_start}) + (S.can_start ? '' : '<p class="muted">يلزم 3 لاعبين متصلين على الأقل.</p>')
                 : '<p class="muted">بانتظار المضيف ليبدأ اللعبة…</p>'}
      ${btn('leave', 'مغادرة الغرفة', {cls: 'link'})}
    </section>`;
  },
  reveal() {
    if (S.me.seen) return `<section class="card enter center"><h2>تم ✓</h2><p class="muted">بانتظار بقية اللاعبين…</p>
      ${plist(p => chip(p.seen, 'شاهد مهنته', 'لم يشاهد'))}</section>`;
    return `<section class="card enter center"><h2>مهنتك السرية</h2>${secretCard()}</section>`;
  },
  discussion() {
    return `<section class="card enter"><h2>وقت النقاش</h2>
      <p class="muted">اسألوا بعضكم أسئلة غير مباشرة. من يجيب بشكل غريب؟</p>
      ${secretCard()}
      <div class="qbox">${question ? `<p class="q">${esc(question)}</p>` : '<p class="muted">لا تعرف ماذا تسأل؟ الاقتراحات اختيارية بالكامل.</p>'}
        ${btn('question', question ? 'سؤال آخر' : 'اقترح سؤالاً', {cls: 'ghost'})}</div>
      ${S.me.ready ? '<p class="ok">أنت جاهز للتصويت ✓</p>' : btn('ready', 'جاهز للتصويت')}
      ${plist(p => chip(p.ready, 'جاهز', 'لم يجهز'))}
      ${isHost() ? btn('start_voting', 'ابدأ التصويت', {ok: S.all_ready}) + (S.all_ready ? '' : '<p class="muted">ينتظر الجميع أن يصبحوا جاهزين.</p>') : ''}
    </section>`;
  },
  voting() {
    const head = `<h2>التصويت${S.vote_round > 1 ? ` <small>(الجولة ${S.vote_round})</small>` : ''}</h2>`;
    const body = S.me.voted
      ? '<p class="ok">تم تسجيل صوتك ✓ — صوتك سرّي حتى إغلاق التصويت.</p>'
      : `<p class="muted">من تظن أنه المحتال؟ لا يمكنك تغيير صوتك بعد الإرسال.</p><div class="votes">${
          S.players.filter(p => p.id !== S.me.id).map(p =>
            `<button class="vote" data-act="vote" data-id="${p.id}">${avatar(p.name)}<span>${esc(p.name)}</span></button>`).join('')}</div>`;
    const voted = S.players.filter(p => p.connected && p.voted).length;
    return `<section class="card enter">${head}${body}
      <p class="muted">صوّت ${voted} من ${connected().length}</p>
      ${isHost() ? btn('close_voting', 'أغلق التصويت وأظهر النتيجة', {ok: S.all_voted}) : ''}</section>`;
  },
  tally() {
    const max = Math.max(1, ...Object.values(S.tally));
    const bars = [...S.players].sort((a, b) => S.tally[b.id] - S.tally[a.id]).map(p => `
      <div class="bar"><span>${esc(p.name)}</span><i style="--w:${S.tally[p.id] / max * 100}%"></i><b>${S.tally[p.id]}</b></div>`).join('');
    if (S.outcome === 'tie') return `<section class="card enter center tie"><h2 dir="ltr">IT'S A TIE!</h2>
      <p>في تعادل في التصويت! اتناقشوا واسألوا بعض أسئلة تانية عشان تتأكدوا مين الـ Impostor.</p>
      <div class="bars">${bars}</div>
      ${isHost() ? btn('new_vote', 'ابدأ تصويتاً جديداً') : '<p class="muted">بانتظار المضيف…</p>'}</section>`;
    return `<section class="card enter center"><p class="muted">المشتبه به الأول</p>
      <div class="suspect">${avatar(nameOf(S.suspect))}<h2>${esc(nameOf(S.suspect))}</h2></div>
      <div class="bars">${bars}</div>
      ${isHost() ? btn('reveal', 'اكشف المهنة الصحيحة') : '<p class="muted">بانتظار المضيف ليكشف المهنة…</p>'}</section>`;
  },
  final() {
    const r = S.result;
    return `<section class="card enter center ${r.correct ? 'win' : 'lose'}">
      <h2>${r.correct ? 'أمسكتم المحتال! 🎉' : 'أخطأتم… المحتال نجا 😈'}</h2>
      <p>المشتبه به: <b>${esc(nameOf(r.suspect_id))}</b> · المحتال الحقيقي: <b>${esc(r.impostor_name)}</b></p>
      <div class="jobs"><div><small>المهنة الصحيحة</small><strong>${esc(r.main_job)}</strong></div>
        <div class="bad"><small>مهنة المحتال</small><strong>${esc(r.impostor_job)}</strong></div></div>
      ${isHost() ? `<div class="row">${btn('new_round', 'جولة جديدة')}${btn('to_lobby', 'العودة للغرفة', {cls: 'ghost'})}</div>`
                 : '<p class="muted">بانتظار قرار المضيف…</p>'}</section>`;
  },
};

function renderJoin(err = '') {
  top.innerHTML = '';
  app.innerHTML = `<section class="card enter"><h2>الانضمام إلى الغرفة <span dir="ltr">${CODE}</span></h2>
    <label>اسمك<input id="jn" maxlength="16" placeholder="مثلاً: ليلى"></label>
    <button class="btn primary" data-act="join">انضم</button><p class="err">${esc(err)}</p>
    <a class="link" href="/">الصفحة الرئيسية</a></section>`;
}

function render() {
  if (!S) return;
  if (S.round_no !== lastRound || S.phase === 'lobby') job = null;
  if (S.phase !== 'discussion') question = null;
  lastRound = S.round_no;
  const idx = PHASES.findIndex(p => p[0] === S.phase);
  top.innerHTML = `<div class="mini" dir="ltr">${S.code}</div>
    <ol class="steps">${PHASES.map((p, i) => `<li class="${i === idx ? 'now' : i < idx ? 'done' : ''}">${p[1]}</li>`).join('')}</ol>
    <div class="who">${avatar(S.me.name)}<span>${esc(S.me.name)}</span></div>`;
  const changed = S.phase !== lastPhase;
  app.innerHTML = VIEWS[S.phase]();
  if (!changed) app.querySelector('.enter')?.classList.remove('enter');
  lastPhase = S.phase;
}

// -------------------------------------------------------------------- actions
const ACT = {
  async join() {
    const r = await call('join', {code: CODE, name: $('#jn').value});
    if (r.ok) store.set(CODE, r.token); else renderJoin(r.error);
  },
  async 'reveal-role'() { const r = await call('request_role'); if (r.ok) { job = r.job; render(); } },
  async 'hide-role'() { job = null; render(); if (S.phase === 'reveal') await call('seen'); },
  async question() { const r = await call('question'); if (r.ok) { question = r.question; render(); } },
  async vote(id) { await call('vote', {target: id}); },
  async leave() { await call('leave'); store.del(CODE); location.href = '/'; },
  async copy(link) { try { await navigator.clipboard.writeText(link); toast('تم نسخ الرابط', 'good'); } catch { prompt('انسخ الرابط:', link); } },
};
app.addEventListener('click', e => {
  const b = e.target.closest('[data-act]');
  if (!b || b.disabled) return;
  const a = b.dataset.act;
  if (ACT[a]) ACT[a](b.dataset.id); else call(a);   // host/player actions map 1:1 to socket events
});
})();
