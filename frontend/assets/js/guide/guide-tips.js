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
    you:                { face: 'good',     priority: 72 },
    about_roadmap:      { face: 'thinking', priority: 68 },
    about_team:         { face: 'good',     priority: 60 },
    about_journal:      { face: 'good',     priority: 66 },
    about_personal:     { face: 'thinking', priority: 69 },
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
    welcome:               { face: 'good',     priority: 74 },
    welcome_checkin:       { face: 'neutral',  priority: 73 },
    welcome_band:          { face: 'thinking', priority: 73 },
    welcome_week:          { face: 'neutral',  priority: 73 },
    welcome_book:          { face: 'good',     priority: 72 },
    welcome_friends:       { face: 'good',     priority: 72 },
    welcome_recovery:      { face: 'neutral',  priority: 72 },
    welcome_end:           { face: 'good',     priority: 71 },
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
      plan_band: "The range this week is aimed at. Its centre is the average of the days you've already logged - not one prediction - and its WIDTH is fitted to you: a model reads how far your own days tend to fall from your own average, so a steady week gets a tighter range than a swingy one. A day that lands outside it is the one worth deciding about: count it, or mark it an exception.",
      plan_personal_signal: "A signal is flagged either because it's far from a healthy target, or because it's slipped from YOUR own normal - whichever is worse. That second half is why a drop from your usual 8 hours to 6.5 gets named even though 6.5 isn't alarming on its own, and the first half is why a habit that's always been rough never gets excused just for being your normal.",
      welcome: "Right - that's the setup done, so let me show you round before you start. Under a minute, and there's a Skip button in the corner if you'd rather just get going. Nothing here needs remembering; I'll be on every page if you want any of it again.",
      welcome_checkin: "This is the part you'll actually do: one check-in a day. Two real models read it - one puts you in a band, one gives you a score out of a hundred - and every result comes with the reasons it landed where it did. One a day is the rule, though you can edit today's if you got something wrong.",
      welcome_band: "On the dashboard you'll see a range for the week rather than one number, and it's yours - a model works out how wide it should be from how much YOUR days actually move. Steady weeks get a narrow one, weeks that swing get a wider one. When a day falls outside it, I'll ask whether something unusual happened. That's the whole point of the range: it decides when a question is worth asking.",
      welcome_week: "Your plan is seven days, and it opens one day at a time - the next one waits until tomorrow, even if you finish today's in five minutes. These are habits, not a checklist to clear. Finish a whole day's exercises and you'll see what I do about it.",
      welcome_book: "Under Your Book there's a diary - a page a day, your words, never fed to any model and it never touches your score. Underneath it is a reading of your own days: what a fit on YOUR data can say, and where it admits it can't say anything yet.",
      welcome_friends: "The Friends League shows nobody anything until you tick it, category by category, and you can untick it just as easily. Your own progress is the headline there; friends sit alongside it, not instead of it.",
      welcome_recovery: "One practical thing. You set a security question when you signed up - that's your way back in if you forget your password, because this app has no mail server, so an emailed reset code lands somewhere you can't read. Your answer is the way home. Don't lose it.",
      welcome_end: "That's everything. Tap me on any page and I'll explain what's on it, or ask the Coach - it only answers from your own numbers and says so when it doesn't know. Go and log your first day; the app has very little to say until it's met you.",
      onboarding_intro: "Three questions, one at a time, and none of them is locked in - you can change any of it later from your profile. They are not a survey: your answer to each one changes what the app leads with. The goal decides which recommendations get pushed to the top, the purpose decides how your screen time is read, and the schedule question decides whether the plan can lean on a routine at all. Skipping is fine too; you will just get the general version until you fill them in.",
      schedule_regularity: "This one matters more than it looks. If your days aren't alike - rotating shifts, irregular hours - the plan stops leading with advice like 'same bedtime every night', which you can't act on, and leads with the one anchor you can actually keep. Answer it honestly rather than aspirationally.",
      progress_consistency: "Two different things used to read the same here. Holding a strong score steady all week is not the same as climbing from a bad one, and you deserve to be told which of the two you did.",
      /* ---- Page-level overviews ---- */
      landing: "Welcome in. This reads the habits you actually report and gives you a score with the reasons attached - no horoscope, no vibe. Every number here traces back to something you typed, and where it cannot, it tells you.",
      dashboard: "This is home. The ring is your most recent real score, the strip under it is the week you've actually logged, and further down are the things that pushed that number around - named, not summarised.",
      checkin: "Everything the app knows about you starts here - nothing is pre-filled with a plausible average. Answer for today and submit, and you get a real prediction back: a class, a score out of a hundred, and the reasons it landed there.",
      weekly: "This week next to last week, and a seven-day plan built from where your own last check-in was weakest. It opens a day at a time - tomorrow's waits until tomorrow, because these are habits rather than a list to clear.",
      coach: "Ask it about your score, or about one thing like sleep or focus, or what to do first. It only answers from what you've actually logged, and when that isn't enough it says so instead of filling the gap.",
      analytics: "Your score over time, and which weekdays tend to go better or worse for you. All of it is computed from days you logged yourself, so it says more the longer you keep at it - and very little on day one.",
      whatif: "A place to try things. Change one habit and watch the real model move, without any of it touching what you've saved. Nothing you do here is recorded as a day.",
      model: "The accuracy numbers, as they actually are. Predicting for somebody it has never seen is genuinely hard, which is why you are not looking at 99% - and if you ever are, on any app, be suspicious.",
      profile: "Who you are here: your avatar, your persona, your badges, and the preferences you set at the start. All of it changes how the app talks to you; none of it changes what the model reads.",
      about: "How this thing works, what it was trained on, and where it stops being able to tell you anything. Worth two minutes before you trust a number it gives you.",
      you: "Two things here belong to you rather than to the project: the book, which is a page a day in your own words and never goes near a model, and the reading, which is what a fit on YOUR days alone can and cannot say. Both are allowed to be empty - a book you have not written and a pattern too short to read are honest answers.",
      about_roadmap: "Twelve stops from a logged day to something you can act on. Every number on the map is measured in this repository, and two of the stops are about what the project decided it could NOT claim - a seven-day regressor that failed its baseline and was left out, and training data that is synthetic. A map that only showed the good parts would not be worth reading.",
      about_team: "Four people, and what each of them actually did. Everything in a profile is what that person said about themselves - nothing here was written on their behalf to fill a gap.",
      about_journal: "One page per day, in your own words. It is saved to your account rather than this browser, it is never fed to any model, and it never touches your wellness score - that number is what the model read from your check-in, and this is what you thought of the day. Deleting your account takes the book with it.",
      about_personal: "Four readings, and each is allowed to say it has nothing. The time is MEASURED - only while a page is actually visible and focused, capped so a tab left open all weekend cannot claim two days. The cohort is the synthetic training data the models were fitted to, not a human population, and the panel says which of the two sources it read. The model is a ridge fit on YOUR days alone, and it leads with the leave-one-out R² rather than the in-sample one, because with ten days the second number flatters. Below eight days it refuses to fit anything at all.",
      settings_panel: "Theme, ambient sound, sound effects and reduced motion are all independent switches — turning one off never turns off another. Demo Mode below fills the whole app with a realistic sample history so you can explore without logging real days first.",
      league: "The number that matters here is your own past. Friends only show up if you have both said yes, and you pick exactly what each of them can see, one category at a time - and you can take it back just as easily.",
      league_progress: "This is the real comparison: your current score against your own score 7 days ago, plus a preview of where the same real model thinks you could realistically end up if you keep going. Friends below are just context, never the main event.",
      league_rules: "Nothing is shared automatically. A friend only sees what you tick, only after you both accept these rules, and you can revoke access at any moment from here.",
      league_connect: "Enter someone's invite code, tick exactly what you'd share if they accept, and send. They see nothing until they explicitly approve. Testing this yourself needs a second account (a private/incognito window works) - one account cannot connect to itself.",
      league_inbox: "This is your notification inbox for League requests - approve, decline, and choose what you share back, all in one place, never a phone push.",
      league_leaderboard: "Everyone who has shared a score is ranked highest first, you included - so your place here is whatever your score earns. Equal scores share a place. Friends only appear for the categories they personally agreed to share with you.",
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
      wizard_time: "Which day you're describing. Weekends really do behave differently from weekdays in this data, so getting it right changes what you get back - it is not bookkeeping.",
      wizard_screen: "Your screen minutes split by category. You don't enter a total — the app adds these up for you, so the parts can never contradict the whole.",
      wizard_device: "How fragmented your day was: notifications, pickups, app opens. In this dataset, how often you check tends to predict focus better than total hours do.",
      wizard_sleep: "Hours actually slept, and how rested you feel. Sleep is one of the strongest signals in the whole model.",
      wizard_mental: "Self-reported mood and stress. Answer honestly rather than optimistically — an inflated input gives you an inflated score, which helps nobody.",
      wizard_focus: "Focus, productivity, activity and caffeine. The last few pieces, then you get your result.",
      wizard_derived: "These are calculated from what you typed above — ratios, densities and indices the model expects. You never type these directly, so they can't disagree with your raw numbers.",
      demo_profiles: "In a hurry? Load a ready-made person and see a full real prediction straight away. It runs the same models on made-up inputs - the numbers are genuine, the person is not.",
      csv_import: "Already track this elsewhere? Download the template, fill in several days at once, and upload it. Every valid row runs a real prediction and lands in your history immediately.",

      /* ---- Result page sections ---- */
      result_ring: "Read this ring from the middle outwards. The big number is a RANGE, not one exact figure — the model has a known average error, so it reports where your score most likely sits. Just under it, the smaller ≈ number is the single best estimate. The thin inner circle is a 0–100 gauge: it fills clockwise from the top to your score, the white tick marks that estimate, and the soft band around it is the give-or-take. The four thick outer arcs are something different — they are the four dimensions behind the score, each with its own colour in the legend below.",
      result_confidence: "How sure the classifier is about the category it picked for you. Read it next to the score: a confident wrong answer and an unsure right one look identical until you check this.",
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
      profile_badges: "Earned strictly from what you actually logged. Each badge names the threshold it needed, so you can check it rather than take our word for it, and none of them can be bought or nudged.",
      profile_tone: "Changes how advice is worded — gentler, blunter, or clinical. It never changes which recommendations you get or their priority.",
      privacy_controls: "Export everything this app stores about you as a file, or delete your account and all its history permanently. Deletion cannot be undone.",
    },

    fa: {
      plan_week_lock: "برنامه‌ی این هفته عمداً برای کل هفته ثابت است. یک بار از الگوی خودت ساخته می‌شود و بعد سر جایش می‌ماند، تا یک چک‌این دوم نتواند بی‌صدا کارها را از زیر تیک‌هایی که زده‌ای عوض کند. بازسازی‌اش یک انتخاب آگاهانه است و تیک‌های این هفته را پاک می‌کند، چون کارهای پشت آن تیک‌ها دیگر وجود نخواهند داشت.",
      plan_band: "بازه‌ای که این هفته هدف گرفته است. مرکزش میانگین روزهایی است که تا حالا ثبت کرده‌ای — نه یک پیش‌بینی — و پهنایش برای خودِ تو اندازه شده: یک مدل یاد گرفته روزهای تو معمولاً چقدر از میانگین خودت فاصله می‌گیرند، پس هفته‌ی یکنواخت بازه‌ی تنگ‌تری می‌گیرد تا هفته‌ی پرنوسان. روزی که بیرون این بازه بیفتد همان روزی است که باید درباره‌اش تصمیم بگیری: به حساب بیاید، یا استثنا علامت بخورد.",
      plan_personal_signal: "یک سیگنال یا به این دلیل علامت می‌خورد که از هدف سلامت دور است، یا به این دلیل که از حالت عادیِ خودِ تو افت کرده — هرکدام که بدتر باشد. نیمه‌ی دوم دلیل این است که افت از ۸ ساعت همیشگی‌ات به ۶.۵ نام برده می‌شود، با اینکه ۶.۵ به‌تنهایی نگران‌کننده نیست؛ و نیمه‌ی اول دلیل این است که عادتی که همیشه بد بوده، فقط به‌خاطر «عادی بودن برای تو» هیچ‌وقت بخشیده نمی‌شود.",
      welcome: 'خب — تنظیمات تمام شد. بگذار قبل از شروع کوتاه دور بگردانمت. کمتر از یک دقیقه است، و اگر ترجیح می‌دهی همین حالا شروع کنی، دکمه‌ی رد کردن گوشه‌ی صفحه است. لازم نیست چیزی را حفظ کنی؛ من توی همه‌ی صفحه‌ها هستم و هر وقت خواستی دوباره می‌گویم.',
      welcome_checkin: 'این همان کاری است که واقعاً انجام می‌دهی: روزی یک ثبت. دو مدل واقعی می‌خوانندش — یکی تو را در یک دسته می‌گذارد، یکی نمره‌ای از صد می‌دهد — و هر نتیجه با دلیلِ همان‌جا بودنش می‌آید. قانون روزی یکی است، هرچند اگر امروز چیزی را اشتباه زدی می‌توانی ویرایشش کنی.',
      welcome_band: 'توی داشبورد به‌جای یک عدد، یک بازه برای هفته می‌بینی — و این بازه مال خودت است: یک مدل از روی اینکه روزهای تو واقعاً چقدر بالا و پایین می‌شوند پهنایش را حساب می‌کند. هفته‌های آرام بازه‌ی باریک می‌گیرند، هفته‌های پرنوسان بازه‌ی پهن‌تر. وقتی روزی بیرون از آن بیفتد، از تو می‌پرسم اتفاق غیرعادی‌ای افتاده یا نه. کل کارِ این بازه همین است: تصمیم می‌گیرد کِی پرسیدن ارزش دارد.',
      welcome_week: 'برنامه‌ات هفت‌روزه است و روزبه‌روز باز می‌شود — روز بعدی تا فردا صبر می‌کند، حتی اگر کارِ امروز را در پنج دقیقه تمام کنی. این‌ها عادت‌اند، نه فهرستی که تیک بخورد و رد شود. تمرین‌های یک روز را کامل کن تا ببینی من چه می‌کنم.',
      welcome_book: 'زیر «دفتر تو» یک دفترچه هست — روزی یک صفحه، به قلم خودت، که هرگز خوراک هیچ مدلی نمی‌شود و هیچ اثری روی نمره‌ات ندارد. پایین‌ترش، خوانشی از روزهای خودت است: اینکه یک برازش روی داده‌ی تو چه می‌تواند بگوید، و کجا صادقانه می‌گوید هنوز چیزی نمی‌دانم.',
      welcome_friends: 'لیگ دوستان تا وقتی خودت تیک نزنی، دسته‌به‌دسته، هیچ‌چیز از تو به کسی نشان نمی‌دهد — و به همان سادگی می‌توانی تیک را برداری. آنجا پیشرفت خودت تیتر است؛ دوستان کنارش نشان داده می‌شوند، نه به‌جایش.',
      welcome_recovery: 'یک نکته‌ی عملی. هنگام ثبت‌نام یک پرسش امنیتی گذاشتی — راه برگشتت اگر رمزت را فراموش کنی همان است، چون این اپ سرور ایمیل ندارد و کد بازیابی جایی می‌رود که تو نمی‌توانی بخوانی. پاسخ تو راه خانه است. گمش نکن.',
      welcome_end: 'همین. توی هر صفحه‌ای رویم بزن تا هرچه آنجاست را توضیح بدهم، یا از مربی بپرس — او فقط از روی عددهای خودت جواب می‌دهد و هر وقت نداند، می‌گوید نمی‌دانم. حالا برو اولین روزت را ثبت کن؛ این اپ تا تو را نشناسد حرف چندانی برای گفتن ندارد.',
      onboarding_intro: "سه سؤال، یکی‌یکی، و هیچ‌کدام قفل نمی‌شود — بعداً از پروفایلت می‌توانی همه را عوض کنی. این‌ها نظرسنجی نیستند: جواب هرکدام تغییر می‌دهد که برنامه با چه چیزی شروع کند. هدف تعیین می‌کند کدام توصیه‌ها بالا بیایند، کاربرد تعیین می‌کند زمان صفحه‌ات چطور خوانده شود، و سؤال برنامه‌ی روزانه تعیین می‌کند که اصلاً می‌شود روی یک روتین حساب کرد یا نه. رد کردنش هم اشکالی ندارد؛ فقط تا وقتی پرشان نکنی نسخه‌ی عمومی را می‌گیری.",
      schedule_regularity: "این یکی از چیزی که به نظر می‌رسد مهم‌تر است. اگر روزهایت شبیه هم نیستند — شیفت گردشی، ساعت‌های نامنظم — برنامه دیگر با توصیه‌هایی مثل «هر شب ساعت خواب ثابت» شروع نمی‌کند که نمی‌توانی اجرایش کنی، و با همان یک لنگرگاهی شروع می‌کند که واقعاً می‌توانی نگهش داری. صادقانه جواب بده، نه آرزومندانه.",
      progress_consistency: "دو چیز متفاوت اینجا یکسان خوانده می‌شد. نگه‌داشتن یک امتیاز خوب در تمام هفته با بالا آمدن از یک امتیاز بد یکی نیست، و حقت است بدانی کدامش را انجام داده‌ای.",
      landing: "خوش آمدی. این اپ عادت‌هایی را که واقعاً گزارش می‌کنی می‌خواند و نمره‌ای با دلیل‌هایش به تو می‌دهد — نه طالع‌بینی، نه حس‌وحال. هر عددی اینجا به چیزی برمی‌گردد که خودت نوشته‌ای، و هرجا نتواند، همین را می‌گوید.",
      dashboard: "اینجا خانه است. حلقه آخرین امتیاز واقعی توست، نوار زیرش هفته‌ای است که واقعاً ثبت کرده‌ای، و پایین‌ترش همان چیزهایی‌اند که آن عدد را بالا و پایین برده‌اند — با اسم، نه خلاصه‌شده.",
      checkin: "هرچه این اپ درباره‌ی تو می‌داند از همین‌جا شروع می‌شود — هیچ خانه‌ای با یک میانگینِ قابل‌قبول از پیش پر نشده. برای امروز جواب بده و بفرست تا یک پیش‌بینی واقعی بگیری: یک دسته، نمره‌ای از صد، و دلیل همان‌جا بودنش.",
      weekly: "این هفته کنار هفته‌ی پیش، و یک برنامه‌ی هفت‌روزه که از ضعیف‌ترین جای آخرین ثبت خودت ساخته شده. روزبه‌روز باز می‌شود — روز فردا تا فردا صبر می‌کند، چون این‌ها عادت‌اند نه فهرستی که تیک بخورد و رد شود.",
      coach: "از او درباره‌ی امتیازت بپرس، یا درباره‌ی یک چیز مشخص مثل خواب یا تمرکز، یا اینکه از کجا شروع کنی. فقط از روی چیزی که واقعاً ثبت کرده‌ای جواب می‌دهد، و وقتی کافی نباشد همین را می‌گوید به‌جای اینکه جای خالی را پر کند.",
      analytics: "امتیازت در طول زمان، و اینکه کدام روزهای هفته برای تو معمولاً بهتر یا بدتر می‌گذرند. همه‌اش از روزهایی حساب شده که خودت ثبت کرده‌ای، پس هرچه بیشتر ادامه بدهی بیشتر حرف دارد — و روز اول تقریباً هیچ.",
      whatif: "جایی برای امتحان کردن. یک عادت را عوض کن و ببین مدل واقعی چطور جابه‌جا می‌شود، بی‌آنکه هیچ‌کدامش به چیزی که ذخیره کرده‌ای دست بزند. هیچ کاری که اینجا می‌کنی به‌عنوان یک روز ثبت نمی‌شود.",
      model: "عددهای دقت، همان‌طور که واقعاً هستند. پیش‌بینی برای کسی که مدل هرگز ندیده‌ است واقعاً سخت است، برای همین اینجا ۹۹٪ نمی‌بینی — و اگر جایی، در هر اپی، دیدی، شک کن.",
      profile: "اینکه اینجا کی هستی: آواتارت، پرسونایت، نشان‌هایت، و ترجیحاتی که اول کار گذاشتی. همه‌اش عوض می‌کند که اپ چطور با تو حرف بزند؛ هیچ‌کدامش عوض نمی‌کند که مدل چه می‌خواند.",
      about: "اینکه این چیز چطور کار می‌کند، روی چه چیزی آموزش دیده، و از کجا به بعد دیگر نمی‌تواند چیزی به تو بگوید. قبل از اینکه به عددی که می‌دهد اعتماد کنی، دو دقیقه‌اش را می‌ارزد.",
      you: 'دو چیز اینجا مال توست نه مال پروژه: کتاب، که روزی یک صفحه به قلم خودت است و هرگز نزدیک هیچ مدلی نمی‌شود، و خوانش، که می‌گوید یک برازش فقط روی روزهای خودت چه می‌تواند بگوید و چه نمی‌تواند. هر دو اجازه دارند خالی باشند — کتابی که ننوشته‌ای و الگویی که برای خوانده‌شدن کوتاه است، هر دو پاسخ‌های صادقانه‌اند.',
      about_roadmap: 'دوازده ایستگاه، از یک روزِ ثبت‌شده تا چیزی که بشود رویش عمل کرد. هر عددی روی این نقشه در همین مخزن اندازه‌گیری شده، و دو ایستگاهش درباره‌ی چیزهایی است که پروژه تصمیم گرفت ادعایشان نکند — یک مدل رگرسیون هفت‌روزه که در آزمون پایه رد شد و کنار گذاشته شد، و داده‌ی آموزشی‌ای که مصنوعی است. نقشه‌ای که فقط بخش‌های خوب را نشان بدهد ارزش خواندن ندارد.',
      about_team: "چهار نفر، و اینکه هرکدام واقعاً چه کردند. هرچه در یک پروفایل هست همان است که خودِ آن شخص درباره‌ی خودش گفته — هیچ‌چیز اینجا به‌جای کسی نوشته نشده تا جای خالی پر شود.",
      about_journal: 'روزی یک صفحه، به قلم خودت. روی حساب خودت ذخیره می‌شود نه روی این مرورگر، هرگز خوراک هیچ مدلی نمی‌شود، و هیچ اثری روی امتیاز سلامتت ندارد — آن عدد چیزی است که مدل از ثبت روزانه‌ات خوانده، و این چیزی است که خودت درباره‌ی آن روز فکر کرده‌ای. پاک‌کردن حساب، کتاب را هم با خودش می‌برد.',
      about_personal: 'چهار خوانش، و هرکدام اجازه دارد بگوید «چیزی ندارم». زمان اندازه‌گیری می‌شود — فقط وقتی صفحه‌ای واقعاً دیده می‌شود و فوکوس دارد، با سقفی که نمی‌گذارد تبِ بازمانده در تمام آخر هفته دو روز را ادعا کند. جمعیت مرجع همان داده‌ی آموزشیِ مصنوعی است که مدل‌ها رویش برازش شده‌اند، نه یک جمعیت انسانی، و خودِ بخش می‌گوید از کدام منبع خوانده. مدل، یک برازش ریج فقط روی روزهای خودت است و با R² «حذف یکی» شروع می‌کند نه R² روی همان داده، چون با ده روز عدد دوم چاپلوسی می‌کند. زیر هشت روز اصلاً چیزی برازش نمی‌کند.',
      settings_panel: 'تم، صدای محیطی، جلوه‌های صوتی و کاهش حرکت همه کلیدهای مستقل‌اند — خاموش‌کردن یکی بقیه را خاموش نمی‌کند. حالت دمو پایین‌تر کل اپ را با یک تاریخچه‌ی نمونه‌ی واقع‌گرایانه پر می‌کند تا بدون ثبت روزهای واقعی بگردی.',
      league: "عددی که اینجا مهم است، گذشته‌ی خودت است. دوستان فقط وقتی پیدایشان می‌شود که هر دو بله گفته باشید، و تو دقیقاً انتخاب می‌کنی هرکدام چه ببیند، دسته‌به‌دسته — و به همان سادگی می‌توانی پسش بگیری.",
      league_progress: 'مقایسه‌ی واقعی همین است: امتیاز فعلی‌ات در برابر امتیاز خودت از ۷ روز پیش، به‌علاوه یک پیش‌نمایش از جایی که همان مدل واقعی فکر می‌کند اگر ادامه بدهی واقع‌بینانه می‌توانی برسی. دوستان پایین صفحه فقط زمینه‌اند، هرگز محور اصلی نیستند.',
      league_rules: 'هیچ‌چیز خودکار به اشتراک گذاشته نمی‌شود. یک دوست فقط چیزی را می‌بیند که تیک زده‌ای، فقط بعد از اینکه هر دو این قوانین را پذیرفتید، و می‌توانی هر لحظه از همین‌جا دسترسی را لغو کنی.',
      league_connect: 'کد دعوت کسی را وارد کن، دقیقاً چیزی که اگر قبول کرد می‌خواهی به اشتراک بگذاری را تیک بزن، و بفرست. او تا وقتی صریحاً تایید نکند چیزی نمی‌بیند. برای تست خودت به یک اکانت دوم نیاز داری (یک پنجره‌ی ناشناس هم کافی است) — یک اکانت نمی‌تواند به خودش وصل شود.',
      league_inbox: 'این صندوق اعلان‌های تو برای درخواست‌های لیگ است — تایید، رد، و انتخاب اینکه چه چیزی در ازایش به اشتراک بگذاری، همه یک‌جا، هرگز نه به‌صورت نوتیف گوشی.',
      league_leaderboard: 'هر کسی که امتیازش را به اشتراک گذاشته از بالا به پایین مرتب می‌شود و تو هم یکی از آن‌هایی - پس جایگاهت همان است که امتیازت به دست آورده. امتیاز برابر یعنی رتبهٔ مشترک. دوستان فقط در دسته‌هایی دیده می‌شوند که خودشان قبول کرده‌اند با تو به اشتراک بگذارند.',
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
      wizard_time: "اینکه داری کدام روز را توصیف می‌کنی. آخر هفته‌ها در این داده واقعاً متفاوت از روزهای کاری رفتار می‌کنند، پس درست گذاشتنش عوض می‌کند چه چیزی می‌گیری — دفترداری نیست.",
      wizard_screen: 'دقایق صفحه‌نمایشت به تفکیک دسته. مجموع را وارد نمی‌کنی — اپ خودش جمع می‌زند، پس اجزا هرگز نمی‌توانند با کل در تناقض باشند.',
      wizard_device: 'اینکه روزت چقدر تکه‌تکه بوده: اعلان‌ها، برداشتن گوشی، باز کردن اپ. در این داده، تعداد دفعات چک‌کردن اغلب بهتر از مجموع ساعت‌ها تمرکز را پیش‌بینی می‌کند.',
      wizard_sleep: 'ساعت‌هایی که واقعاً خوابیده‌ای و اینکه چقدر سرحالی. خواب یکی از قوی‌ترین سیگنال‌های کل مدل است.',
      wizard_mental: 'حال‌وهوا و استرس خوداظهاری. صادقانه پاسخ بده نه خوش‌بینانه — ورودی متورم امتیاز متورم می‌دهد که به درد هیچ‌کس نمی‌خورد.',
      wizard_focus: 'تمرکز، بهره‌وری، فعالیت و کافئین. چند مورد آخر، بعد نتیجه‌ات را می‌گیری.',
      wizard_derived: 'این‌ها از چیزی که بالا نوشتی محاسبه شده‌اند — نسبت‌ها، تراکم‌ها و شاخص‌هایی که مدل انتظار دارد. اینها را مستقیم وارد نمی‌کنی، پس نمی‌توانند با اعداد خامت مخالف باشند.',
      demo_profiles: "عجله داری؟ یک آدم آماده را بارگذاری کن و همان لحظه یک پیش‌بینی کامل و واقعی ببین. همان مدل‌ها را روی ورودی‌های ساختگی اجرا می‌کند — عددها واقعی‌اند، آدمش نه.",
      csv_import: 'از قبل جای دیگری ثبت می‌کنی؟ قالب را دانلود کن، چند روز را یکجا پر کن و آپلود کن. هر ردیف معتبر یک پیش‌بینی واقعی اجرا می‌کند و بلافاصله در تاریخچه‌ات می‌نشیند.',

      result_ring: 'این حلقه را از وسط به بیرون بخوان. عدد بزرگ یک بازه است، نه یک رقم دقیق — چون مدل خطای میانگین مشخصی دارد، پس می‌گوید امتیازت به احتمال زیاد کجاست. درست زیرش، عدد کوچک‌تر با علامت ≈ همان بهترین برآورد تک‌عددی است. دایره‌ی نازک داخلی یک مقیاس ۰ تا ۱۰۰ است: از بالا در جهت عقربه‌های ساعت تا امتیازت پر می‌شود، خط سفید همان برآورد را نشان می‌دهد، و باند نرم اطرافش میزان عدم‌قطعیت را نشان می‌دهد. چهار کمان ضخیم بیرونی چیز دیگری‌اند — چهار بعد پشت این امتیاز‌اند، هرکدام با رنگ خودشان در راهنمای پایین.',
      result_confidence: "اینکه دسته‌بند چقدر از دسته‌ای که برایت انتخاب کرده مطمئن است. کنار نمره بخوانش: یک جواب غلطِ مطمئن و یک جواب درستِ نامطمئن تا وقتی این را نبینی عین هم‌اند.",
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
      profile_badges: "دقیقاً از روی چیزی که واقعاً ثبت کرده‌ای به دست می‌آیند. هر نشان آستانه‌ای را که لازم داشته اسم می‌برد، تا بتوانی خودت بررسی‌اش کنی و مجبور نباشی حرف ما را قبول کنی — و هیچ‌کدام خریدنی یا هل‌دادنی نیستند.",
      profile_tone: 'نحوه‌ی بیان توصیه‌ها را تغییر می‌دهد — ملایم‌تر، صریح‌تر یا بالینی. هرگز تغییر نمی‌دهد که چه توصیه‌هایی می‌گیری یا اولویتشان چیست.',
      privacy_controls: 'هرچه این اپ درباره‌ی تو ذخیره کرده را به‌صورت فایل خروجی بگیر، یا حساب و کل تاریخچه‌اش را برای همیشه حذف کن. حذف برگشت‌پذیر نیست.',
    },
    ar: {
      plan_week_lock: "خطة هذا الأسبوع ثابتة طوال الأسبوع عن قصد. تُبنى مرة واحدة من نمطك أنت ثم تبقى كما هي، كي لا يستطيع تسجيل ثانٍ أن يبدّل المهام بهدوء من تحت المربعات التي أشّرتها. وإعادة بنائها اختيار مقصود، وهي تمسح تأشيرات هذا الأسبوع لأن المهام التي تخصها لن تكون موجودة بعدها.",
      plan_band: "النطاق الذي يستهدفه هذا الأسبوع. مركزه متوسط الأيام التي سجّلتها بالفعل — لا تنبؤ واحد — وعرضه مُفصَّل عليك: نموذج يقرأ كم تبتعد أيامك عادةً عن متوسطك أنت، فيحصل الأسبوع الثابت على نطاق أضيق من الأسبوع المتقلّب. واليوم الذي يقع خارجه هو اليوم الجدير بقرار: أن يُحتسب، أو أن يُوسم كاستثناء.",
      plan_personal_signal: "تُوسم الإشارة إما لأنها بعيدة عن هدف صحي، أو لأنها تراجعت عن معتادك أنت — أيهما أسوأ. النصف الثاني هو سبب تسمية الهبوط من ثماني ساعات معتادة إلى ست ونصف رغم أن ست ونصف ليست مقلقة بذاتها، والنصف الأول هو سبب ألا تُعفى عادة كانت سيئة دوماً لمجرد أنها معتادك.",
      welcome: "حسناً — انتهى الإعداد، فدعني أطوف بك سريعاً قبل أن تبدأ. أقل من دقيقة، وفي الزاوية زرّ تخطٍّ إن كنت تفضّل الانطلاق فوراً. لا شيء هنا يحتاج إلى حفظ؛ سأكون في كل صفحة إن أردت سماعه ثانية.",
      welcome_checkin: "هذا ما ستفعله فعلاً: تسجيل واحد كل يوم. يقرؤه نموذجان حقيقيان — أحدهما يضعك في فئة، والآخر يعطيك درجة من مئة — وكل نتيجة تأتي بأسباب وقوعها حيث وقعت. القاعدة واحد يومياً، وإن أخطأت في شيء اليوم فبإمكانك تعديله.",
      welcome_band: "في لوحة المعلومات سترى مدى للأسبوع بدل رقم واحد، وهو مداك أنت: يحسب نموذج عرضه من مقدار تذبذب أيامك أنت. الأسابيع الهادئة تأخذ مدى ضيقاً، والمتقلبة تأخذ أوسع. وحين يقع يوم خارجه، أسألك إن كان قد حدث شيء غير معتاد. هذا كل غرض المدى: أن يقرّر متى يستحق السؤال أن يُطرح.",
      welcome_week: "خطتك سبعة أيام، وتُفتح يوماً بيوم — اليوم التالي ينتظر الغد، حتى لو أنهيت اليوم في خمس دقائق. هذه عادات لا قائمة تُشطب. أتمم تمارين يوم كامل وسترى ماذا أفعل حينها.",
      welcome_book: "تحت «دفترك» هناك يوميات — صفحة كل يوم بكلماتك، لا تُغذّى لأي نموذج ولا تمسّ درجتك. وتحتها قراءة لأيامك أنت: ما تستطيع ملاءمة على بياناتك قوله، وأين تعترف بأنها لا تستطيع قول شيء بعد.",
      welcome_friends: "دوري الأصدقاء لا يُظهر عنك شيئاً لأحد حتى تحدّده أنت، فئةً فئة، ويمكنك إلغاؤه بالسهولة نفسها. تقدّمك أنت هو العنوان هناك؛ والأصدقاء إلى جانبه لا بدلاً منه.",
      welcome_recovery: "أمر عملي واحد. وضعت سؤالاً أمنياً عند التسجيل — هذا طريق عودتك إن نسيت كلمة المرور، فهذا التطبيق بلا خادم بريد، ورمز الاستعادة يصل إلى مكان لا تستطيع قراءته. جوابك هو طريق البيت. لا تُضِعه.",
      welcome_end: "هذا كل شيء. انقر عليّ في أي صفحة لأشرح ما فيها، أو اسأل المدرّب — فهو لا يجيب إلا من أرقامك أنت، ويقول إنه لا يعرف حين لا يعرف. اذهب وسجّل يومك الأول؛ لا يملك هذا التطبيق الكثير ليقوله قبل أن يعرفك.",
      onboarding_intro: "ثلاثة أسئلة، واحداً تلو الآخر، ولا شيء منها نهائي — تستطيع تغييرها لاحقاً من ملفك. وهي ليست استبياناً: إجابتك عن كل سؤال تغيّر ما يبدأ به التطبيق. الهدف يحدّد أي التوصيات تتصدّر، والغرض يحدّد كيف يُقرأ وقت شاشتك، وسؤال الجدول يحدّد هل يمكن للخطة أن تتكئ على روتين أصلاً. وتخطّيها لا بأس به؛ ستحصل فقط على النسخة العامة حتى تملأها.",
      schedule_regularity: "هذا السؤال أهم مما يبدو. إن لم تكن أيامك متشابهة — ورديات متناوبة، ساعات غير منتظمة — فلن تبدأ الخطة بنصائح مثل «موعد نوم ثابت كل ليلة» التي لا تستطيع تنفيذها، بل بالمرساة الوحيدة التي تستطيع الحفاظ عليها فعلاً. أجب بصدق لا بأمنية.",
      progress_consistency: "كان أمران مختلفان يُقرآن هنا على نحو واحد. الحفاظ على درجة قوية طوال الأسبوع ليس كالصعود من درجة سيئة، ومن حقك أن يُقال لك أيّهما فعلت.",
      landing: "أهلاً بك. يقرأ هذا عاداتك كما تصرّح بها فعلاً، ويعطيك درجة مع أسبابها — لا طالعاً ولا انطباعاً. كل رقم هنا يعود إلى شيء كتبته أنت، وحيث لا يستطيع، يقول ذلك.",
      dashboard: "هنا البيت. الحلقة هي أحدث درجة حقيقية لك، والشريط تحتها هو الأسبوع الذي سجّلته فعلاً، وأسفل منه الأشياء التي حرّكت ذلك الرقم — مسمّاة، لا ملخّصة.",
      checkin: "كل ما يعرفه التطبيق عنك يبدأ من هنا — لا شيء مملوء مسبقاً بمتوسط معقول. أجب عن اليوم وأرسل، فتعود إليك تنبؤ حقيقي: فئة، ودرجة من مئة، وأسباب وقوعها هناك.",
      weekly: "هذا الأسبوع بجانب الأسبوع الماضي، وخطة سبعة أيام مبنية على أضعف ما في آخر تسجيل لك. تُفتح يوماً بيوم — ويوم الغد ينتظر الغد، لأن هذه عادات لا قائمة تُشطب.",
      coach: "اسأله عن درجتك، أو عن شيء بعينه كالنوم أو التركيز، أو عمّا تبدأ به. لا يجيب إلا مما سجّلته فعلاً، وحين لا يكفي ذلك يقولها بدل أن يملأ الفراغ.",
      analytics: "درجتك عبر الزمن، وأي أيام الأسبوع تميل لأن تكون أفضل أو أسوأ لك. كل ذلك محسوب من أيام سجّلتها بنفسك، فكلما واظبت قال أكثر — وفي اليوم الأول لا يقول شيئاً يُذكر.",
      whatif: "مكان للتجريب. غيّر عادة واحدة وراقب النموذج الحقيقي وهو يتحرك، دون أن يمسّ شيء من ذلك ما حفظته. لا شيء تفعله هنا يُسجَّل كيوم.",
      model: "أرقام الدقة كما هي فعلاً. التنبؤ لشخص لم يره النموذج قط صعب حقاً، ولهذا لا ترى هنا ٩٩٪ — وإن رأيتها يوماً في أي تطبيق، فارتَبْ.",
      profile: "من أنت هنا: صورتك، وشخصيتك، وأوسمتك، والتفضيلات التي ضبطتها في البداية. كل ذلك يغيّر كيف يخاطبك التطبيق؛ ولا شيء منه يغيّر ما يقرؤه النموذج.",
      about: "كيف يعمل هذا الشيء، وعلى ماذا دُرِّب، ومن أين يتوقف عن القدرة على إخبارك بشيء. يستحق دقيقتين قبل أن تثق برقم يعطيك إياه.",
      you: "شيئان هنا لك أنت لا للمشروع: الدفتر، صفحة كل يوم بكلماتك ولا يقترب من أي نموذج، والقراءة، وهي ما تستطيع ملاءمة على أيامك وحدها أن تقوله وما لا تستطيع. ويحق لكليهما أن يكونا فارغين - دفتر لم تكتبه ونمط أقصر من أن يُقرأ، كلاهما جواب صادق.",
      about_roadmap: "اثنتا عشرة محطة، من يوم مُسجَّل إلى شيء يمكنك التصرف بناءً عليه. كل رقم على الخريطة مُقاس داخل هذا المستودع، ومحطتان منها عمّا قرّر المشروع أنه لا يستطيع ادّعاءه — نموذج انحدار سباعي فشل في خط الأساس فتُرك، وبيانات تدريب اصطناعية. خريطة تُظهر الجوانب الجيدة وحدها لا تستحق القراءة.",
      about_team: "أربعة أشخاص، وما فعله كلٌّ منهم فعلاً. كل ما في الملف هو ما قاله ذلك الشخص عن نفسه — ولم يُكتب هنا شيء نيابةً عن أحد لسدّ فراغ.",
      about_journal: "صفحة لكل يوم، بكلماتك أنت. تُحفظ في حسابك لا في هذا المتصفح، ولا تُغذّى لأي نموذج، ولا تمس درجة عافيتك — تلك الدرجة هي ما قرأه النموذج من تسجيلك اليومي، وهذه هي رؤيتك أنت لليوم. وحذف الحساب يأخذ الكتاب معه.",
      about_personal: "أربع قراءات، ولكلٍّ أن تقول إنها لا تملك شيئًا. الوقت مُقاس — فقط أثناء ظهور صفحة فعليًا وتركيزها، وبسقف يمنع تبويبًا متروكًا طوال العطلة من ادّعاء يومين. والمجموعة المرجعية هي بيانات التدريب الاصطناعية التي لوئمت عليها النماذج، لا مجتمعًا بشريًا، واللوحة تقول من أي المصدرين قرأت. والنموذج ملاءمة ريدج على أيامك أنت وحدها، ويبدأ بـ R² بحذف واحد لا بـ R² داخل العينة، لأن الثاني يجامل عند عشرة أيام. ودون ثمانية أيام يرفض الملاءمة أصلًا.",
      settings_panel: "المظهر، والصوت المحيط، والمؤثرات الصوتية، وتقليل الحركة كلها مفاتيح مستقلة — إطفاء أحدها لا يطفئ آخر أبداً. ووضع العرض بالأسفل يملأ التطبيق كله بسجل نموذجي واقعي لتستكشفه دون تسجيل أيام حقيقية أولاً.",
      league: "الرقم المهم هنا هو ماضيك أنت. لا يظهر الأصدقاء إلا إن وافق كلاكما، وأنت تختار بالضبط ما يراه كل منهم، فئةً فئة — ويمكنك سحبه بالسهولة نفسها.",
      league_progress: "هذه هي المقارنة الحقيقية: درجتك الآن مقابل درجتك أنت قبل سبعة أيام، مع لمحة عن المكان الذي يرى النموذج نفسه أنك قد تصل إليه واقعياً إن واصلت. الأصدقاء بالأسفل سياق فقط، لا الحدث الرئيسي.",
      league_rules: "لا شيء يُشارَك تلقائياً. لا يرى الصديق إلا ما تؤشّر عليه، وبعد أن يقبل الطرفان هذه القواعد، ويمكنك سحب الوصول في أي لحظة من هنا.",
      league_connect: "أدخل رمز دعوة شخص ما، وأشّر بالضبط على ما ستشاركه إن قَبِل، ثم أرسل. لا يرى شيئاً حتى يوافق صراحةً. لاختبار هذا بنفسك تحتاج حساباً ثانياً (نافذة تصفح خاص تكفي) — لا يمكن لحساب أن يتصل بنفسه.",
      league_inbox: "هذا صندوق إشعاراتك لطلبات الدوري — القبول والرفض واختيار ما تشاركه بالمقابل، كله في مكان واحد، ولا إشعار هاتف أبداً.",
      league_leaderboard: "كل من شارك درجته يُرتَّب من الأعلى إلى الأدنى، وأنت منهم - فموقعك هنا هو ما تستحقه درجتك. الدرجات المتساوية تتقاسم المرتبة نفسها. ولا يظهر الأصدقاء إلا في الفئات التي وافقوا شخصياً على مشاركتها معك.",
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
      wizard_time: "أي يوم تصفه. عطلات نهاية الأسبوع تتصرف فعلاً على نحو مختلف عن أيام العمل في هذه البيانات، فضبطها يغيّر ما يعود إليك — وليست مجرد إجراء شكلي.",
      wizard_screen: "دقائق شاشتك موزّعة حسب الفئة. أنت لا تُدخل مجموعاً — التطبيق يجمعها لك، فلا يمكن للأجزاء أن تناقض الكل.",
      wizard_device: "كم كان يومك مجزّأً: الإشعارات، ومرات التقاط الهاتف، وفتح التطبيقات. في هذه البيانات، عدد مرات تفقّدك يتنبأ بالتركيز أفضل من مجموع الساعات.",
      wizard_sleep: "الساعات التي نمتها فعلاً، ومدى شعورك بالراحة. النوم من أقوى الإشارات في النموذج كله.",
      wizard_mental: "المزاج والتوتر كما تصفهما أنت. أجب بصدق لا بتفاؤل — فالمُدخل المنفوخ يعطيك درجة منفوخة، وهذا لا ينفع أحداً.",
      wizard_focus: "التركيز، والإنتاجية، والنشاط، والكافيين. آخر القطع، ثم تحصل على نتيجتك.",
      wizard_derived: "هذه محسوبة مما كتبته أعلاه — نسب وكثافات ومؤشرات يتوقعها النموذج. أنت لا تكتبها مباشرةً أبداً، فلا يمكن أن تتعارض مع أرقامك الخام.",
      demo_profiles: "في عجلة؟ حمِّل شخصاً جاهزاً وشاهد تنبؤاً كاملاً حقيقياً على الفور. يشغّل النماذج نفسها على مدخلات مصطنعة — الأرقام حقيقية، والشخص لا.",
      csv_import: "تتابع هذا في مكان آخر أصلاً؟ نزّل القالب، واملأ عدة أيام دفعةً واحدة، وارفعه. كل صف صالح يشغّل تنبؤاً حقيقياً ويستقر في سجلك فوراً.",
      result_ring: "اقرأ هذه الحلقة من المنتصف إلى الخارج. الرقم الكبير ليس رقماً دقيقاً واحداً بل نطاق - فالنموذج له خطأ متوسط معروف، لذا يعرض أين تقع درجتك على الأرجح. وتحته مباشرة، الرقم الأصغر بعلامة ≈ هو أفضل تقدير واحد. الدائرة الداخلية الرفيعة هي مقياس من 0 إلى 100: تمتلئ باتجاه عقارب الساعة من الأعلى حتى درجتك، والعلامة البيضاء تشير إلى ذلك التقدير، والنطاق اللين حولها هو هامش عدم اليقين. أما الأقواس السميكة الأربعة الخارجية فشيء مختلف تماماً - إنها الأبعاد الأربعة وراء الدرجة، ولكل منها لونه الخاص في المفتاح أسفله.",
      result_confidence: "مدى ثقة المصنّف بالفئة التي اختارها لك. اقرأه بجانب الدرجة: جواب خاطئ واثق وجواب صحيح متردد يبدوان متطابقين حتى تنظر إلى هذا.",
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
      profile_badges: "تُكتسب حصراً مما سجّلته فعلاً. كل وسام يذكر العتبة التي احتاجها، فيمكنك التحقق بنفسك بدل أن تأخذ بكلامنا، ولا يمكن شراء أيٍّ منها ولا دفعه.",
      profile_tone: "يغيّر صياغة النصيحة — ألطف، أو أصرح، أو أكثر جفافاً. ولا يغيّر أبداً أي التوصيات تصلك ولا أولويتها.",
      privacy_controls: "صدّر كل ما يخزّنه هذا التطبيق عنك كملف، أو احذف حسابك وكل سجله نهائياً. الحذف لا يمكن التراجع عنه.",
    },
    zh: {
      plan_week_lock: "本周的计划是刻意在整周内固定的。它根据你自己的模式生成一次，然后就保持不变，这样第二次打卡就无法在你已勾选的方框底下悄悄换掉任务。重新生成是一个有意的选择，并且会清空本周的勾选，因为它们对应的任务已经不存在了。",
      plan_band: "本周瞄准的区间。它的中心是你已经记录的那些天的平均值——而不是某一次预测——它的宽度则是为你量身定的：一个模型学过你自己的日子通常离你自己的平均值有多远，所以平稳的一周得到的区间比起伏大的一周更窄。落在区间之外的那一天，正是值得你做决定的：算进去，还是标记为例外。",
      plan_personal_signal: "一个信号被标记，要么是因为它离健康目标很远，要么是因为它相对「你自己的正常水平」下滑了——取两者中更严重的那个。后半部分解释了为什么从你惯常的 8 小时降到 6.5 小时会被点名，尽管 6.5 本身并不吓人；前半部分解释了为什么一个一直很糟的习惯，不会仅因为「这就是你的常态」而被放过。",
      welcome: "好了——设置完成了，开始之前我带你快速转一圈。不到一分钟，如果你更想直接上手，角落里有跳过按钮。这里没有需要记住的东西；我在每个页面都在，随时可以再讲一遍。",
      welcome_checkin: "这是你真正要做的事：每天记录一次。两个真实的模型会读它——一个把你归入某个区间，一个给你一个百分制分数——每个结果都会附上它为什么落在那里的理由。规则是每天一次，不过今天记错了还可以改。",
      welcome_band: "在仪表盘上你看到的是这一周的一个区间，而不是一个数字，而且它属于你：模型会根据你自己的日子实际波动多大，算出它该有多宽。平稳的一周区间窄，起伏大的一周区间宽。当某一天落在区间之外，我会问你那天是不是发生了什么特别的事。这个区间的全部意义就在这里：它决定什么时候值得问一句。",
      welcome_week: "你的计划是七天，一天一天解锁——下一天要等到明天，哪怕你五分钟就做完了今天的。这些是习惯，不是一张勾完就算了的清单。把某一天的练习全部完成，你就会看到我会做什么。",
      welcome_book: "在「你的手记」里有一本日记——每天一页，用你自己的话写，绝不喂给任何模型，也不影响你的分数。下面是对你自己日子的一份读数：只在你的数据上做的拟合能说什么，以及它在哪里坦白自己还说不出什么。",
      welcome_friends: "好友联赛在你逐项勾选之前，不会向任何人展示你的任何信息，而且取消同样容易。那里的主角是你自己的进展；好友是并列展示，不是取而代之。",
      welcome_recovery: "一件实际的事。注册时你设置了一个安全问题——万一忘记密码，那就是你回来的路，因为这个应用没有邮件服务器，重置码会寄到你读不到的地方。你的答案就是回家的路，别弄丢了。",
      welcome_end: "就这些。在任何页面点我，我都会讲讲上面是什么，或者问教练——它只根据你自己的数字回答，不知道的时候就说不知道。去记录你的第一天吧；在认识你之前，这个应用其实没什么可说的。",
      onboarding_intro: "三个问题，一次一个，而且都不是定死的——之后随时可以在个人资料里改。它们不是问卷：每个答案都会改变这个应用优先呈现什么。目标决定哪些建议排在最前，用途决定你的屏幕时间怎么被解读，作息那道题则决定计划能不能依靠一套固定节奏。跳过也没关系；只是在你填之前，你拿到的会是通用版本。",
      schedule_regularity: "这个问题比看上去更重要。如果你每天都不一样——轮班、作息不规律——计划就不会再以「每晚固定就寝时间」这类你无法执行的建议开头，而是从你真正能守住的那一个锚点开始。请如实回答，而不是按理想状态回答。",
      progress_consistency: "这里原本把两件不同的事说成了一样。整周稳住一个好分数，和从一个差分数爬上来，不是一回事，你有权知道自己做到的是哪一个。",
      landing: "欢迎。它读的是你真实填报的习惯，给你一个分数并附上理由——不是星座，也不是感觉。这里每个数字都能追溯到你亲手填的东西；追溯不到的时候，它会告诉你。",
      dashboard: "这里是你的主页。圆环是你最近一次的真实分数，下面那条是你确实记录过的这一周，再往下是把那个数字推上推下的那些因素——一一点名，不是笼统概括。",
      checkin: "这个应用对你的全部了解都从这里开始——没有任何一栏是用一个看似合理的平均值预填的。填今天，提交，你会拿到一个真实的预测：一个类别、一个百分制分数，以及它为什么落在那里。",
      weekly: "这一周和上一周并排，还有一份根据你自己上次记录中最薄弱之处生成的七天计划。它一天一天解锁——明天那天要等到明天，因为这些是习惯，不是一张勾完就算的清单。",
      coach: "问它你的分数，或者问某一件具体的事——睡眠、专注，或者该先做什么。它只根据你真正记录过的东西回答，不够的时候它会直说，而不是把空缺补上。",
      analytics: "你的分数随时间的变化，以及一周里哪几天对你来说通常更好或更差。这些全都来自你自己记录的日子，所以你坚持得越久它能说的越多——第一天几乎什么都说不了。",
      whatif: "一个可以随便试的地方。改动一个习惯，看看真实的模型怎么变，而这一切都不会碰你已经保存的东西。你在这里做的任何事都不会被记成一天。",
      model: "准确率数字，就是它本来的样子。为一个从没见过的人做预测确实很难，所以你在这里看不到 99%——哪天你在任何应用上看到了，请保持怀疑。",
      profile: "你在这里是谁：你的头像、你的人格画像、你的徽章，以及你一开始设置的偏好。这些都会改变应用跟你说话的方式；但都不会改变模型读到的东西。",
      about: "这东西是怎么运作的、用什么训练的，以及从哪里开始它就说不出什么了。在你相信它给出的数字之前，值得花两分钟看看。",
      you: "这里有两样东西属于你而不属于这个项目：手记，每天一页、用你自己的话写，绝不接触任何模型；以及读数，它说明只在你自己的日子上做的拟合能讲什么、不能讲什么。两者都可以是空的——还没写的手记，和短到读不出规律的日子，都是诚实的回答。",
      about_roadmap: "十二站，从记录下来的一天，到你能据此行动的东西。地图上每个数字都在本仓库中实测；其中两站讲的是这个项目认为自己不能声称的东西——一个未通过基线检验、因而没有上线的七天回归模型，以及合成的训练数据。只展示好的一面的地图，不值得读。",
      about_team: "四个人，以及他们各自真正做了什么。个人资料里的每一句都是本人自己说的——这里没有任何一句是替谁写来填空的。",
      about_journal: "每天一页，用你自己的话写。它保存在你的账号里而不是这个浏览器，绝不喂给任何模型，也不影响你的健康分数——那个分数是模型从你的每日记录中读出的，而这里是你自己对这一天的看法。删除账号时，这本书也会一起被删除。",
      about_personal: "四项读数，每一项都可以说自己没有数据。时间是实测的——只在页面真正可见且处于焦点时计时，并设有上限，使整个周末开着的标签页无法声称两天。参照人群是模型据以拟合的合成训练数据，不是真实人群，面板会说明它读的是两种来源中的哪一种。模型是只在你自己的日子上做的岭回归，并且优先给出留一法 R² 而不是样本内 R²，因为在十天的量级上后者会自我美化。不足八天时它干脆不拟合。",
      settings_panel: "主题、环境音、音效和减少动效都是各自独立的开关——关掉一个绝不会关掉另一个。下面的演示模式会用一份逼真的示例历史填满整个应用，让你无需先记录真实的日子就能探索。",
      league: "在这里真正重要的数字是你自己的过去。好友只有在双方都同意后才会出现，而且你逐项决定每个人能看到什么——收回同样容易。",
      league_progress: "这才是真正的比较：你现在的分数对比你自己七天前的分数，再加上同一个真实模型认为你继续下去可能实际到达的位置。下面的好友只是背景，从来不是主角。",
      league_rules: "没有任何东西会自动分享。好友只能看到你勾选的内容，而且要在双方都接受这些规则之后，你也可以随时从这里撤回访问权限。",
      league_connect: "输入某人的邀请码，准确勾选对方接受后你愿意分享的内容，然后发送。在对方明确同意之前，他们什么也看不到。要亲自测试这个流程，需要第二个账号（一个隐私/无痕窗口就够了）——账号无法连接自己。",
      league_inbox: "这是你处理排行榜请求的通知箱——同意、拒绝、以及选择你回赠分享的内容，都在一个地方，而且永远不会有手机推送。",
      league_leaderboard: "所有分享了分数的人都按从高到低排名，你也在其中——你的位置就是你的分数挣来的。分数相同则并列。好友只会在他们本人同意与你分享的类别里出现。",
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
      wizard_time: "你描述的是哪一天。在这份数据里，周末的表现确实和工作日不同，所以填对它会改变你拿到的结果——这不是走个形式。",
      wizard_screen: "你的屏幕分钟数按类别拆分。你不需要填总数——应用会替你相加，所以各部分永远不会和总和矛盾。",
      wizard_device: "你的一天有多碎片化：通知、拿起手机的次数、打开应用的次数。在这份数据里，你查看的频率对专注度的预测力，往往强于总时长。",
      wizard_sleep: "实际睡了多少小时，以及你觉得有多解乏。睡眠是整个模型里最强的信号之一。",
      wizard_mental: "你自己报告的情绪和压力。请诚实作答，而不是乐观作答——虚高的输入只会给你一个虚高的分数，那对谁都没好处。",
      wizard_focus: "专注、效率、活动量和咖啡因。最后几项，然后你就能拿到结果了。",
      wizard_derived: "这些是根据你上面填的内容算出来的——模型需要的比率、密度和指数。你从来不会直接填它们，所以它们不可能和你的原始数字打架。",
      demo_profiles: "赶时间？加载一个现成的人物，立刻看到一次完整的真实预测。它用的是同样的模型，只是输入是编的——数字是真的，人不是。",
      csv_import: "已经在别处记录了？下载模板，一次填好几天，然后上传。每一行有效数据都会跑一次真实预测，并立即进入你的历史。",
      result_ring: "这个圆环从中间往外读。中间的大数字不是一个精确的数值，而是一个区间——模型有一个已知的平均误差，所以它给出的是你分数最可能落在的范围。紧挨在它下面、带 ≈ 符号的小数字是单一的最佳估计值。内圈那条细线是一个 0–100 的刻度：它从顶部开始顺时针填充到你的分数，白色刻度标记的就是那个估计值，周围柔和的色带表示上下浮动的余地。外圈四条粗弧是完全不同的东西——它们是分数背后的四个维度，每一个在下方图例里都有自己的颜色。",
      result_confidence: "分类器对它为你选的那个类别有多确定。请和分数一起看：在你查看这一项之前，一个自信的错答案和一个不确定的对答案看起来一模一样。",
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
      profile_badges: "严格根据你真正记录的内容获得。每枚徽章都写明它所需的门槛，你可以自己核对，不必只听我们说——而且它们都买不到、也推不动。",
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
    about: ['about', 'about_roadmap', 'about_team'],
    you: ['you', 'about_journal', 'about_personal'],
    landing: ['landing'],
    // Runs itself once, right after sign-up (app.js::maybeRunFirstRunTour).
    // Everywhere else the guide waits to be asked; this is the one
    // moment it earns going first, because a brand new account is
    // looking at a screen with no explanation of what any of it is for.
    onboarding: ['onboarding_intro', 'schedule_regularity'],
    // The one tour that starts itself, once, after a new account has
    // answered the preference questions (app.js::maybeRunFirstRunTour).
    // It waits until then on purpose: it used to fire ON the first
    // question, so the guide talked over the questionnaire it was
    // introducing. Everywhere else the guide waits to be asked.
    welcome: [
      'welcome', 'welcome_checkin', 'welcome_band', 'welcome_week',
      'welcome_book', 'welcome_friends', 'welcome_recovery', 'welcome_end',
    ],
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

  /* The running tour, if there is one. At most one at a time: two
     tours talking over each other is not a thing anybody wants, and
     the second one silently winning is worse. */
  let activeTour = null;

  /** Stop the tour, wherever it has got to. */
  function stopTour() {
    if (!activeTour) return false;
    clearTimeout(activeTour.timer);
    activeTour = null;
    removeSkipButton();
    if (window.DWMascot && window.DWMascot.say) window.DWMascot.say('');
    return true;
  }

  function removeSkipButton() {
    const existing = document.getElementById('dwTourSkip');
    if (existing) existing.remove();
  }

  const SKIP_LABEL = {
    en: 'Skip the tour', fa: 'رد کردن تور',
    ar: 'تخطَّ الجولة', zh: '跳过导览',
  };

  /* A real control, not a keyboard shortcut nobody is told about. The
     tour arrives uninvited on somebody's first minute in the app, so
     the way out has to be visible for as long as it is running. */
  function addSkipButton() {
    removeSkipButton();
    const lang = (window.DWI18n && window.DWI18n.get()) || 'en';
    const button = document.createElement('button');
    button.type = 'button';
    button.id = 'dwTourSkip';
    button.className = 'dw-tour-skip';
    button.textContent = SKIP_LABEL[lang] || SKIP_LABEL.en;
    button.addEventListener('click', stopTour);
    document.body.appendChild(button);
  }

  /** Walk a page's sections in order, one bubble at a time.
   *
   *  Steps are CHAINED rather than queued as N timeouts up front. The
   *  queued version could not be stopped: every bubble was already
   *  scheduled by the time the first one appeared, so "skip" could only
   *  ever hide the current line and then be talked over by the next
   *  seven. A tour that cannot be left is not a tour, it is an
   *  interruption - and this one starts itself, so leaving it has to
   *  work.
   *
   *  Runs once per page per browser unless forced.
   */
  function startTour(pageKey, opts) {
    opts = opts || {};
    const topics = topicsFor(pageKey);
    if (!topics.length) return false;

    const tourKey = TOUR_PREFIX + pageKey;
    if (!opts.force && localStorage.getItem(tourKey) === '1') return false;
    try { localStorage.setItem(tourKey, '1'); } catch (e) {}

    stopTour();
    const step = opts.stepMs || 7000;
    const tour = { timer: null, index: 0 };
    activeTour = tour;
    addSkipButton();

    (function next() {
      if (activeTour !== tour) return;         // stopped, or superseded
      if (tour.index >= topics.length) { stopTour(); return; }
      explain(topics[tour.index], { force: true, duration: step - 400 });
      tour.index += 1;
      tour.timer = setTimeout(next, step);
    })();
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
    explain, speak, attach, autoAttach, topicsFor, startTour, stopTour, TIPS,
    // Registry surface (see B-5): metadata, eligibility and fatigue.
    register, metaFor, canShow, explainBest, noteDismissed,
    isFatigued, inGlobalQuiet,
  };
})();
