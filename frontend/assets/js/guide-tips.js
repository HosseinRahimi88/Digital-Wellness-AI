/*
  Digital Guide — the contextual help layer behind the mascot.

  Design intent: a guide that speaks once per page and goes quiet is
  decoration. This module is built so the guide can explain (a) what a
  page is for, (b) what each individual section on it means, (c) what
  each step of the check-in wizard is asking for and why it matters,
  and (d) what to do next from an empty state — all in the user's own
  language, all triggerable on demand.

  Honesty rules, same as the rest of the app:
  - The guide explains the PRODUCT, never the user's own numbers. It
    will say "this ring is your score" but never "your score is bad" —
    interpreting real values is the job of the prediction/coach layers,
    which have the actual data.
  - Nothing here claims a medical or diagnostic fact.
  - Every string exists in all four languages (en, fa, ar, zh); a
    missing translation falls back to English rather than showing
    nothing, but that fallback is the exception, not the norm.

  Public API:
    DWGuide.explain(topicKey, {force})   - speak about one topic
    DWGuide.attach(el, topicKey)         - make any element ask for help
    DWGuide.autoAttach(root)             - wire every [data-guide] in the DOM
    DWGuide.topicsFor(pageKey)           - the tour list for a page
    DWGuide.startTour(pageKey)           - walk that page's sections in order
*/
(function () {
  const SEEN_PREFIX = 'dwai_guide_seen_';
  const TOUR_PREFIX = 'dwai_guide_tour_';
  const DISMISS_PREFIX = 'dwai_guide_dismiss_';
  const SHOWN_AT_PREFIX = 'dwai_guide_shown_';
  const QUIET_UNTIL_KEY = 'dwai_guide_quiet_until';

  /* Fatigue control. A guide that keeps talking gets switched off, so
     dismissal is treated as data rather than as a no-op:

       - Two dismissals of the same topic and that topic stops
         auto-showing for TOPIC_QUIET_DAYS. It stays available on demand,
         because silencing a click would be a different (worse) bug.
       - Dismissing GLOBAL_DISMISS_LIMIT topics in one stretch reads as
         "not now, any of it", so ALL auto-showing pauses for
         GLOBAL_QUIET_HOURS. Explicit clicks still work.

     Both are per-browser, in localStorage, alongside the existing
     seen/tour flags this module already owns - not a second storage
     layer. */
  const DISMISSALS_BEFORE_QUIET = 2;
  const TOPIC_QUIET_DAYS = 14;
  const GLOBAL_DISMISS_LIMIT = 4;
  const GLOBAL_QUIET_HOURS = 24;

  const DAY_MS = 86400000;

  /* Per-topic metadata: which expression the guide wears, how important
     the topic is when several could fire at once, and whether it may
     ever auto-repeat.

     `face` values are exactly mascot.js's FACES keys - there is no second
     vocabulary to keep in sync. Before this existed, explain() rendered
     'neutral' for all 55 topics, so the guide's expression never had
     anything to do with what it was saying.

     `cooldownDays: 0` (the default) preserves the original behaviour:
     auto-show once per browser, ever. A positive value lets a topic
     become eligible again, which is opt-in precisely so this change
     cannot make the guide chattier by accident. */
  const META = {
    // Page overviews - orienting, friendly.
    landing:            { face: 'good',     priority: 90 },
    dashboard:          { face: 'good',     priority: 85 },
    checkin:            { face: 'neutral',  priority: 85 },
    weekly:             { face: 'good',     priority: 80 },
    coach:              { face: 'good',     priority: 80 },
    analytics:          { face: 'thinking', priority: 80 },
    whatif:             { face: 'thinking', priority: 80 },
    model:              { face: 'thinking', priority: 80 },
    profile:            { face: 'neutral',  priority: 75 },
    about:              { face: 'neutral',  priority: 70 },
    settings_panel:     { face: 'neutral',  priority: 70 },
    league:             { face: 'good',     priority: 75 },
    league_progress:    { face: 'good',     priority: 60 },
    league_rules:       { face: 'neutral',  priority: 75 },
    league_connect:     { face: 'neutral',  priority: 60 },
    plan_week_lock:        { face: 'neutral',  priority: 62 },
    plan_band:             { face: 'neutral',  priority: 61 },
    plan_personal_signal:  { face: 'neutral',  priority: 63 },
    schedule_regularity:   { face: 'thinking', priority: 70 },
    onboarding_intro:      { face: 'good', priority: 72 },
    progress_consistency:  { face: 'good',     priority: 58 },
    league_inbox:       { face: 'neutral',  priority: 60 },
    league_leaderboard: { face: 'good',     priority: 60 },
    coach_menu:         { face: 'good',     priority: 65 },
    demo_mode:          { face: 'great',    priority: 65 },
    future_self:        { face: 'thinking', priority: 65 },

    // Dashboard sections.
    dash_score:         { face: 'thinking', priority: 55 },
    dash_week_avg:      { face: 'neutral',  priority: 50 },
    dash_entries:       { face: 'neutral',  priority: 45 },
    dash_heatmap:       { face: 'neutral',  priority: 50 },
    dash_recs:          { face: 'good',     priority: 55 },
    dash_cohort:        { face: 'thinking', priority: 45 },

    // Check-in wizard steps - explaining what is being asked and why.
    wizard_demographics: { face: 'neutral',  priority: 40 },
    wizard_time:         { face: 'neutral',  priority: 40 },
    wizard_screen:       { face: 'neutral',  priority: 40 },
    wizard_device:       { face: 'neutral',  priority: 40 },
    wizard_sleep:        { face: 'neutral',  priority: 40 },
    wizard_mental:       { face: 'neutral',  priority: 40 },
    wizard_focus:        { face: 'neutral',  priority: 40 },
    wizard_derived:      { face: 'thinking', priority: 40 },
    demo_profiles:       { face: 'good',     priority: 35 },
    csv_import:          { face: 'neutral',  priority: 35 },

    // Result page - where the model explains itself.
    result_ring:          { face: 'thinking', priority: 70 },
    result_confidence:    { face: 'thinking', priority: 70 },
    result_dimensions:    { face: 'thinking', priority: 60 },
    result_shap:          { face: 'thinking', priority: 70 },
    result_recs:          { face: 'good',     priority: 65 },
    // An out-of-distribution day is a caution, not a scolding.
    result_ood:           { face: 'borderline', priority: 65 },
    result_roadmap:       { face: 'good',     priority: 60 },
    social_login:         { face: 'neutral',  priority: 50 },
    exclude_from_analysis:{ face: 'neutral',  priority: 55 },
    edit_today:{ face: 'thinking', priority: 57 },
    band_decision:{ face: 'thinking', priority: 59 },
    heatmap_exceptions:{ face: 'neutral', priority: 45 },
    violations:{ face: 'thinking', priority: 48 },
    plan_week_progress:{ face: 'good', priority: 52 },
    day_colours:{ face: 'neutral', priority: 50 },
    demo_lapsed:{ face: 'thinking', priority: 44 },

    // Everything else.
    weekly_plan:      { face: 'good',     priority: 60 },
    coach_chat:       { face: 'good',     priority: 55 },
    analytics_trend:  { face: 'thinking', priority: 50 },
    analytics_weekday:{ face: 'thinking', priority: 50 },
    whatif_sweep:     { face: 'thinking', priority: 50 },
    profile_avatar:   { face: 'good',     priority: 35 },
    profile_persona:  { face: 'good',     priority: 45 },
    profile_badges:   { face: 'great',    priority: 50 },
    profile_tone:     { face: 'neutral',  priority: 40 },
    privacy_controls: { face: 'neutral',  priority: 60 },
  };

  const DEFAULT_META = { face: 'neutral', priority: 50, cooldownDays: 0 };

  /* ---------------------------------------------------------------
     Topic copy. Keys are stable ids referenced by data-guide="..."
     attributes in the HTML and by the page tours below.
     --------------------------------------------------------------- */
  const TIPS = {
    en: {
      plan_week_lock: "This week's plan is fixed for the week on purpose. It's built once from your own pattern and then stays put, so a second check-in can't quietly swap the tasks out from under the boxes you've already ticked. Rebuilding it is a deliberate choice, and it clears this week's ticks because the tasks behind them would no longer exist.",
      plan_band: "The range this week is aimed at, taken from the days you've already logged - not from one prediction. A day that lands outside it is the one worth deciding about: count it, or mark it an exception.",
      plan_personal_signal: "A signal is flagged either because it's far from a healthy target, or because it's slipped from YOUR own normal - whichever is worse. That second half is why a drop from your usual 8 hours to 6.5 gets named even though 6.5 isn't alarming on its own, and the first half is why a habit that's always been rough never gets excused just for being your normal.",
      onboarding_intro: "Three questions, one at a time, and none of them is locked in - you can change any of it later from your profile. They are not a survey: your answer to each one changes what the app leads with. The goal decides which recommendations get pushed to the top, the purpose decides how your screen time is read, and the schedule question decides whether the plan can lean on a routine at all. Skipping is fine too; you will just get the general version until you fill them in.",
      schedule_regularity: "This one matters more than it looks. If your days aren't alike - rotating shifts, irregular hours - the plan stops leading with advice like 'same bedtime every night', which you can't act on, and leads with the one anchor you can actually keep. Answer it honestly rather than aspirationally.",
      progress_consistency: "Two different things used to read the same here. Holding a strong score steady all week is a result, not an absence of one - so a flat line at a good level is now named as consistency, and told apart from a flat line at a low level and from an average that's only flat because the days underneath it are swinging.",
      /* ---- Page-level overviews ---- */
      landing: "Welcome. This app reads your real daily habits with a trained machine-learning model and gives you an honest wellness score plus the exact reasons behind it. Nothing here is a horoscope — every number traces back to something you entered.",
      dashboard: "This is your home base. The ring is your most recent real score, the heatmap shows this week's check-ins, and below that are the exact factors that pushed your score up or down.",
      checkin: "This form is the only place your data comes from — nothing is pre-filled with a fake average. Answer for today, then submit to get a real prediction: a risk class, a 0–100 score, and the reasons why.",
      weekly: "This week versus last, side by side, plus a 7-day plan built from your last check-in's weakest signals — not a generic template.",
      coach: "Ask about your score, a specific area like sleep or focus, or what to prioritise. The Coach reads your real check-in and says so plainly when it doesn't have enough data.",
      analytics: "Your score over time and which weekdays tend to go better or worse — computed from your own logged history, so it gets more meaningful the more you log.",
      whatif: "A sandbox. Change one habit and watch the real model's prediction move, without touching your saved history.",
      model: "The model's real, current accuracy numbers — not marketing claims. Predicting for people it has never seen is genuinely hard, which is why these aren't 99%.",
      profile: "Your identity here: avatar, persona, badges and preferences. These personalise how the app talks to you; they never change what the model sees as input.",
      about: "How this project works, what data it uses, and where its limits are.",
      settings_panel: "Theme, ambient sound, sound effects and reduced motion are all independent switches — turning one off never turns off another. Demo Mode below fills the whole app with a realistic sample history so you can explore without logging real days first.",
      league: "Compare yourself mainly against your own past — that's the main number. Friends only appear if you've both explicitly agreed to it, and you choose exactly what each friend can see, one category at a time.",
      league_progress: "This is the real comparison: your current score against your own score 7 days ago, plus a preview of where the same real model thinks you could realistically end up if you keep going. Friends below are just context, never the main event.",
      league_rules: "Nothing is shared automatically. A friend only sees what you tick, only after you both accept these rules, and you can revoke access at any moment from here.",
      league_connect: "Enter someone's invite code, tick exactly what you'd share if they accept, and send. They see nothing until they explicitly approve. Testing this yourself needs a second account (a private/incognito window works) - one account cannot connect to itself.",
      league_inbox: "This is your notification inbox for League requests - approve, decline, and choose what you share back, all in one place, never a phone push.",
      league_leaderboard: "Your own score comes first, always. Friends only appear here for the categories they've personally agreed to share with you.",
      coach_menu: "More than a hundred ready-made questions, grouped by topic, each answered from your real current data — not a script. Ask your own question in the box below if none of them fit.",
      demo_mode: "One click fills the entire app — history, Coach, League, everything — with a realistic 23-day sample so you can explore or record a demo without logging real days first. It never touches your real check-ins.",
      future_self: "These numbers come from the same trained model as your score above, re-run on a hypothetical future pattern — not a guess or a script.",

      /* ---- Dashboard sections ---- */
      dash_score: "Your most recent real wellness score, 0–100, from the regression model. The arrow underneath compares it to your previous check-in — not to anyone else.",
      dash_week_avg: "The average score across this calendar week's check-ins. Days you've muted from your trend aren't counted here.",
      dash_entries: "How many check-ins you've logged in total. More entries make every trend on this page more trustworthy.",
      dash_heatmap: "Monday to Sunday of the current week. A filled square is a logged day, coloured by score. Click any square to mute that day from your averages — useful for a day you know was an outlier.",
      dash_recs: "The recommendations from your latest check-in, chosen by which factors the model found were dragging your score down.",
      dash_cohort: "How your averages compare with the wider population in the training data. Context, not a competition.",

      /* ---- Check-in wizard steps ---- */
      wizard_demographics: "Basic context about you. The model uses these to compare like with like — a student's typical pattern isn't a retiree's.",
      wizard_time: "Which day this entry describes. Weekends genuinely behave differently from weekdays in the data, so this matters.",
      wizard_screen: "Your screen minutes split by category. You don't enter a total — the app adds these up for you, so the parts can never contradict the whole.",
      wizard_device: "How fragmented your day was: notifications, pickups, app opens. In this dataset, how often you check tends to predict focus better than total hours do.",
      wizard_sleep: "Hours actually slept, and how rested you feel. Sleep is one of the strongest signals in the whole model.",
      wizard_mental: "Self-reported mood and stress. Answer honestly rather than optimistically — an inflated input gives you an inflated score, which helps nobody.",
      wizard_focus: "Focus, productivity, activity and caffeine. The last few pieces, then you get your result.",
      wizard_derived: "These are calculated from what you typed above — ratios, densities and indices the model expects. You never type these directly, so they can't disagree with your raw numbers.",
      demo_profiles: "In a hurry? Load a ready-made profile to see a full real prediction instantly. It runs the same model on the same pipeline — only the inputs are pre-filled.",
      csv_import: "Already track this elsewhere? Download the template, fill in several days at once, and upload it. Every valid row runs a real prediction and lands in your history immediately.",

      /* ---- Result page sections ---- */
      result_ring: "Read this ring from the middle outwards. The big number is a RANGE, not one exact figure — the model has a known average error, so it reports where your score most likely sits. Just under it, the smaller ≈ number is the single best estimate. The thin inner circle is a 0–100 gauge: it fills clockwise from the top to your score, the white tick marks that estimate, and the soft band around it is the give-or-take. The four thick outer arcs are something different — they are the four dimensions behind the score, each with its own colour in the legend below.",
      result_confidence: "How sure the classifier is about the category it picked. Worth reading alongside the score, not instead of it.",
      result_dimensions: "A transparent, rule-based breakdown of the same inputs by area. This is plain arithmetic you could redo by hand — deliberately separate from the model's own score above.",
      result_shap: "The specific factors that moved your score, from SHAP. Green pushed it up, red pulled it down. This is the model explaining itself, not a guess.",
      result_recs: "Actions matched to the factors that hurt your score. Each one carries a success metric so you can tell whether it worked.",
      result_ood: "A warning that some of today's values sit at the very edge of what the model has seen. The score is still real; just treat it with more caution.",
      result_roadmap: "A 7-day plan generated from today's own weakest signals, right here so you don't have to jump pages to see what's next.",
      social_login: "GitHub sign-in here is real: it uses your verified GitHub email, and only asks to read your profile and email address. If an account was created this way it has no password, so it signs in with the GitHub button rather than the password form - that is deliberate, otherwise knowing your address would be enough to claim the account.",
      day_colours: "Each square is a day, and it is scored on two separate things: did you check in, and did you do that day's plan task. Green is both. Orange means you checked in but the task went undone. Grey means the opposite - you did the work but never logged the day, which costs the app its data. Red is neither, and is the only full point. Today is shown but never counted; it is not over. None of this touches your wellness score - that number is the model reading your habits, and this is a record of how you and the app got on. Mixing the two would make one number mean two different things.",
      demo_lapsed: "The tick in the demo picker that decides whether this demo user kept up with their plan. Off, they logged every day and did the work. On, their history has real gaps, plan days sit undone, badges get spent paying for those days and violations are left over once the badges run out. It is the only way to see the greyed and red days, the violations panel and an empty badge wall - which is a large part of what this app actually does, and none of it was reachable while every demo user was a model citizen. Sixteen demo states become thirty-two.",
      plan_week_progress: "This plan is not rebuilt from scratch every Monday. A focus area you carried over from last week starts where you actually got to, not back at the gentlest version of itself - a third week on sleep should not open with \"set a fixed bedtime\" for the third time. The streak has to be unbroken to count: skip a week on a theme and it starts over, because picking up at the hardest tier after a month away is how a plan gets abandoned. The plan also has two halves, and the coach can show you both - ask it what to work on for the weak signals, and what you are doing well for the ones already worth protecting.",
      violations: "Your week runs in order: a day opens once the day before it is finished. When a day's date passes with the day left undone, it costs a badge - and if there is no badge left to spend, it is recorded here as an open violation instead. Nothing here is a verdict on you; it is a count with a way back. Earn a badge and one clears. While any are still open a newly earned badge is spent clearing rather than added to your wall, so the fastest route back to collecting badges is to finish the days you have. This section only appears when there is something in it.",
      heatmap_exceptions: "Days you answered \"that was an unusual day\" about. They are not the same as a day you excluded outright: an excluded day drops out of your averages completely, because you said it was not your data. An exception day happened - it stays in your history, stays on this row, and still pulls on your weekly range, just less than a normal day would. If this line is getting long, that is worth noticing on its own: a week that is mostly exceptions is not really an unusual week any more.",
      band_decision: "Your weekly plan aims at a RANGE, not a single number - the range under the ring. From the second day of a week onward, a day can land outside it, and that means one of two completely different things. \"It was an unusual day\" leaves your plan exactly as it is: the day still stays in your history and on your dashboard, and it still counts toward your range, just for less than a normal day rather than nothing at all - a day that vanished entirely would let a week be quietly curated into a straight line. \"Count it\" says this is where you are now, and rebuilds the REST of the week around the new range; the days you have already been through keep their tasks and their ticks, because those record things you actually did.",
      edit_today: "This only appears on a day you have already checked in on. One main check-in a day is the rule, so a second submission would REPLACE the first rather than add a day - the tick is you saying that is what you meant. Ticking it also refills the form with the answers you gave this morning, so correcting one number does not mean retyping the whole questionnaire, and once the update goes through your weekly plan and improvements are rebuilt from the new answers.",
      exclude_from_analysis: "Tick this for a hypothetical or test entry - it still gives you a real prediction, but nothing is saved to your history, so it can never skew your weekly analysis. Leave it unchecked for a normal, real check-in - today's actual weekday gets stamped in automatically, no need to pick it.",

      /* ---- Other sections ---- */
      weekly_plan: "A seven-day plan generated by rules from your real weakest areas. Tick tasks as you do them — progress is saved permanently, not just for this visit.",
      coach_chat: "Type a question, or /fit to load your latest check-in as context. The Coach only knows what your real data tells it.",
      analytics_trend: "Your score over time. Three or more check-ins make the direction meaningful; below that it's just points on a chart.",
      analytics_weekday: "Average score per weekday. A weekday you've only logged once is marked as low-confidence rather than presented as a pattern.",
      whatif_sweep: "Pick one field, and this runs the real model across its whole range so you can see exactly where your score turns.",
      profile_avatar: "Your picture stays on your own device and in your account record only. It's resized in your browser before saving, and it never reaches the model.",
      profile_persona: "A plain-language archetype derived from your real habits by documented rules — you can always see the numbers that earned it. Shown next to the statistical ML persona, which is a different thing.",
      profile_badges: "Earned strictly from real logged values. Each badge names the threshold it required, so none of them are mysterious.",
      profile_tone: "Changes how advice is worded — gentler, blunter, or clinical. It never changes which recommendations you get or their priority.",
      privacy_controls: "Export everything this app stores about you as a file, or delete your account and all its history permanently. Deletion cannot be undone.",
    },

    fa: {
      plan_week_lock: "برنامه‌ی این هفته عمداً برای کل هفته ثابت است. یک بار از الگوی خودت ساخته می‌شود و بعد سر جایش می‌ماند، تا یک چک‌این دوم نتواند بی‌صدا کارها را از زیر تیک‌هایی که زده‌ای عوض کند. بازسازی‌اش یک انتخاب آگاهانه است و تیک‌های این هفته را پاک می‌کند، چون کارهای پشت آن تیک‌ها دیگر وجود نخواهند داشت.",
      plan_band: "بازه‌ای که این هفته هدف گرفته، از روزهایی که تا حالا ثبت کرده‌ای گرفته شده — نه از یک پیش‌بینی. روزی که بیرون این بازه بیفتد همان روزی است که باید درباره‌اش تصمیم بگیری: به حساب بیاید، یا استثنا علامت بخورد.",
      plan_personal_signal: "یک سیگنال یا به این دلیل علامت می‌خورد که از هدف سلامت دور است، یا به این دلیل که از حالت عادیِ خودِ تو افت کرده — هرکدام که بدتر باشد. نیمه‌ی دوم دلیل این است که افت از ۸ ساعت همیشگی‌ات به ۶.۵ نام برده می‌شود، با اینکه ۶.۵ به‌تنهایی نگران‌کننده نیست؛ و نیمه‌ی اول دلیل این است که عادتی که همیشه بد بوده، فقط به‌خاطر «عادی بودن برای تو» هیچ‌وقت بخشیده نمی‌شود.",
      onboarding_intro: "سه سؤال، یکی‌یکی، و هیچ‌کدام قفل نمی‌شود — بعداً از پروفایلت می‌توانی همه را عوض کنی. این‌ها نظرسنجی نیستند: جواب هرکدام تغییر می‌دهد که برنامه با چه چیزی شروع کند. هدف تعیین می‌کند کدام توصیه‌ها بالا بیایند، کاربرد تعیین می‌کند زمان صفحه‌ات چطور خوانده شود، و سؤال برنامه‌ی روزانه تعیین می‌کند که اصلاً می‌شود روی یک روتین حساب کرد یا نه. رد کردنش هم اشکالی ندارد؛ فقط تا وقتی پرشان نکنی نسخه‌ی عمومی را می‌گیری.",
      schedule_regularity: "این یکی از چیزی که به نظر می‌رسد مهم‌تر است. اگر روزهایت شبیه هم نیستند — شیفت گردشی، ساعت‌های نامنظم — برنامه دیگر با توصیه‌هایی مثل «هر شب ساعت خواب ثابت» شروع نمی‌کند که نمی‌توانی اجرایش کنی، و با همان یک لنگرگاهی شروع می‌کند که واقعاً می‌توانی نگهش داری. صادقانه جواب بده، نه آرزومندانه.",
      progress_consistency: "قبلاً دو چیز متفاوت اینجا یکسان خوانده می‌شدند. نگه‌داشتن یک امتیاز قوی در تمام هفته خودش یک نتیجه است، نه نبودِ نتیجه — پس حالا خط صافِ در سطح خوب به‌عنوان «ثبات» نام‌گذاری می‌شود و از خط صافِ در سطح پایین، و از میانگینی که فقط چون روزهای زیرش نوسان دارند صاف به نظر می‌رسد، جدا می‌شود.",
      landing: 'خوش آمدی. این اپ عادت‌های واقعی روزانه‌ات را با یک مدل یادگیری ماشین آموزش‌دیده می‌خواند و یک امتیاز صادقانه‌ی سلامت به‌همراه دلیل دقیقش به تو می‌دهد. هیچ‌چیز اینجا فال نیست — هر عدد به چیزی که خودت وارد کرده‌ای برمی‌گردد.',
      dashboard: 'اینجا نقطه‌ی شروع توست. حلقه، آخرین امتیاز واقعی‌ات است، نقشه‌ی حرارتی چک‌این‌های این هفته را نشان می‌دهد، و پایین‌تر دقیقاً همان عواملی هستند که امتیازت را بالا یا پایین برده‌اند.',
      checkin: 'این فرم تنها منبع داده‌ی توست — هیچ‌چیزش با یک میانگین ساختگی از پیش پر نشده. برای امروز پاسخ بده و بفرست تا یک پیش‌بینی واقعی بگیری: یک دسته‌ی ریسک، یک امتیاز ۰ تا ۱۰۰، و دلیلش.',
      weekly: 'این هفته در برابر هفته‌ی قبل، کنار هم، به‌همراه یک برنامه‌ی ۷ روزه که از ضعیف‌ترین سیگنال‌های آخرین چک‌این تو ساخته شده — نه یک قالب عمومی.',
      coach: 'درباره‌ی امتیازت، یک حوزه‌ی خاص مثل خواب یا تمرکز، یا اولویت اولت بپرس. مربی داده‌ی واقعی‌ات را می‌خواند و اگر داده‌ی کافی نداشته باشد، صریح می‌گوید.',
      analytics: 'امتیازت در طول زمان و اینکه کدام روزهای هفته بهتر یا بدتر پیش می‌روند — از تاریخچه‌ی واقعی خودت محاسبه شده، پس هرچه بیشتر ثبت کنی معنادارتر می‌شود.',
      whatif: 'یک محیط آزمایشی. یک عادت را تغییر بده و ببین پیش‌بینی مدل واقعی چطور جابه‌جا می‌شود، بدون اینکه به تاریخچه‌ی ذخیره‌شده‌ات دست بخورد.',
      model: 'اعداد واقعی و فعلی دقت مدل — نه ادعای تبلیغاتی. پیش‌بینی برای افرادی که مدل هرگز ندیده واقعاً سخت است؛ برای همین این اعداد ۹۹٪ نیستند.',
      profile: 'هویت تو اینجا: تصویر، پرسونا، نشان‌ها و ترجیحات. این‌ها لحن گفتگوی اپ با تو را شخصی می‌کنند؛ هرگز ورودی مدل را تغییر نمی‌دهند.',
      about: 'اینکه این پروژه چطور کار می‌کند، از چه داده‌ای استفاده می‌کند، و محدودیت‌هایش کجاست.',
      settings_panel: 'تم، صدای محیطی، جلوه‌های صوتی و کاهش حرکت همه کلیدهای مستقل‌اند — خاموش‌کردن یکی بقیه را خاموش نمی‌کند. حالت دمو پایین‌تر کل اپ را با یک تاریخچه‌ی نمونه‌ی واقع‌گرایانه پر می‌کند تا بدون ثبت روزهای واقعی بگردی.',
      league: 'مقایسه‌ی اصلی با گذشته‌ی خودت است — آن عدد اصلی است. دوستان فقط وقتی ظاهر می‌شوند که هر دو صریحاً موافقت کرده باشید، و تو دقیقاً انتخاب می‌کنی هر دوست چه چیزی را ببیند، یک دسته در هر بار.',
      league_progress: 'مقایسه‌ی واقعی همین است: امتیاز فعلی‌ات در برابر امتیاز خودت از ۷ روز پیش، به‌علاوه یک پیش‌نمایش از جایی که همان مدل واقعی فکر می‌کند اگر ادامه بدهی واقع‌بینانه می‌توانی برسی. دوستان پایین صفحه فقط زمینه‌اند، هرگز محور اصلی نیستند.',
      league_rules: 'هیچ‌چیز خودکار به اشتراک گذاشته نمی‌شود. یک دوست فقط چیزی را می‌بیند که تیک زده‌ای، فقط بعد از اینکه هر دو این قوانین را پذیرفتید، و می‌توانی هر لحظه از همین‌جا دسترسی را لغو کنی.',
      league_connect: 'کد دعوت کسی را وارد کن، دقیقاً چیزی که اگر قبول کرد می‌خواهی به اشتراک بگذاری را تیک بزن، و بفرست. او تا وقتی صریحاً تایید نکند چیزی نمی‌بیند. برای تست خودت به یک اکانت دوم نیاز داری (یک پنجره‌ی ناشناس هم کافی است) — یک اکانت نمی‌تواند به خودش وصل شود.',
      league_inbox: 'این صندوق اعلان‌های تو برای درخواست‌های لیگ است — تایید، رد، و انتخاب اینکه چه چیزی در ازایش به اشتراک بگذاری، همه یک‌جا، هرگز نه به‌صورت نوتیف گوشی.',
      league_leaderboard: 'امتیاز خودت همیشه اول است. دوستان فقط برای دسته‌هایی که شخصاً موافقت کرده‌اند با تو به اشتراک بگذارند اینجا نشان داده می‌شوند.',
      coach_menu: 'بیش از صد سوال آماده، دسته‌بندی‌شده بر اساس موضوع، هرکدام از روی داده‌ی واقعی و فعلی تو پاسخ داده می‌شود — نه یک متن از پیش نوشته. اگر هیچ‌کدام مناسب نبود، سوال خودت را در کادر پایین بپرس.',
      demo_mode: 'با یک کلیک کل اپ — تاریخچه، مربی، لیگ، همه‌چیز — با یک نمونه‌ی واقع‌گرایانه‌ی ۲۳ روزه پر می‌شود تا بدون ثبت روزهای واقعی بگردی یا ازش دمو بگیری. هیچ‌وقت به چک‌این‌های واقعی‌ات دست نمی‌زند.',
      future_self: 'این اعداد از همان مدل آموزش‌دیده‌ای می‌آیند که امتیاز بالا را ساخته، فقط این‌بار روی یک الگوی فرضی آینده دوباره اجرا شده — نه یک حدس یا متن از پیش نوشته.',

      dash_score: 'آخرین امتیاز واقعی سلامت دیجیتال تو، ۰ تا ۱۰۰، از مدل رگرسیون. فلش زیرش آن را با چک‌این قبلی خودت مقایسه می‌کند، نه با کس دیگری.',
      dash_week_avg: 'میانگین امتیاز چک‌این‌های این هفته‌ی تقویمی. روزهایی که از روندت بی‌صدا کرده‌ای اینجا شمرده نمی‌شوند.',
      dash_entries: 'تعداد کل چک‌این‌هایی که ثبت کرده‌ای. هرچه بیشتر باشد، هر روندی در این صفحه قابل‌اعتمادتر است.',
      dash_heatmap: 'دوشنبه تا یکشنبه‌ی هفته‌ی جاری. مربع پرشده یعنی روز ثبت‌شده، با رنگ متناسب امتیاز. روی هر مربع کلیک کن تا آن روز از میانگین‌هایت حذف شود — برای روزی که می‌دانی پرت بوده مفید است.',
      dash_recs: 'توصیه‌های آخرین چک‌این تو، انتخاب‌شده بر اساس عواملی که مدل تشخیص داده امتیازت را پایین می‌کشیدند.',
      dash_cohort: 'مقایسه‌ی میانگین‌های تو با جمعیت گسترده‌تر در داده‌ی آموزشی. زمینه است، نه مسابقه.',

      wizard_demographics: 'زمینه‌ی پایه درباره‌ی تو. مدل از این‌ها برای مقایسه‌ی همسان استفاده می‌کند — الگوی معمول یک دانشجو با یک بازنشسته یکی نیست.',
      wizard_time: 'این ورودی مربوط به کدام روز است. آخر هفته‌ها در داده واقعاً متفاوت رفتار می‌کنند، پس این مهم است.',
      wizard_screen: 'دقایق صفحه‌نمایشت به تفکیک دسته. مجموع را وارد نمی‌کنی — اپ خودش جمع می‌زند، پس اجزا هرگز نمی‌توانند با کل در تناقض باشند.',
      wizard_device: 'اینکه روزت چقدر تکه‌تکه بوده: اعلان‌ها، برداشتن گوشی، باز کردن اپ. در این داده، تعداد دفعات چک‌کردن اغلب بهتر از مجموع ساعت‌ها تمرکز را پیش‌بینی می‌کند.',
      wizard_sleep: 'ساعت‌هایی که واقعاً خوابیده‌ای و اینکه چقدر سرحالی. خواب یکی از قوی‌ترین سیگنال‌های کل مدل است.',
      wizard_mental: 'حال‌وهوا و استرس خوداظهاری. صادقانه پاسخ بده نه خوش‌بینانه — ورودی متورم امتیاز متورم می‌دهد که به درد هیچ‌کس نمی‌خورد.',
      wizard_focus: 'تمرکز، بهره‌وری، فعالیت و کافئین. چند مورد آخر، بعد نتیجه‌ات را می‌گیری.',
      wizard_derived: 'این‌ها از چیزی که بالا نوشتی محاسبه شده‌اند — نسبت‌ها، تراکم‌ها و شاخص‌هایی که مدل انتظار دارد. اینها را مستقیم وارد نمی‌کنی، پس نمی‌توانند با اعداد خامت مخالف باشند.',
      demo_profiles: 'عجله داری؟ یک پروفایل آماده را بارگذاری کن تا فوراً یک پیش‌بینی واقعی کامل ببینی. همان مدل روی همان مسیر اجرا می‌شود — فقط ورودی‌ها از پیش پر شده‌اند.',
      csv_import: 'از قبل جای دیگری ثبت می‌کنی؟ قالب را دانلود کن، چند روز را یکجا پر کن و آپلود کن. هر ردیف معتبر یک پیش‌بینی واقعی اجرا می‌کند و بلافاصله در تاریخچه‌ات می‌نشیند.',

      result_ring: 'این حلقه را از وسط به بیرون بخوان. عدد بزرگ یک بازه است، نه یک رقم دقیق — چون مدل خطای میانگین مشخصی دارد، پس می‌گوید امتیازت به احتمال زیاد کجاست. درست زیرش، عدد کوچک‌تر با علامت ≈ همان بهترین برآورد تک‌عددی است. دایره‌ی نازک داخلی یک مقیاس ۰ تا ۱۰۰ است: از بالا در جهت عقربه‌های ساعت تا امتیازت پر می‌شود، خط سفید همان برآورد را نشان می‌دهد، و باند نرم اطرافش میزان عدم‌قطعیت را نشان می‌دهد. چهار کمان ضخیم بیرونی چیز دیگری‌اند — چهار بعد پشت این امتیاز‌اند، هرکدام با رنگ خودشان در راهنمای پایین.',
      result_confidence: 'اینکه طبقه‌بند چقدر به دسته‌ای که انتخاب کرده مطمئن است. ارزش دارد کنار امتیاز خوانده شود، نه به‌جای آن.',
      result_dimensions: 'یک تفکیک شفاف و قانون‌محور از همین ورودی‌ها بر اساس حوزه. این حساب ساده‌ای است که خودت هم می‌توانی انجام دهی — عمداً جدا از امتیاز خود مدل در بالا.',
      result_shap: 'عوامل مشخصی که امتیازت را جابه‌جا کردند، از SHAP. سبز بالا برده، قرمز پایین کشیده. این خود مدل است که توضیح می‌دهد، نه یک حدس.',
      result_recs: 'اقدام‌هایی متناسب با عواملی که به امتیازت آسیب زدند. هرکدام یک معیار موفقیت دارند تا بفهمی جواب داده یا نه.',
      result_ood: 'هشداری که بعضی از مقادیر امروز درست لبه‌ی چیزی هستند که مدل دیده. امتیاز همچنان واقعی است؛ فقط با احتیاط بیشتری با آن برخورد کن.',
      result_roadmap: 'یک برنامه‌ی ۷ روزه ساخته‌شده از ضعیف‌ترین سیگنال‌های همین امروز، درست همین‌جا تا لازم نباشد صفحه عوض کنی.',
      social_login: 'ورود با گیت‌هاب اینجا واقعی است: از ایمیل تاییدشده‌ی گیت‌هابت استفاده می‌کند و فقط اجازه‌ی خواندن پروفایل و ایمیل را می‌خواهد. اگر حسابی از این راه ساخته شود رمز عبور ندارد، پس با دکمه‌ی گیت‌هاب وارد می‌شود نه با فرم رمز — این عمدی است، وگرنه دانستن ایمیلت برای تصاحب حساب کافی بود.',
      day_colours: 'هر مربع یک روز است و روی دو چیز جدا سنجیده می‌شود: چک‌این کردی یا نه، و تمرین آن روز را انجام دادی یا نه. سبز یعنی هر دو. نارنجی یعنی چک‌این کردی ولی تمرین انجام نشد. خاکستری برعکسش است — کار را کردی ولی روز را ثبت نکردی، که هزینه‌اش برای برنامه از دست رفتن داده است. قرمز یعنی هیچ‌کدام، و تنها حالتی است که یک امتیاز کامل کم می‌کند. امروز نشان داده می‌شود ولی هیچ‌وقت حساب نمی‌شود؛ هنوز تمام نشده. هیچ‌کدام این‌ها به امتیاز سلامتت دست نمی‌زند — آن عدد خوانش مدل از عادت‌های توست و این سابقه‌ی همراهی تو با برنامه است. قاطی‌کردنشان یعنی یک عدد دو معنی داشته باشد.',
      demo_lapsed: 'همان تیکی در انتخابگر دمو که تعیین می‌کند این کاربر نمایشی به برنامه‌اش پایبند بوده یا نه. خاموش: هر روز ثبت کرده و تمرین‌ها را انجام داده. روشن: تاریخچه‌اش شکاف واقعی دارد، روزهایی از برنامه انجام‌نشده مانده، بج‌ها خرج جبران آن روزها شده و وقتی بجی نماند، تخلف باقی می‌ماند. این تنها راه دیدن روزهای خاکستری و قرمز، بخش تخلف‌ها و دیوار خالی نشان‌هاست — که بخش بزرگی از کار واقعی این برنامه است و تا وقتی همه‌ی کاربران نمایشی بی‌نقص بودند، اصلاً دیده نمی‌شد. شانزده حالت دمو می‌شود سی‌ودو.',
      plan_week_progress: 'این برنامه هر دوشنبه از صفر ساخته نمی‌شود. حوزه‌ای که از هفته‌ی قبل ادامه داده‌ای، از همان‌جایی شروع می‌شود که واقعاً رسیده‌ای، نه از ملایم‌ترین نسخه‌اش — هفته‌ی سوم روی خواب نباید دوباره با «ساعت خواب ثابت بگذار» شروع شود. این پیوستگی باید نشکند تا حساب شود: اگر یک هفته آن موضوع را رها کنی، از نو شروع می‌شود، چون شروع از سخت‌ترین سطح بعد از یک ماه دوری، راهِ رهاکردن برنامه است. برنامه دو نیمه هم دارد و مربی هر دو را نشانت می‌دهد — بپرس روی چی کار کنم برای سیگنال‌های ضعیف، و چی خوب پیش می‌رود برای آن‌هایی که همین حالا ارزش حفظ‌کردن دارند.',
      violations: 'هفته‌ات به ترتیب جلو می‌رود: هر روز وقتی باز می‌شود که روز قبلش تمام شده باشد. اگر تاریخ یک روز بگذرد و آن روز انجام نشده بماند، هزینه‌اش یک بج است — و اگر بجی برای خرج‌کردن نمانده باشد، به‌جایش همین‌جا به عنوان تخلف باز ثبت می‌شود. هیچ‌چیز اینجا حکمی درباره‌ی تو نیست؛ یک شمارش است با راه برگشت. یک بج بگیری، یکی پاک می‌شود. تا وقتی تخلفی باز است، بج تازه به‌جای اضافه‌شدن به دیوارت خرج پاک‌کردن می‌شود، پس سریع‌ترین راه برگشتن به جمع‌کردن بج، تمام‌کردن همان روزهایی است که داری. این بخش فقط وقتی نشان داده می‌شود که چیزی در آن باشد.',
      heatmap_exceptions: 'روزهایی که درباره‌شان گفتی «روز غیرعادی بود». این‌ها با روزی که کاملاً کنار گذاشته‌ای فرق دارند: روز کنارگذاشته‌شده به‌کل از میانگین‌هایت بیرون می‌رود، چون گفتی داده‌ی تو نیست. اما روز غیرعادی اتفاق افتاده — در تاریخچه‌ات می‌ماند، در همین ردیف می‌ماند، و هنوز بازه‌ی هفتگی‌ات را می‌کشد، فقط کمتر از یک روز عادی. اگر این خط دارد بلند می‌شود، خودش قابل توجه است: هفته‌ای که بیشترش استثناست، دیگر واقعاً هفته‌ی غیرعادی نیست.',
      band_decision: 'برنامه‌ی هفتگی‌ات یک بازه را هدف می‌گیرد، نه یک عدد — همان بازه‌ای که زیر حلقه می‌بینی. از روز دوم هفته به بعد، ممکن است یک روز بیرون از آن بیفتد، و این دقیقاً دو معنی کاملاً متفاوت دارد. «یک روز غیرعادی بود» برنامه‌ات را دست‌نخورده می‌گذارد: آن روز در تاریخچه و داشبوردت می‌ماند و هنوز روی بازه‌ات اثر می‌گذارد، فقط کمتر از یک روز عادی و نه هیچ — روزی که کاملاً ناپدید شود یعنی می‌شود هفته را بی‌سروصدا به یک خط صاف تبدیل کرد. «حساب شود» یعنی الان اینجا هستی، و باقی هفته حول بازه‌ی جدید بازسازی می‌شود؛ روزهایی که پشت سر گذاشته‌ای کارها و تیک‌هایشان را نگه می‌دارند، چون آن‌ها کارهایی را ثبت کرده‌اند که واقعاً انجام داده‌ای.',
      edit_today: 'این فقط در روزی نشان داده می‌شود که قبلاً برایش چک‌این کرده‌ای. قانون این است که هر روز فقط یک چک‌این اصلی ثبت می‌شود، پس ثبت دوم جای اولی را می‌گیرد، نه اینکه روز تازه‌ای اضافه کند — این تیک یعنی خودت همین را می‌خواهی. با زدن تیک، فرم با همان پاسخ‌های امروز صبحت پر می‌شود تا برای اصلاح یک عدد مجبور نباشی کل پرسشنامه را دوباره بنویسی، و بعد از به‌روزرسانی، برنامه‌ی هفتگی و بهبودهایت از روی پاسخ‌های تازه دوباره ساخته می‌شوند.',
      exclude_from_analysis: 'این را برای یک ورودی فرضی یا آزمایشی تیک بزن — همچنان یک پیش‌بینی واقعی می‌گیری، اما هیچ‌چیز در تاریخچه‌ات ذخیره نمی‌شود، پس هرگز تحلیل هفتگی‌ات را به‌هم نمی‌زند. برای یک چک‌این واقعی و عادی، تیک‌نخورده بگذار — روز واقعی امروز خودکار ثبت می‌شود، نیازی نیست انتخابش کنی.',

      weekly_plan: 'یک برنامه‌ی هفت‌روزه که با قوانین از ضعیف‌ترین حوزه‌های واقعی تو ساخته شده. کارها را که انجام دادی تیک بزن — پیشرفت برای همیشه ذخیره می‌شود، نه فقط برای همین بازدید.',
      coach_chat: 'یک سؤال بنویس، یا /fit را بزن تا آخرین چک‌این‌ات به‌عنوان زمینه بارگذاری شود. مربی فقط چیزی را می‌داند که داده‌ی واقعی‌ات به او می‌گوید.',
      analytics_trend: 'امتیازت در طول زمان. سه چک‌این یا بیشتر جهت را معنادار می‌کند؛ کمتر از آن فقط چند نقطه روی نمودار است.',
      analytics_weekday: 'میانگین امتیاز به تفکیک روز هفته. روزی که فقط یک‌بار ثبت کرده‌ای به‌جای الگو، کم‌اعتماد علامت زده می‌شود.',
      whatif_sweep: 'یک فیلد انتخاب کن؛ این مدل واقعی را در کل بازه‌اش اجرا می‌کند تا دقیقاً ببینی امتیازت کجا تغییر جهت می‌دهد.',
      profile_avatar: 'تصویر تو فقط روی دستگاه خودت و در رکورد حسابت می‌ماند. قبل از ذخیره در مرورگرت کوچک می‌شود و هرگز به مدل نمی‌رسد.',
      profile_persona: 'یک کهن‌الگوی ساده که با قوانین مستند از عادت‌های واقعی تو استخراج شده — همیشه می‌توانی اعدادی که آن را ساخته‌اند ببینی. کنار پرسونای آماری ML نمایش داده می‌شود که چیز دیگری است.',
      profile_badges: 'صرفاً از مقادیر واقعی ثبت‌شده به دست می‌آیند. هر نشان آستانه‌ای که لازم داشته را نام می‌برد، پس هیچ‌کدام مرموز نیستند.',
      profile_tone: 'نحوه‌ی بیان توصیه‌ها را تغییر می‌دهد — ملایم‌تر، صریح‌تر یا بالینی. هرگز تغییر نمی‌دهد که چه توصیه‌هایی می‌گیری یا اولویتشان چیست.',
      privacy_controls: 'هرچه این اپ درباره‌ی تو ذخیره کرده را به‌صورت فایل خروجی بگیر، یا حساب و کل تاریخچه‌اش را برای همیشه حذف کن. حذف برگشت‌پذیر نیست.',
    },
    ar: {
      plan_week_lock: "خطة هذا الأسبوع ثابتة طوال الأسبوع عن قصد. تُبنى مرة واحدة من نمطك أنت ثم تبقى كما هي، كي لا يستطيع تسجيل ثانٍ أن يبدّل المهام بهدوء من تحت المربعات التي أشّرتها. وإعادة بنائها اختيار مقصود، وهي تمسح تأشيرات هذا الأسبوع لأن المهام التي تخصها لن تكون موجودة بعدها.",
      plan_band: "النطاق الذي يستهدفه هذا الأسبوع مأخوذ من الأيام التي سجّلتها بالفعل — لا من تنبؤ واحد. واليوم الذي يقع خارجه هو اليوم الجدير بقرار: أن يُحتسب، أو أن يُوسم كاستثناء.",
      plan_personal_signal: "تُوسم الإشارة إما لأنها بعيدة عن هدف صحي، أو لأنها تراجعت عن معتادك أنت — أيهما أسوأ. النصف الثاني هو سبب تسمية الهبوط من ثماني ساعات معتادة إلى ست ونصف رغم أن ست ونصف ليست مقلقة بذاتها، والنصف الأول هو سبب ألا تُعفى عادة كانت سيئة دوماً لمجرد أنها معتادك.",
      onboarding_intro: "ثلاثة أسئلة، واحداً تلو الآخر، ولا شيء منها نهائي — تستطيع تغييرها لاحقاً من ملفك. وهي ليست استبياناً: إجابتك عن كل سؤال تغيّر ما يبدأ به التطبيق. الهدف يحدّد أي التوصيات تتصدّر، والغرض يحدّد كيف يُقرأ وقت شاشتك، وسؤال الجدول يحدّد هل يمكن للخطة أن تتكئ على روتين أصلاً. وتخطّيها لا بأس به؛ ستحصل فقط على النسخة العامة حتى تملأها.",
      schedule_regularity: "هذا السؤال أهم مما يبدو. إن لم تكن أيامك متشابهة — ورديات متناوبة، ساعات غير منتظمة — فلن تبدأ الخطة بنصائح مثل «موعد نوم ثابت كل ليلة» التي لا تستطيع تنفيذها، بل بالمرساة الوحيدة التي تستطيع الحفاظ عليها فعلاً. أجب بصدق لا بأمنية.",
      progress_consistency: "كان شيئان مختلفان يُقرآن هنا بالطريقة نفسها. الحفاظ على درجة قوية ثابتة طوال الأسبوع نتيجة، لا غياب نتيجة — فصار الخط المستوي عند مستوى جيد يُسمّى ثباتاً، ويُميَّز عن خط مستوٍ عند مستوى منخفض، وعن متوسط بدا مستوياً فقط لأن الأيام تحته تتأرجح.",
      landing: "أهلاً. يقرأ هذا التطبيق عاداتك اليومية الحقيقية بنموذج تعلّم آلي مدرَّب، ويعطيك درجة عافية صادقة مع الأسباب الدقيقة وراءها. لا شيء هنا تنجيم — كل رقم يعود إلى شيء أدخلته أنت.",
      dashboard: "هذه قاعدتك. الحلقة هي أحدث درجة حقيقية لك، والخريطة الحرارية تعرض تسجيلات هذا الأسبوع، وتحتها العوامل التي رفعت درجتك أو خفضتها بالضبط.",
      checkin: "هذا النموذج هو المصدر الوحيد لبياناتك — لا شيء معبّأ مسبقاً بمتوسط مزيّف. أجب عن اليوم، ثم أرسل لتحصل على تنبؤ حقيقي: فئة مخاطرة، ودرجة من 0 إلى 100، والأسباب.",
      weekly: "هذا الأسبوع مقابل السابق، جنباً إلى جنب، مع خطة سبعة أيام مبنية على أضعف إشاراتك في آخر تسجيل — لا قالب عام.",
      coach: "اسأل عن درجتك، أو عن مجال بعينه مثل النوم أو التركيز، أو عمّا ينبغي أن تبدأ به. يقرأ المدرب تسجيلك الحقيقي، ويقول بوضوح حين لا تكفيه البيانات.",
      analytics: "درجتك عبر الوقت، وأي أيام الأسبوع تميل إلى أن تكون أفضل أو أسوأ — محسوبة من سجلك أنت، فتزداد معنى كلما سجّلت أكثر.",
      whatif: "مساحة تجريب. غيّر عادة واحدة وراقب تنبؤ النموذج الحقيقي وهو يتحرك، دون المساس بسجلك المحفوظ.",
      model: "أرقام دقة النموذج الحقيقية والحالية — لا ادعاءات تسويقية. التنبؤ لأشخاص لم يرهم قط صعب فعلاً، ولهذا ليست 99٪.",
      profile: "هويتك هنا: الصورة الرمزية، والشخصية، والأوسمة، والتفضيلات. هذه تخصّص طريقة حديث التطبيق معك؛ ولا تغيّر أبداً ما يراه النموذج كمُدخل.",
      about: "كيف يعمل هذا المشروع، وما البيانات التي يستخدمها، وأين تقف حدوده.",
      settings_panel: "المظهر، والصوت المحيط، والمؤثرات الصوتية، وتقليل الحركة كلها مفاتيح مستقلة — إطفاء أحدها لا يطفئ آخر أبداً. ووضع العرض بالأسفل يملأ التطبيق كله بسجل نموذجي واقعي لتستكشفه دون تسجيل أيام حقيقية أولاً.",
      league: "قارن نفسك أساساً بماضيك أنت — هذا هو الرقم الأهم. لا يظهر الأصدقاء إلا إذا وافق الطرفان صراحةً، وأنت تختار بالضبط ما يراه كل صديق، فئةً فئة.",
      league_progress: "هذه هي المقارنة الحقيقية: درجتك الآن مقابل درجتك أنت قبل سبعة أيام، مع لمحة عن المكان الذي يرى النموذج نفسه أنك قد تصل إليه واقعياً إن واصلت. الأصدقاء بالأسفل سياق فقط، لا الحدث الرئيسي.",
      league_rules: "لا شيء يُشارَك تلقائياً. لا يرى الصديق إلا ما تؤشّر عليه، وبعد أن يقبل الطرفان هذه القواعد، ويمكنك سحب الوصول في أي لحظة من هنا.",
      league_connect: "أدخل رمز دعوة شخص ما، وأشّر بالضبط على ما ستشاركه إن قَبِل، ثم أرسل. لا يرى شيئاً حتى يوافق صراحةً. لاختبار هذا بنفسك تحتاج حساباً ثانياً (نافذة تصفح خاص تكفي) — لا يمكن لحساب أن يتصل بنفسه.",
      league_inbox: "هذا صندوق إشعاراتك لطلبات الدوري — القبول والرفض واختيار ما تشاركه بالمقابل، كله في مكان واحد، ولا إشعار هاتف أبداً.",
      league_leaderboard: "درجتك أنت أولاً، دائماً. ولا يظهر الأصدقاء هنا إلا في الفئات التي وافقوا شخصياً على مشاركتها معك.",
      coach_menu: "أكثر من مئة سؤال جاهز، مرتّبة حسب الموضوع، يُجاب عن كل منها من بياناتك الحالية الحقيقية — لا من نص محفوظ. واسأل سؤالك في المربع بالأسفل إن لم يناسبك أي منها.",
      demo_mode: "نقرة واحدة تملأ التطبيق كله — السجل، والمدرب، والدوري، كل شيء — بعيّنة واقعية من ثلاثة وعشرين يوماً لتستكشف أو تسجّل عرضاً دون تسجيل أيام حقيقية أولاً. ولا يمسّ ذلك تسجيلاتك الحقيقية أبداً.",
      future_self: "تأتي هذه الأرقام من النموذج المدرَّب نفسه الذي أعطى درجتك أعلاه، مُعاد تشغيله على نمط مستقبلي افتراضي — لا تخميناً ولا نصاً محفوظاً.",
      dash_score: "أحدث درجة عافية حقيقية لك، من 0 إلى 100، من نموذج الانحدار. والسهم تحتها يقارنها بتسجيلك السابق — لا بأي شخص آخر.",
      dash_week_avg: "متوسط الدرجة عبر تسجيلات هذا الأسبوع التقويمي. والأيام التي كتمتها عن اتجاهك غير محسوبة هنا.",
      dash_entries: "كم تسجيلاً سجّلته إجمالاً. كلما زادت المدخلات، صار كل اتجاه في هذه الصفحة أجدر بالثقة.",
      dash_heatmap: "من الاثنين إلى الأحد في الأسبوع الحالي. المربع الممتلئ يوم مسجَّل، ملوّن حسب الدرجة. انقر أي مربع لكتم ذلك اليوم عن متوسطاتك — مفيد ليوم تعرف أنه كان استثناءً.",
      dash_recs: "توصيات آخر تسجيل لك، مختارة حسب العوامل التي وجد النموذج أنها تسحب درجتك إلى الأسفل.",
      dash_cohort: "كيف تقارَن متوسطاتك بعموم الناس في بيانات التدريب. سياق، لا منافسة.",
      wizard_demographics: "سياق أساسي عنك. يستخدمه النموذج ليقارن المتشابه بالمتشابه — فنمط الطالب المعتاد ليس نمط متقاعد.",
      wizard_time: "أي يوم يصفه هذا الإدخال. عطلات نهاية الأسبوع تتصرف فعلاً بشكل مختلف عن أيام العمل في البيانات، فهذا مهم.",
      wizard_screen: "دقائق شاشتك موزّعة حسب الفئة. أنت لا تُدخل مجموعاً — التطبيق يجمعها لك، فلا يمكن للأجزاء أن تناقض الكل.",
      wizard_device: "كم كان يومك مجزّأً: الإشعارات، ومرات التقاط الهاتف، وفتح التطبيقات. في هذه البيانات، عدد مرات تفقّدك يتنبأ بالتركيز أفضل من مجموع الساعات.",
      wizard_sleep: "الساعات التي نمتها فعلاً، ومدى شعورك بالراحة. النوم من أقوى الإشارات في النموذج كله.",
      wizard_mental: "المزاج والتوتر كما تصفهما أنت. أجب بصدق لا بتفاؤل — فالمُدخل المنفوخ يعطيك درجة منفوخة، وهذا لا ينفع أحداً.",
      wizard_focus: "التركيز، والإنتاجية، والنشاط، والكافيين. آخر القطع، ثم تحصل على نتيجتك.",
      wizard_derived: "هذه محسوبة مما كتبته أعلاه — نسب وكثافات ومؤشرات يتوقعها النموذج. أنت لا تكتبها مباشرةً أبداً، فلا يمكن أن تتعارض مع أرقامك الخام.",
      demo_profiles: "في عجلة؟ حمّل ملفاً جاهزاً لترى تنبؤاً حقيقياً كاملاً فوراً. يشغّل النموذج نفسه على المسار نفسه — المُدخلات وحدها معبّأة مسبقاً.",
      csv_import: "تتابع هذا في مكان آخر أصلاً؟ نزّل القالب، واملأ عدة أيام دفعةً واحدة، وارفعه. كل صف صالح يشغّل تنبؤاً حقيقياً ويستقر في سجلك فوراً.",
      result_ring: "اقرأ هذه الحلقة من المنتصف إلى الخارج. الرقم الكبير ليس رقماً دقيقاً واحداً بل نطاق - فالنموذج له خطأ متوسط معروف، لذا يعرض أين تقع درجتك على الأرجح. وتحته مباشرة، الرقم الأصغر بعلامة ≈ هو أفضل تقدير واحد. الدائرة الداخلية الرفيعة هي مقياس من 0 إلى 100: تمتلئ باتجاه عقارب الساعة من الأعلى حتى درجتك، والعلامة البيضاء تشير إلى ذلك التقدير، والنطاق اللين حولها هو هامش عدم اليقين. أما الأقواس السميكة الأربعة الخارجية فشيء مختلف تماماً - إنها الأبعاد الأربعة وراء الدرجة، ولكل منها لونه الخاص في المفتاح أسفله.",
      result_confidence: "كم المصنِّف واثق من الفئة التي اختارها. يستحق القراءة إلى جانب الدرجة، لا بدلاً منها.",
      result_dimensions: "تفصيل شفاف قائم على قواعد للمُدخلات نفسها حسب المجال. هذا حساب بسيط يمكنك إعادته بيدك — منفصل عمداً عن درجة النموذج أعلاه.",
      result_shap: "العوامل المحددة التي حرّكت درجتك، من SHAP. الأخضر رفعها، والأحمر خفضها. هذا النموذج يشرح نفسه، لا تخميناً.",
      result_recs: "إجراءات مطابقة للعوامل التي أضرّت بدرجتك. ولكل منها معيار نجاح لتعرف إن كان قد نفع.",
      result_ood: "تنبيه بأن بعض قيم اليوم تقع عند الحافة القصوى لما رآه النموذج. الدرجة ما تزال حقيقية؛ فقط تعامل معها بحذر أكبر.",
      result_roadmap: "خطة سبعة أيام مولّدة من أضعف إشارات اليوم نفسه، هنا مباشرة كي لا تضطر للتنقل بين الصفحات لترى ما التالي.",
      social_login: "تسجيل الدخول عبر GitHub هنا حقيقي: يستخدم بريدك الموثّق في GitHub، ولا يطلب سوى قراءة ملفك وعنوان بريدك. والحساب المنشأ بهذه الطريقة بلا كلمة مرور، فيدخل بزر GitHub لا بنموذج كلمة المرور — وهذا مقصود، وإلا لكفت معرفة عنوانك للاستيلاء على الحساب.",
      day_colours: "كل مربع يوم، ويُقيَّم على أمرين منفصلين: هل سجّلت، وهل نفّذت مهمة الخطة لذلك اليوم. الأخضر كلاهما. البرتقالي يعني أنك سجّلت لكن المهمة لم تُنفَّذ. الرمادي عكسه — أنجزت العمل لكنك لم تسجّل اليوم، وثمنه أن يفقد التطبيق بياناته. الأحمر لا هذا ولا ذاك، وهو وحده نقطة كاملة. اليوم الحالي يُعرض ولا يُحتسب أبداً؛ فهو لم ينتهِ. ولا شيء من هذا يمسّ درجة عافيتك — تلك قراءة النموذج لعاداتك، وهذا سجلّ لتفاعلك مع التطبيق. وخلطهما يجعل رقماً واحداً يعني شيئين.",
      demo_lapsed: "التأشير في منتقي العرض الذي يحدّد هل التزم هذا المستخدم التجريبي بخطته. مطفأ: سجّل كل يوم ونفّذ المهام. مُفعّل: في سجلّه فجوات حقيقية، وأيام خطة لم تُنفَّذ، وشارات صُرفت تعويضاً عنها، ومخالفات تبقى حين تنفد الشارات. وهي الطريقة الوحيدة لرؤية الأيام الرمادية والحمراء ولوحة المخالفات وجدار شارات فارغ — وهي جزء كبير مما يفعله هذا التطبيق فعلاً، ولم يكن أي منها قابلاً للوصول ما دام كل مستخدم تجريبي مثالياً. ستّ عشرة حالة عرض تصير اثنتين وثلاثين.",
      plan_week_progress: "هذه الخطة لا تُبنى من الصفر كل اثنين. مجال تركيز انتقل معك من الأسبوع الماضي يبدأ من حيث وصلت فعلاً، لا من أرقّ صوره — فأسبوع ثالث على النوم لا ينبغي أن يفتتح بـ«حدّد موعد نوم ثابت» للمرة الثالثة. ويجب ألا تنقطع السلسلة لتُحتسب: تخطَّ أسبوعاً في موضوع ما فيبدأ من جديد، لأن الاستئناف من أصعب مستوى بعد شهر من الانقطاع هو الطريق إلى هجر الخطة. وللخطة نصفان أيضاً، والمدرّب يعرض كليهما — اسأله على ماذا أعمل للإشارات الضعيفة، وما الذي أفعله جيداً لما يستحق الحماية الآن.",
      violations: "أسبوعك يسير بالترتيب: يُفتح اليوم بعد إتمام اليوم الذي قبله. وإذا مرّ تاريخ يوم وبقي دون تنفيذ، كلّف ذلك شارة — وإن لم تبقَ شارة تُصرف، سُجّل هنا كمخالفة مفتوحة بدلاً منها. لا شيء هنا حكم عليك؛ إنه عدد ومعه طريق للعودة. اكسب شارة تُمحَ واحدة. وما دامت هناك مخالفة مفتوحة تُصرَف الشارة الجديدة في المحو بدل أن تُضاف إلى جدارك، فأسرع طريق للعودة إلى جمع الشارات هو إتمام الأيام التي بين يديك. ولا يظهر هذا القسم إلا إذا كان فيه شيء.",
      heatmap_exceptions: "الأيام التي أجبت عنها بـ«كان يوماً غير معتاد». وهي ليست كاليوم الذي استبعدته تماماً: اليوم المستبعَد يخرج من متوسطاتك كلياً لأنك قلت إنه ليس بياناتك. أما اليوم غير المعتاد فقد حدث — يبقى في سجلّك، ويبقى في هذا الصف، ولا يزال يشدّ نطاقك الأسبوعي، لكن أقل من يوم عادي. وإن طال هذا السطر فذلك جدير بالانتباه بذاته: أسبوع معظمه استثناءات لم يعد أسبوعاً غير معتاد حقاً.",
      band_decision: "خطتك الأسبوعية تستهدف نطاقاً لا رقماً واحداً — النطاق الظاهر تحت الحلقة. من اليوم الثاني في الأسبوع فصاعداً قد يقع يوم خارجه، وهذا يعني أحد أمرين مختلفين تماماً. «كان يوماً غير معتاد» يترك خطتك كما هي تماماً: يبقى اليوم في سجلّك وعلى لوحتك، ولا يزال يؤثر في نطاقك، لكن بأقل من يوم عادي لا بلا شيء — فاليوم الذي يختفي تماماً يجعل من الممكن تهذيب الأسبوع بهدوء حتى يصير خطاً مستقيماً. و«احسبه» يعني أن هذا وضعك الآن، فيُعاد بناء بقية الأسبوع حول النطاق الجديد؛ والأيام التي مررت بها تحتفظ بمهامها وعلاماتها لأنها تسجّل أشياء فعلتها بالفعل.",
      edit_today: "لا يظهر هذا إلا في يوم سجّلت فيه من قبل. القاعدة تسجيل رئيسي واحد في اليوم، لذا فإن الإرسال الثاني يستبدل الأول ولا يضيف يوماً جديداً — والتأشير هو قولك إن هذا ما تقصده. التأشير يملأ النموذج أيضاً بإجاباتك من هذا الصباح، فتصحيح رقم واحد لا يعني إعادة كتابة الاستبيان كله، وبعد التحديث تُعاد صياغة خطتك الأسبوعية وتحسيناتك من الإجابات الجديدة.",
      exclude_from_analysis: "أشّر على هذا لإدخال افتراضي أو تجريبي — ستحصل على تنبؤ حقيقي، لكن لا شيء يُحفظ في سجلك، فلا يمكنه أن يخلّ بتحليلك الأسبوعي. اتركه دون تأشير للتسجيل العادي الحقيقي — يوم الأسبوع الفعلي يُختم تلقائياً، ولا حاجة لاختياره.",
      weekly_plan: "خطة سبعة أيام تولّدها قواعد من أضعف مجالاتك الحقيقية. أشّر على المهام وأنت تنجزها — التقدّم يُحفظ بشكل دائم، لا لهذه الزيارة فقط.",
      coach_chat: "اكتب سؤالاً، أو /fit لتحميل آخر تسجيل لك كسياق. لا يعرف المدرب إلا ما تخبره به بياناتك الحقيقية.",
      analytics_trend: "درجتك عبر الوقت. ثلاثة تسجيلات أو أكثر تجعل الاتجاه ذا معنى؛ وما دون ذلك مجرد نقاط على رسم.",
      analytics_weekday: "متوسط الدرجة لكل يوم من أيام الأسبوع. واليوم الذي سجّلته مرة واحدة فقط يوسَم بأنه ضعيف الثقة بدل تقديمه كنمط.",
      whatif_sweep: "اختر حقلاً واحداً، وهذا يشغّل النموذج الحقيقي عبر مداه كله لترى بالضبط أين تنعطف درجتك.",
      profile_avatar: "تبقى صورتك على جهازك أنت وفي سجل حسابك فقط. يُعاد تحجيمها في متصفحك قبل الحفظ، ولا تصل إلى النموذج أبداً.",
      profile_persona: "نمط بلغة بسيطة مستخرَج من عاداتك الحقيقية بقواعد موثّقة — ويمكنك دائماً رؤية الأرقام التي استحقته. يُعرض بجوار شخصية التعلّم الآلي الإحصائية، وهي شيء مختلف.",
      profile_badges: "تُكتسب حصراً من قيم مسجَّلة حقيقية. وكل وسام يذكر العتبة التي تطلّبها، فلا غموض في أي منها.",
      profile_tone: "يغيّر صياغة النصيحة — ألطف، أو أصرح، أو أكثر جفافاً. ولا يغيّر أبداً أي التوصيات تصلك ولا أولويتها.",
      privacy_controls: "صدّر كل ما يخزّنه هذا التطبيق عنك كملف، أو احذف حسابك وكل سجله نهائياً. الحذف لا يمكن التراجع عنه.",
    },
    zh: {
      plan_week_lock: "本周的计划是刻意在整周内固定的。它根据你自己的模式生成一次，然后就保持不变，这样第二次打卡就无法在你已勾选的方框底下悄悄换掉任务。重新生成是一个有意的选择，并且会清空本周的勾选，因为它们对应的任务已经不存在了。",
      plan_band: "本周瞄准的区间来自你已经记录的那些天——而不是某一次预测。落在区间之外的那一天，正是值得你做决定的：算进去，还是标记为例外。",
      plan_personal_signal: "一个信号被标记，要么是因为它离健康目标很远，要么是因为它相对「你自己的正常水平」下滑了——取两者中更严重的那个。后半部分解释了为什么从你惯常的 8 小时降到 6.5 小时会被点名，尽管 6.5 本身并不吓人；前半部分解释了为什么一个一直很糟的习惯，不会仅因为「这就是你的常态」而被放过。",
      onboarding_intro: "三个问题，一次一个，而且都不是定死的——之后随时可以在个人资料里改。它们不是问卷：每个答案都会改变这个应用优先呈现什么。目标决定哪些建议排在最前，用途决定你的屏幕时间怎么被解读，作息那道题则决定计划能不能依靠一套固定节奏。跳过也没关系；只是在你填之前，你拿到的会是通用版本。",
      schedule_regularity: "这个问题比看上去更重要。如果你每天都不一样——轮班、作息不规律——计划就不会再以「每晚固定就寝时间」这类你无法执行的建议开头，而是从你真正能守住的那一个锚点开始。请如实回答，而不是按理想状态回答。",
      progress_consistency: "以前这里有两种完全不同的情况被读成了同一种。整周稳住一个不错的分数本身就是成果，而不是没有成果——所以现在处于良好水平的平直线会被称为「稳定」，并与处于低水平的平直线，以及那种只因底下每天大幅波动才显得平坦的平均值区分开来。",
      landing: "欢迎。这个应用用一个训练好的机器学习模型读取你真实的日常习惯，给你一个诚实的健康分数，以及背后确切的原因。这里没有任何星座占卜——每个数字都能追溯到你自己填的东西。",
      dashboard: "这里是你的主页。圆环是你最近一次的真实分数，热力图显示本周的记录，下面则是把你的分数推上去或拉下来的确切因素。",
      checkin: "这个表单是你数据的唯一来源——没有任何一项被虚假的平均值预先填好。为今天作答，然后提交，你会得到一个真实的预测：一个风险类别、一个 0–100 的分数，以及原因。",
      weekly: "本周与上周并排对照，再加上一份根据你上次记录中最弱的信号生成的七日计划——不是通用模板。",
      coach: "问你的分数，问某个具体方面比如睡眠或专注，或者问该先做什么。教练读的是你真实的记录，数据不够时它会直说。",
      analytics: "你的分数随时间的变化，以及哪些星期几往往更好或更差——都由你自己的记录算出，所以你记得越多，它就越有意义。",
      whatif: "一个沙盒。改动一个习惯，看真实模型的预测怎么变，而不会碰到你已保存的历史。",
      model: "模型真实的、当前的准确率数字——不是营销说辞。为从未见过的人做预测确实很难，这就是为什么这些数字不是 99%。",
      profile: "这里是你的身份：头像、人格、徽章和偏好。它们个性化了应用和你说话的方式；但绝不会改变模型看到的输入。",
      about: "这个项目如何运作、用了什么数据，以及它的边界在哪里。",
      settings_panel: "主题、环境音、音效和减少动效都是各自独立的开关——关掉一个绝不会关掉另一个。下面的演示模式会用一份逼真的示例历史填满整个应用，让你无需先记录真实的日子就能探索。",
      league: "主要是和你自己的过去比——那才是最重要的数字。只有在双方都明确同意后好友才会出现，而且你可以逐项决定每位好友能看到什么。",
      league_progress: "这才是真正的比较：你现在的分数对比你自己七天前的分数，再加上同一个真实模型认为你继续下去可能实际到达的位置。下面的好友只是背景，从来不是主角。",
      league_rules: "没有任何东西会自动分享。好友只能看到你勾选的内容，而且要在双方都接受这些规则之后，你也可以随时从这里撤回访问权限。",
      league_connect: "输入某人的邀请码，准确勾选对方接受后你愿意分享的内容，然后发送。在对方明确同意之前，他们什么也看不到。要亲自测试这个流程，需要第二个账号（一个隐私/无痕窗口就够了）——账号无法连接自己。",
      league_inbox: "这是你处理排行榜请求的通知箱——同意、拒绝、以及选择你回赠分享的内容，都在一个地方，而且永远不会有手机推送。",
      league_leaderboard: "你自己的分数永远排在最前面。好友只会在他们本人同意与你分享的那些类别里出现。",
      coach_menu: "一百多个现成的问题，按主题分组，每一个都根据你当前的真实数据来回答——不是照本宣科。如果都不合适，就在下面的框里问你自己的问题。",
      demo_mode: "一次点击就用一份逼真的二十三天样本填满整个应用——历史、教练、排行榜，全部——让你无需先记录真实的日子就能探索或录制演示。它绝不会碰你真实的记录。",
      future_self: "这些数字来自和上面你的分数同一个训练好的模型，只是在一个假设的未来模式上重新跑了一遍——不是猜测，也不是写死的脚本。",
      dash_score: "你最近一次真实的健康分数，0–100，来自回归模型。下面的箭头是把它和你上一次记录相比——不是和别人比。",
      dash_week_avg: "本自然周内所有记录的平均分。你从趋势里静音掉的日子不计入这里。",
      dash_entries: "你一共记录了多少次。记录越多，这一页上的每条趋势就越可靠。",
      dash_heatmap: "当前这一周的周一到周日。填色的方块是有记录的一天，颜色按分数。点任意方块可以把那天从你的平均值里静音——对你知道属于异常的日子很有用。",
      dash_recs: "来自你最近一次记录的建议，依据是模型发现哪些因素在把你的分数往下拉。",
      dash_cohort: "你的平均值与训练数据中更广泛人群的对比。这是背景，不是比赛。",
      wizard_demographics: "关于你的基本背景。模型用它来做同类相比——学生的典型模式不同于退休者的。",
      wizard_time: "这条记录描述的是哪一天。在数据里，周末的表现确实和工作日不同，所以这一项有意义。",
      wizard_screen: "你的屏幕分钟数按类别拆分。你不需要填总数——应用会替你相加，所以各部分永远不会和总和矛盾。",
      wizard_device: "你的一天有多碎片化：通知、拿起手机的次数、打开应用的次数。在这份数据里，你查看的频率对专注度的预测力，往往强于总时长。",
      wizard_sleep: "实际睡了多少小时，以及你觉得有多解乏。睡眠是整个模型里最强的信号之一。",
      wizard_mental: "你自己报告的情绪和压力。请诚实作答，而不是乐观作答——虚高的输入只会给你一个虚高的分数，那对谁都没好处。",
      wizard_focus: "专注、效率、活动量和咖啡因。最后几项，然后你就能拿到结果了。",
      wizard_derived: "这些是根据你上面填的内容算出来的——模型需要的比率、密度和指数。你从来不会直接填它们，所以它们不可能和你的原始数字打架。",
      demo_profiles: "赶时间？加载一个现成的档案，立刻看到一次完整的真实预测。它跑的是同一个模型、同一条流程——只有输入是预先填好的。",
      csv_import: "已经在别处记录了？下载模板，一次填好几天，然后上传。每一行有效数据都会跑一次真实预测，并立即进入你的历史。",
      result_ring: "这个圆环从中间往外读。中间的大数字不是一个精确的数值，而是一个区间——模型有一个已知的平均误差，所以它给出的是你分数最可能落在的范围。紧挨在它下面、带 ≈ 符号的小数字是单一的最佳估计值。内圈那条细线是一个 0–100 的刻度：它从顶部开始顺时针填充到你的分数，白色刻度标记的就是那个估计值，周围柔和的色带表示上下浮动的余地。外圈四条粗弧是完全不同的东西——它们是分数背后的四个维度，每一个在下方图例里都有自己的颜色。",
      result_confidence: "分类器对它选出的类别有多确定。这值得和分数一起读，而不是用来取代分数。",
      result_dimensions: "对同一批输入按领域做的、基于规则的透明拆解。这是你可以用手重算一遍的普通算术——刻意与上面模型自己的分数分开。",
      result_shap: "具体是哪些因素移动了你的分数，来自 SHAP。绿色把它推上去，红色把它拉下来。这是模型在解释它自己，不是猜的。",
      result_recs: "针对伤害了你分数的那些因素给出的行动。每一条都带一个成功指标，好让你判断它有没有奏效。",
      result_ood: "一个提醒：今天有些数值处在模型见过的范围的最边缘。分数依然是真实的，只是请更谨慎地对待它。",
      result_roadmap: "一份根据今天自己最弱的信号生成的七日计划，就放在这里，省得你为了看下一步而跳页。",
      social_login: "这里的 GitHub 登录是真的：它使用你在 GitHub 上已验证的邮箱，并且只请求读取你的资料和邮箱地址。用这种方式创建的账号没有密码，所以要用 GitHub 按钮登录，而不是密码表单——这是有意的，否则光知道你的邮箱地址就足以夺走账号。",
      day_colours: "每个方块是一天，并按两件独立的事来评定：你有没有记录，以及有没有做当天的计划任务。绿色是两样都做了。橙色表示你记录了，但任务没做。灰色相反——你做了事，却始终没有记录这一天，代价是这个应用失去了数据。红色是两样都没有，也是唯一扣满一分的情况。今天会显示但永远不计入；它还没结束。这些都不会影响你的健康分数——那是模型对你习惯的读数，而这只是你与应用相处的记录。把两者混在一起，会让一个数字同时代表两件事。",
      demo_lapsed: "演示选择器里的那个勾选项，决定这位演示用户有没有跟上他的计划。不勾：他每天都记录，也把任务做完了。勾上：他的历史里有真实的缺口，有些计划的日子没做，徽章被拿去抵偿那些日子，徽章用完后就留下未清的违规。这是看到灰色和红色日子、违规面板以及空徽章墙的唯一方式——而这些正是这个应用实际功能里很大的一块，只要每个演示用户都是模范生，它们就永远看不到。十六个演示状态因此变成三十二个。",
      plan_week_progress: "这份计划不会每周一从零开始。从上一周延续下来的重点，会从你实际到达的地方接着走，而不是退回它最温和的版本——第三周做睡眠，不该再一次以「设定固定就寝时间」开场。这条连续性必须不断才算数：某个主题空了一周就会重新开始，因为隔了一个月还从最难的层级接手，正是计划被放弃的方式。计划还有两个半边，教练两边都能给你看——问它「我该加强什么」看弱信号，问它「我哪里做得好」看那些已经值得守住的。",
      violations: "你的一周是按顺序走的：前一天完成后，后一天才会开启。如果某一天的日期过去了、那天却没做，代价是一枚徽章——若已没有徽章可扣，就会作为一条未清违规记在这里。这里没有任何对你的评判；它只是一个数字，以及回去的路。拿到一枚徽章就清掉一条。只要还有未清的违规，新拿到的徽章就会被用来清账，而不会挂上你的墙，所以回到收集徽章最快的路，就是把手上的日子做完。这个板块只在里面确实有内容时才出现。",
      heatmap_exceptions: "你回答过「那天不太寻常」的日子。它们和你彻底排除掉的日子不一样：被排除的一天会完全退出你的平均值，因为你说过那不是你的数据。而不寻常的一天确实发生过——它留在你的历史里、留在这一行上，也依然会拉动你的每周区间，只是比平常的一天更轻。如果这一行越来越长，本身就值得注意：一周里大多是例外的话，那就不算什么不寻常的一周了。",
      band_decision: "你的每周计划瞄准的是一个区间，而不是单个数字——就是圆环下方的那个区间。从一周的第二天起，某一天可能落在区间之外，而这意味着两件完全不同的事。「那天不太寻常」会让你的计划完全保持原样：这一天仍留在你的历史里、显示在你的面板上，也仍会影响你的区间，只是权重低于平常的一天，而不是归零——一个彻底消失的日子，会让一整周被悄悄修饰成一条直线。「算进去」意味着你现在就处在这个状态，本周剩下的部分会围绕新的区间重新生成；已经过去的日子会保留任务和勾选，因为那记录的是你真正做过的事。",
      edit_today: "这一项只在你当天已经记录过时出现。规则是每天只有一条主记录，所以第二次提交是取代第一次，而不是新增一天——勾选它就是你确认要这么做。勾选后表单还会用你今早填的答案回填，改一个数字不必把整份问卷重打一遍；更新完成后，你的每周计划和改进建议会依据新答案重新生成。",
      exclude_from_analysis: "假设性或测试性的记录请勾选这个——你依然会得到真实的预测，但不会有任何东西存进你的历史，所以它绝不会扭曲你的周分析。正常的真实记录就别勾——今天实际的星期几会自动打上，不用你选。",
      weekly_plan: "一份由规则根据你真实的薄弱环节生成的七日计划。做完就勾掉——进度是永久保存的，不只是这一次访问。",
      coach_chat: "输入一个问题，或者用 /fit 把你最近一次记录作为上下文加载进来。教练只知道你真实的数据告诉它的东西。",
      analytics_trend: "你的分数随时间的变化。三次或更多记录才让方向有意义；少于这个数，就只是图上的几个点而已。",
      analytics_weekday: "每个星期几的平均分。只记录过一次的星期几会被标为低置信度，而不是被当作一种模式呈现。",
      whatif_sweep: "选一个字段，这会让真实模型跑遍它的整个取值范围，让你确切看到你的分数在哪里转向。",
      profile_avatar: "你的图片只留在你自己的设备上和你的账号记录里。它在保存前会先在你的浏览器里缩放，而且永远不会到达模型那里。",
      profile_persona: "一个用平实语言表达的原型，由有据可循的规则从你真实的习惯中得出——你随时可以看到让它成立的那些数字。它显示在统计式机器学习人格旁边，那是另一回事。",
      profile_badges: "严格从真实记录的数值中获得。每个徽章都写明了它所要求的门槛，所以没有一个是神秘的。",
      profile_tone: "改变建议的措辞——更温和、更直接，或更冷静客观。它绝不会改变你收到哪些建议，也不会改变它们的优先级。",
      privacy_controls: "把这个应用存储的关于你的一切导出成一个文件，或者永久删除你的账号及其全部历史。删除无法撤销。",
    },
  };

  /* Ordered section tours per page - used by startTour() and by the
     "explain this page" affordance. */
  const PAGE_TOURS = {
    dashboard: ['dashboard', 'dash_score', 'dash_week_avg', 'dash_entries', 'dash_heatmap', 'dash_recs', 'dash_cohort'],
    checkin: ['checkin', 'demo_profiles', 'csv_import', 'wizard_derived'],
    result: ['result_ring', 'result_confidence', 'result_dimensions', 'result_shap', 'result_recs', 'result_roadmap', 'future_self'],
    weekly: ['weekly', 'weekly_plan'],
    coach: ['coach', 'coach_chat'],
    analytics: ['analytics', 'analytics_trend', 'analytics_weekday'],
    whatif: ['whatif', 'whatif_sweep'],
    model: ['model'],
    profile: ['profile', 'profile_avatar', 'profile_persona', 'profile_badges', 'profile_tone', 'privacy_controls'],
    about: ['about'],
    landing: ['landing'],
    // Runs itself once, right after sign-up (app.js::maybeRunFirstRunTour).
    // Everywhere else the guide waits to be asked; this is the one
    // moment it earns going first, because a brand new account is
    // looking at a screen with no explanation of what any of it is for.
    onboarding: ['onboarding_intro', 'schedule_regularity'],
    league: ['league', 'league_rules', 'league_connect', 'league_inbox', 'league_leaderboard'],
  };

  function copyFor(topicKey) {
    const lang = (window.DWI18n && window.DWI18n.get()) || 'en';
    const pool = TIPS[lang] || TIPS.en;
    return pool[topicKey] || TIPS.en[topicKey] || null;
  }

  /* ---------------------------------------------------------------
     Registry accessors. Metadata is looked up rather than assumed, so
     a topic registered later by a feature module behaves the same as
     one declared here.
     --------------------------------------------------------------- */

  function metaFor(topicKey) {
    const declared = META[topicKey] || {};
    return {
      face: declared.face || DEFAULT_META.face,
      priority: typeof declared.priority === 'number' ? declared.priority : DEFAULT_META.priority,
      cooldownDays: typeof declared.cooldownDays === 'number'
        ? declared.cooldownDays : DEFAULT_META.cooldownDays,
    };
  }

  function readInt(key) {
    const raw = localStorage.getItem(key);
    const n = raw == null ? 0 : parseInt(raw, 10);
    return Number.isFinite(n) ? n : 0;
  }

  function store(key, value) {
    try { localStorage.setItem(key, String(value)); } catch (e) {}
  }

  /** True while all auto-showing is paused because the user dismissed
   *  several topics in a row. Explicit clicks bypass this. */
  function inGlobalQuiet() {
    const until = readInt(QUIET_UNTIL_KEY);
    return until > Date.now();
  }

  /** True when this specific topic has been dismissed enough times to
   *  have earned silence, and its quiet window has not yet expired. */
  function isFatigued(topicKey) {
    const dismissals = readInt(DISMISS_PREFIX + topicKey);
    if (dismissals < DISMISSALS_BEFORE_QUIET) return false;
    const lastShown = readInt(SHOWN_AT_PREFIX + topicKey);
    return Date.now() - lastShown < TOPIC_QUIET_DAYS * DAY_MS;
  }

  /** Record that the user actively dismissed the guide while it was
   *  talking about `topicKey`. Called by the bubble's close control. */
  function noteDismissed(topicKey) {
    if (!topicKey) return;
    const next = readInt(DISMISS_PREFIX + topicKey) + 1;
    store(DISMISS_PREFIX + topicKey, next);

    // Count how many distinct topics are currently at or past the
    // per-topic limit. Enough of them means "not now, any of it".
    let quietTopics = 0;
    for (let i = 0; i < localStorage.length; i += 1) {
      const key = localStorage.key(i);
      if (key && key.indexOf(DISMISS_PREFIX) === 0
          && readInt(key) >= DISMISSALS_BEFORE_QUIET) {
        quietTopics += 1;
      }
    }
    if (quietTopics >= GLOBAL_DISMISS_LIMIT) {
      store(QUIET_UNTIL_KEY, Date.now() + GLOBAL_QUIET_HOURS * 3600000);
    }
  }

  /** Whether `explain(topicKey)` would actually speak right now, without
   *  causing it to. Lets a caller pick the best of several candidates
   *  instead of firing them all and letting the bubble thrash. */
  function canShow(topicKey, opts) {
    opts = opts || {};
    if (!topicKey || !copyFor(topicKey)) return false;
    if (opts.force) return true;
    if (inGlobalQuiet() || isFatigued(topicKey)) return false;

    const { cooldownDays } = metaFor(topicKey);
    const seen = localStorage.getItem(SEEN_PREFIX + topicKey) === '1';
    if (!seen) return true;
    if (cooldownDays <= 0) return false;  // once per browser, as before
    return Date.now() - readInt(SHOWN_AT_PREFIX + topicKey) >= cooldownDays * DAY_MS;
  }

  /** Of several candidate topics, speak the highest-priority one that is
   *  actually eligible. Returns the key spoken, or null. */
  function explainBest(topicKeys, opts) {
    const eligible = (topicKeys || []).filter((k) => canShow(k, opts));
    if (!eligible.length) return null;
    eligible.sort((a, b) => metaFor(b).priority - metaFor(a).priority);
    return explain(eligible[0], opts) ? eligible[0] : null;
  }

  /** Speak about one topic. Auto-shown topics respect the once-per-browser
   *  flag, the per-topic cooldown, and the fatigue rules; `force: true`
   *  (a click) always speaks, because silencing a deliberate request
   *  would be worse than being talkative. */
  function explain(topicKey, opts) {
    opts = opts || {};
    if (!topicKey || !window.DWMascot) return false;
    const text = copyFor(topicKey);
    if (!text) return false;
    if (!canShow(topicKey, opts)) return false;

    store(SEEN_PREFIX + topicKey, 1);
    store(SHOWN_AT_PREFIX + topicKey, Date.now());

    // The expression now follows the content instead of being 'neutral'
    // for all 55 topics.
    window.DWMascot.renderFace(metaFor(topicKey).face);
    window.DWMascot.say(text, {
      attention: !!opts.force,
      duration: opts.duration || 9500,
      // Lets the bubble's close control attribute a dismissal to the
      // right topic without the mascot layer knowing what a topic is.
      topic: topicKey,
    });
    return true;
  }

  /** Add topics at runtime, content and metadata together.
   *
   *  This exists so a feature can ship its guide copy alongside itself
   *  rather than as a later editing pass on this file - the same
   *  `register()` shape DWCoachKnowledge already uses, so there is one
   *  pattern for extending content, not two.
   *
   *  entries: { <topicKey>: { en, fa, ar, zh, face?, priority?, cooldownDays? } }
   */
  function register(entries) {
    Object.keys(entries || {}).forEach((key) => {
      const entry = entries[key] || {};
      ['en', 'fa', 'ar', 'zh'].forEach((lang) => {
        // TIPS currently declares only en and fa, so a missing block has
        // to be created rather than skipped. Guarding with `TIPS[lang] &&`
        // instead would silently discard Arabic and Chinese copy that a
        // caller did supply - the same quiet-drop failure that left the
        // rest of this codebase half-translated.
        if (!TIPS[lang]) TIPS[lang] = {};
        if (entry[lang] && TIPS[lang][key] === undefined) {
          TIPS[lang][key] = entry[lang];
        }
      });
      if (META[key] === undefined) {
        const meta = {};
        if (entry.face) meta.face = entry.face;
        if (typeof entry.priority === 'number') meta.priority = entry.priority;
        if (typeof entry.cooldownDays === 'number') meta.cooldownDays = entry.cooldownDays;
        META[key] = meta;
      }
    });
  }

  /* Controls that own their own click/keyboard behaviour. A [data-guide]
     container is often a whole card that *contains* these, and DOM events
     bubble - so without this guard the handlers below would swallow a
     space or an Enter typed into a text field inside the card. That is
     exactly what made the Coach chat box impossible to type in: every
     space was cancelled by preventDefault() and Enter never submitted. */
  const INTERACTIVE_SEL = 'input, textarea, select, button, a[href], label, [contenteditable=""], [contenteditable="true"]';

  function fromInteractive(e, host) {
    const t = e.target;
    if (!t || t === host || typeof t.closest !== 'function') return false;
    return !!t.closest(INTERACTIVE_SEL);
  }

  /** Make any element a help trigger for `topicKey`. Adds a keyboard
   *  path too, so the guide isn't mouse-only. */
  function attach(el, topicKey) {
    if (!el || !topicKey || el.__dwGuideBound) return;
    el.__dwGuideBound = true;
    el.classList.add('has-guide');

    // Only take focus/button semantics when the element is a leaf-ish
    // trigger. Making a whole card role="button" while it contains real
    // inputs is invalid ARIA and traps keyboard users.
    const holdsControls = !!el.querySelector(INTERACTIVE_SEL);
    if (!holdsControls) {
      if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '0');
      el.setAttribute('role', el.getAttribute('role') || 'button');
    }

    const speak = (e) => { e.stopPropagation(); explain(topicKey, { force: true }); };
    el.addEventListener('click', (e) => {
      if (fromInteractive(e, el)) return;
      speak(e);
    });
    el.addEventListener('keydown', (e) => {
      if (fromInteractive(e, el)) return;
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); speak(e); }
    });
  }

  /** Wire every element carrying data-guide="topic" in one pass. */
  function autoAttach(root) {
    (root || document).querySelectorAll('[data-guide]').forEach((el) => {
      attach(el, el.getAttribute('data-guide'));
    });
  }

  function topicsFor(pageKey) {
    return PAGE_TOURS[pageKey] || [];
  }

  /** Walk a page's sections in order, one bubble at a time. Runs once
   *  per page per browser unless forced. */
  function startTour(pageKey, opts) {
    opts = opts || {};
    const topics = topicsFor(pageKey);
    if (!topics.length) return false;

    const tourKey = TOUR_PREFIX + pageKey;
    if (!opts.force && localStorage.getItem(tourKey) === '1') return false;
    try { localStorage.setItem(tourKey, '1'); } catch (e) {}

    const step = opts.stepMs || 7000;
    topics.forEach((topic, i) => {
      setTimeout(() => explain(topic, { force: true, duration: step - 400 }), i * step);
    });
    return true;
  }

  /** Speak a line the registry cannot hold as a fixed topic.
   *
   *  The 63 badges (C-3) are the reason this exists: their explanations
   *  are composed at render time from the badge registry plus that
   *  user's own numbers, so there is no static topic string to look up.
   *  Everything else still goes through explain(); this is deliberately
   *  the only bypass, and it routes into exactly the same mascot path,
   *  which is what keeps voice coverage complete (B-3).
   */
  function speak(text, opts) {
    opts = opts || {};
    if (!text || !window.DWMascot) return false;
    window.DWMascot.renderFace(opts.face || 'neutral');
    window.DWMascot.say(text, {
      attention: opts.force !== false,
      duration: opts.duration || Math.min(6000 + text.length * 45, 20000),
      topic: opts.topic || null,
    });
    return true;
  }

  window.DWGuide = {
    explain, speak, attach, autoAttach, topicsFor, startTour, TIPS,
    // Registry surface (see B-5): metadata, eligibility and fatigue.
    register, metaFor, canShow, explainBest, noteDismissed,
    isFatigued, inGlobalQuiet,
  };
})();
