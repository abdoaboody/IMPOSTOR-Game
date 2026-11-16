// i18n — Arabic (default, RTL) + Italian (LTR). The choice is remembered per device.
// Usage: I18N.t('key', {vars}); I18N.toggle(); I18N.lang -> 'ar' | 'it'.
window.I18N = (() => {
  const DICT = {
    ar: {
      game_name: 'المحتال',
      title_home: 'المحتال — لعبة جماعية',
      title_room: 'غرفة {code} — المحتال',
      hero_badge: 'لعبة جماعية بالوقت الحقيقي',
      tagline: 'الكل يحمل نفس المهنة… إلا واحداً. ناقشوا، اسألوا، وكشفوه قبل أن يكشفكم.',
      lang_btn: 'Italiano',
      lang_aria: 'تغيير اللغة إلى الإيطالية',
      conn_lost: 'انقطع الاتصال… جارٍ إعادة المحاولة',
      timeout_err: 'انتهت مهلة الاتصال، حاول مجدداً.',
      loader_aria: 'جارٍ التحميل',

      tab_create: 'إنشاء غرفة',
      tab_join: 'الانضمام لغرفة',
      label_name: 'اسمك',
      label_max: 'الحد الأقصى للاعبين',
      label_code: 'رمز الغرفة',
      ph_name_create: 'مثلاً: جو',
      ph_name_join: 'مثلاً: سارة',
      btn_create: 'أنشئ الغرفة',
      btn_join: 'انضم',

      credit_made: 'صُنعت هذه اللعبة بواسطة',
      credit_github: 'مشروعنا على GitHub',
      credit_aria: 'بطاقة صانع اللعبة',

      phase_lobby: 'الانتظار',
      phase_reveal: 'المهنة',
      phase_discussion: 'النقاش',
      phase_voting: 'التصويت',
      phase_tally: 'النتيجة',
      phase_final: 'الكشف',

      you: '(أنت)',
      host_crown: 'المضيف',
      offline: 'غير متصل',
      lobby_title: 'غرفة الانتظار',
      copy_invite: 'نسخ رابط الدعوة',
      players_count: '{n} / {m} لاعبين · {c} متصلون',
      btn_start: 'ابدأ اللعبة',
      need_three: 'يلزم 3 لاعبين متصلين على الأقل.',
      wait_start: 'بانتظار المضيف ليبدأ اللعبة…',
      btn_leave: 'مغادرة الغرفة',

      secret_title: 'مهنتك السرية',
      secret_warn: 'تأكد أن لا أحد ينظر إلى شاشتك',
      btn_show: 'اضغط لإظهار مهنتك',
      btn_hide_follow: 'إخفاء ومتابعة',
      btn_hide: 'إخفاء',
      done: 'تم ✓',
      wait_others: 'بانتظار بقية اللاعبين…',
      seen_yes: 'شاهد مهنته',
      seen_no: 'لم يشاهد',

      disc_title: 'وقت النقاش',
      disc_hint: 'اسألوا بعضكم أسئلة غير مباشرة. من يجيب بشكل غريب؟',
      q_hint: 'لا تعرف ماذا تسأل؟ الاقتراحات اختيارية بالكامل.',
      btn_q1: 'اقترح سؤالاً',
      btn_q2: 'سؤال آخر',
      ready_ok: 'أنت جاهز للتصويت ✓',
      btn_ready: 'جاهز للتصويت',
      ready_yes: 'جاهز',
      ready_no: 'لم يجهز',
      btn_start_vote: 'ابدأ التصويت',
      wait_ready: 'ينتظر الجميع أن يصبحوا جاهزين.',

      vote_title: 'التصويت',
      vote_round: '(الجولة {n})',
      voted_ok: 'تم تسجيل صوتك ✓ — صوتك سرّي حتى إغلاق التصويت.',
      vote_hint: 'من تظن أنه المحتال؟ لا يمكنك تغيير صوتك بعد الإرسال.',
      voted_count: 'صوّت {n} من {m}',
      btn_close: 'أغلق التصويت وأظهر النتيجة',

      tie_title: 'تعادل!',
      tie_text: 'في تعادل في التصويت! اتناقشوا واسألوا بعض أسئلة تانية عشان تتأكدوا مين الـ Impostor.',
      btn_new_vote: 'ابدأ تصويتاً جديداً',
      wait_host: 'بانتظار المضيف…',
      suspect_label: 'المشتبه به الأول',
      btn_reveal: 'اكشف المهنة الصحيحة',
      wait_reveal: 'بانتظار المضيف ليكشف المهنة…',

      win_title: 'أمسكتم المحتال! 🎉',
      lose_title: 'أخطأتم… المحتال نجا 😈',
      r_suspect: 'المشتبه به',
      r_impostor: 'المحتال الحقيقي',
      job_main: 'المهنة الصحيحة',
      job_imp: 'مهنة المحتال',
      btn_new_round: 'جولة جديدة',
      btn_back: 'العودة للغرفة',
      wait_decision: 'بانتظار قرار المضيف…',

      join_title: 'الانضمام إلى الغرفة',
      home_link: 'الصفحة الرئيسية',
      toast_copied: 'تم نسخ الرابط',
      prompt_copy: 'انسخ الرابط:',
    },

    it: {
      game_name: "L'Impostore",
      title_home: "L'Impostore — gioco di gruppo",
      title_room: "Stanza {code} — L'Impostore",
      hero_badge: 'Gioco di gruppo in tempo reale',
      tagline: 'Tutti hanno la stessa professione… tranne uno. Discutete, fate domande e smascheratelo prima che sia lui a smascherarvi.',
      lang_btn: 'عربي',
      lang_aria: "Cambia lingua in arabo",
      conn_lost: 'Connessione interrotta… riprovo',
      timeout_err: 'Connessione scaduta, riprova.',
      loader_aria: 'Caricamento',

      tab_create: 'Crea stanza',
      tab_join: 'Entra in stanza',
      label_name: 'Il tuo nome',
      label_max: 'Giocatori massimi',
      label_code: 'Codice stanza',
      ph_name_create: 'es: Gio',
      ph_name_join: 'es: Sara',
      btn_create: 'Crea la stanza',
      btn_join: 'Entra',

      credit_made: 'Questo gioco è stato creato da',
      credit_github: 'Il nostro progetto su GitHub',
      credit_aria: "Scheda dell'autore del gioco",

      phase_lobby: 'Atesa',
      phase_reveal: 'Ruolo',
      phase_discussion: 'Discussione',
      phase_voting: 'Voto',
      phase_tally: 'Risultato',
      phase_final: 'Rivelazione',

      you: '(tu)',
      host_crown: 'Host',
      offline: 'Non in linea',
      lobby_title: "Sala d'attesa",
      copy_invite: 'Copia il link di invito',
      players_count: '{n} / {m} giocatori · {c} in linea',
      btn_start: 'Inizia la partita',
      need_three: 'Servono almeno 3 giocatori in linea.',
      wait_start: "In attesa che l'host inizi la partita…",
      btn_leave: 'Lascia la stanza',

      secret_title: 'La tua professione segreta',
      secret_warn: 'Assicurati che nessuno guardi il tuo schermo',
      btn_show: 'Tocca per vedere la tua professione',
      btn_hide_follow: 'Nascondi e continua',
      btn_hide: 'Nascondi',
      done: 'Fatto ✓',
      wait_others: 'In attesa degli altri giocatori…',
      seen_yes: 'Ha visto il ruolo',
      seen_no: 'Non ha visto',

      disc_title: 'Tempo di discussione',
      disc_hint: 'Fatevi domande indirette. Chi risponde in modo strano?',
      q_hint: 'Non sai cosa chiedere? I suggerimenti sono facoltativi.',
      btn_q1: 'Suggerisci una domanda',
      btn_q2: "Un'altra domanda",
      ready_ok: 'Sei pronto per votare ✓',
      btn_ready: 'Pronto per votare',
      ready_yes: 'Pronto',
      ready_no: 'Non pronto',
      btn_start_vote: 'Avvia la votazione',
      wait_ready: 'Tutti devono essere pronti.',

      vote_title: 'Votazione',
      vote_round: '(Turno {n})',
      voted_ok: 'Voto registrato ✓ — resterà segreto fino alla chiusura.',
      vote_hint: 'Chi sospetti? Non puoi cambiare il tuo voto dopo averlo inviato.',
      voted_count: 'Hanno votato {n} di {m}',
      btn_close: 'Chiudi la votazione e mostra il risultato',

      tie_title: 'PAREGGIO!',
      tie_text: "Siete in pareggio! Discutete ancora e fatevi altre domande per scoprire chi è l'impostore.",
      btn_new_vote: 'Nuova votazione',
      wait_host: "In attesa dell'host…",
      suspect_label: 'Il principale sospettato',
      btn_reveal: 'Rivela la professione giusta',
      wait_reveal: "In attesa che l'host riveli la professione…",

      win_title: "Avete preso l'impostore! 🎉",
      lose_title: "Avete sbagliato… l'impostore è scappato 😈",
      r_suspect: 'Sospettato',
      r_impostor: "L'impostore vero",
      job_main: 'La professione giusta',
      job_imp: "La professione dell'impostore",
      btn_new_round: 'Nuova partita',
      btn_back: 'Torna alla sala',
      wait_decision: "In attesa della decisione dell'host…",

      join_title: 'Entra nella stanza',
      home_link: 'Pagina iniziale',
      toast_copied: 'Link copiato!',
      prompt_copy: 'Copia il link:',
    },
  };

  let lang = 'ar';
  try { lang = localStorage.getItem('impostor:lang') === 'it' ? 'it' : 'ar'; } catch {}

  function t(key, vars) {
    let s = (DICT[lang] && DICT[lang][key]) || DICT.ar[key] || key;
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
    return s;
  }

  function apply() {
    const root = document.documentElement;
    root.lang = lang;
    root.dir = lang === 'ar' ? 'rtl' : 'ltr';
    const titleKey = document.body && document.body.dataset.i18nTitle;
    if (titleKey) document.title = t(titleKey, {code: document.body.dataset.code || ''});
    document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll('[data-i18n-ph]').forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
    document.querySelectorAll('[data-i18n-aria]').forEach(el => { el.setAttribute('aria-label', t(el.dataset.i18nAria)); });
    window.dispatchEvent(new CustomEvent('langchange', {detail: {lang}}));
  }

  function setLang(l) {
    lang = l === 'it' ? 'it' : 'ar';
    try { localStorage.setItem('impostor:lang', lang); } catch {}
    apply();
  }

  return {
    t, apply, setLang,
    toggle: () => setLang(lang === 'ar' ? 'it' : 'ar'),
    get lang() { return lang; },
    isRTL: () => lang === 'ar',
  };
})();

I18N.apply();
