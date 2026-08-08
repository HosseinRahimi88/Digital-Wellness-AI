/* Client-side i18n: a flat key -> string dictionary per language
   (en/fa/ar/zh) plus RTL handling. `t(key)` always falls back to the
   English string (then the raw key) so a missing translation degrades
   visibly instead of throwing. `applyToDom()` fills every
   `[data-i18n]`/`[data-i18n-placeholder]` element on the page. */
(function () {
  const KEY = 'dwai_lang';
  const RTL_LANGS = ['ar', 'fa'];

  const dict = {
    en: {
      nav_home: 'Home', nav_features: 'Features', nav_app: 'Open App', nav_login: 'Log in', nav_logout: 'Log out',
      hero_eyebrow: 'AI-powered digital wellness', hero_title: 'Know your screen habits before they know you.',
      hero_lede: 'A real machine-learning model reads your daily digital habits and gives you an honest, explainable wellness score — plus a plan to actually improve it.',
      hero_cta_primary: 'Get my wellness score', hero_cta_secondary: 'See how it works',
      stat_accuracy: 'model accuracy', stat_features: 'signals analyzed', stat_users: 'checks run today',
      features_eyebrow: 'What you get', features_title: 'One check-in, a full picture',
      f1_title: 'Explainable predictions', f1_desc: 'Every score comes with SHAP-based reasons — you see exactly what pushed it up or down.',
      f2_title: 'Personalized coaching', f2_desc: 'Guardrail-checked recommendations tailored to the habits actually driving your score.',
      f3_title: 'Persona & cohort insight', f3_desc: 'See which behavioral persona you match and how you compare to everyone else.',
      f4_title: 'Track your trend', f4_desc: 'Daily history, weekly summaries, and streaks — not just a one-off number.',
      f5_title: 'Downloadable reports', f5_desc: 'Export a clean PDF wellness report any time you want a record.',
      f6_title: 'Private by design', f6_desc: 'Your data drives your predictions only — nothing sold, nothing shared.',
      persona_eyebrow: 'Built for everyone', persona_title: 'Whoever you are, this adapts to you',
      persona_1_tag: 'Students & gamers', persona_1_title: 'Late-night grind mode', persona_1_desc: 'Tuned to catch fragmented attention, night gaming, and social pressure.',
      persona_2_tag: 'Professionals', persona_2_title: 'Focus & burnout signals', persona_2_desc: 'Reads productivity vs. screen-time tradeoffs with a serious, data-first tone.',
      persona_3_tag: 'Everyone else', persona_3_title: 'General wellness', persona_3_desc: 'A balanced check-in for anyone curious about their digital habits.',
      quote_text: '"The recommendations felt like they were actually reading my data, not a generic checklist."',
      quote_cite: '— Early tester',
      intake_title: 'Before you dive in — what brings you here?', intake_sub: 'This just personalizes your experience. You can change it anytime.',
      intake_opt_sleep: 'Better sleep', intake_opt_focus: 'More focus', intake_opt_balance: 'Life balance', intake_opt_curious: 'Just curious',
      intake_cta: 'Continue to the app',
      security_note: 'Your responses are used only to compute your own predictions.',
      footer_rights: 'Digital Wellness AI — a research/demo project.', footer_terms: 'Terms', footer_privacy: 'Privacy', footer_source: 'Source',

      auth_login_title: 'Welcome back', auth_login_sub: 'Log in to see your wellness dashboard.',
      auth_register_title: 'Create your account', auth_register_sub: 'Takes less than a minute.',
      auth_email: 'Email', auth_password: 'Password', auth_name: 'Display name',
      auth_terms_prefix: 'I agree to the', auth_terms_link: 'Terms & Privacy Notice',
      auth_login_btn: 'Log in', auth_register_btn: 'Create account',
      auth_have_account: 'Already have an account?', auth_no_account: "Don't have an account?",
      auth_switch_login: 'Log in', auth_switch_register: 'Sign up',

      onboard_title: "Let's tailor things to you", onboard_sub: 'Optional — answer what you like, skip the rest.',
      onboard_goal: 'What would you most like to improve?', onboard_purpose: 'What do you mainly use your devices for?',
      onboard_schedule: 'What does your daily schedule look like?', onboard_skip: 'Skip for now', onboard_save: 'Save & continue',

      predict_title: 'Daily wellness check-in', predict_sub: 'Answer honestly — the model only works as well as your data.',
      demo_label: 'Or try a demo profile:', predict_next: 'Next', predict_back: 'Back', predict_submit: 'Get my prediction',
      derived_title: 'Auto-calculated (from what you entered above)',
      step_demographics: 'About you', step_time: 'Timing', step_screen: 'Screen time', step_device: 'Device habits',
      step_sleep: 'Sleep', step_mental: 'Mind & mood', step_focus: 'Focus & lifestyle',

      think_1: 'Reading your inputs…', think_2: 'Running the classifier…', think_3: 'Estimating your wellness score…',
      think_4: 'Explaining the result with SHAP…', think_5: 'Calibrating uncertainty…', think_6: 'Building your recommendations…',

      result_title: 'Your wellness result', result_confidence: 'Confidence', result_score_label: 'Wellness score',
      result_uncertainty: 'Uncertainty', result_shap_title: 'What drove this score', result_rec_title: 'Recommended for you',
      result_download: 'Download PDF report', result_again: 'Run another check-in', result_persona: 'Behavioral persona',
      empty_title: 'No check-ins yet', empty_desc: 'Run your first wellness check-in to see your score, trends, and recommendations here.',
      empty_cta: 'Start check-in',

      settings_title: 'Settings', settings_theme: 'Dark mode', settings_lang: 'Language', settings_music: 'Ambient sound',
      settings_animations: 'Rich animations', settings_reduce_motion: 'Reduce motion',

      toast_login_ok: 'Welcome back!', toast_register_ok: 'Account created — welcome!', toast_login_fail: 'Invalid email or password.',
      toast_register_fail: 'Could not create account.', toast_predict_ok: 'Prediction complete!', toast_predict_fail: 'Prediction failed — check your inputs.',
      toast_terms_required: 'Please accept the terms to continue.', toast_field_error: 'Please fix the highlighted fields.',
      toast_logged_out: 'Logged out.', toast_saved: 'Saved.',

      mascot_lines: [
        "Hey! I'm Pixel, your wellness buddy. Poke me if you're bored 👋",
        "Fun fact: I judge your screen time, but lovingly.",
        "Fill out the form — I promise it's less painful than doom-scrolling.",
        "Did you know? Consistent sleep is basically a cheat code for your score.",
        "I'm 90% code, 10% enthusiasm.",
      ],
      mascot_greeting: "Hi there! Ready to check in on your digital habits?",
      rec_none_title: 'Nothing to flag right now',
      rec_none_desc: 'Every top factor behind this score is already working in your favour — keep it up.',
      rec_success_label: 'Success metric',
      settings_reduce_motion: 'Reduce motion',

      result_dimension_title: 'Wellness dimension breakdown',
      result_dimension_hint: "A transparent, rule-based view of the same inputs, grouped by area — separate from the model's own score above.",
      result_rec_exclude_hint: 'Not interested in coaching on a topic? Use "Don\'t coach me on this" below — it only changes future recommendations, never your score.',
      rec_exclude_btn: "Don't coach me on this",
      rec_exclude_confirm: 'Got it — {category} recommendations are muted. You can undo this in Settings.',
      settings_excluded_topics: 'Muted coaching topics',
      settings_reset: 'Reset',
      settings_reset_done: 'Muted topics cleared.',
      dim_sleep: 'Sleep', dim_focus: 'Focus & Productivity', dim_emotional: 'Emotional Wellbeing',
      dim_screen_habits: 'Screen Habits', dim_physical: 'Physical & Lifestyle',

      profile_persona_title: 'Your persona',
      profile_persona_alts: 'Also matches:',
      profile_persona_empty: 'Run a check-in and your persona will be derived from your real habits.',
      profile_badges_title: 'Badges earned',
      profile_badges_hint: 'Each one comes from a real logged value — hover to see what it required.',
      profile_badges_empty: 'No badges yet. They unlock from real logged values, not from clicking around.',
      profile_progress_title: 'Your progress',
      profile_avatar_change: 'Change picture',
      profile_tone_title: 'How should advice sound?',
      profile_tone_hint: 'Wording only — this never changes which recommendations you get or their priority.',
      tone_gentle: 'Gentle', tone_direct: 'Direct', tone_clinical: 'Clinical',
      profile_privacy_title: 'Your data',
      profile_privacy_hint: 'Everything this app stores about you is yours to take or erase.',
      profile_export: '⬇️ Export my data',
      profile_delete: '🗑️ Delete my account',
      profile_delete_confirm: 'This permanently deletes your account and all history. Type your email ({email}) to confirm.',
      profile_delete_mismatch: 'That did not match your email — nothing was deleted.',
      profile_delete_done: 'Your account and history have been deleted.',
      progress_streak: 'Current streak', progress_longest: 'Longest streak', progress_entries: 'Check-ins',
      progress_wins: 'Since your last check-in', progress_before_after: 'Before vs. after',
      progress_within_noise: 'within model noise',

      csv_import_label: 'Got several days already logged elsewhere?',
      csv_download_template: '⬇️ Download CSV template',
      csv_upload_btn: '⬆️ Upload CSV',
      csv_import_success: '{count} day(s) imported and added to your history.',
      csv_import_failed_count: '{count} row(s) could not be imported:',
      csv_import_row_label: 'Row',
      csv_import_none_imported: 'Nothing could be imported — check the file against the template and try again.',

      heatmap_include_tip: 'Click to exclude {date} from your trend averages',
      heatmap_excluded_tip: '{date} is excluded from your trend averages — click to include it again',
      heatmap_excluded_toast: 'That day is now excluded from trend/average calculations. Its own prediction is unchanged.',
      heatmap_included_toast: 'That day is included in trend/average calculations again.',

      nav_dashboard: 'Dashboard', nav_checkin: 'Check-in', nav_weekly: 'Weekly Plan', nav_coach: 'AI Coach',
      nav_analytics: 'Analytics', nav_whatif: 'What-if', nav_model: 'Model', nav_profile: 'Profile', nav_about: 'About',
      result_dashboard: 'Go to Dashboard',

      dash_hello: 'Hi', dash_sub: "Here's where your digital wellness stands today.",
      dash_last_score: 'Last Score', dash_week_avg: "This Week's Avg", dash_entries: 'Check-ins Logged',
      dash_heatmap_title: 'This Week', dash_rec_title: 'From Your Last Check-in', dash_see_coach: 'See full AI Coach →',
      dash_cohort_title: 'You vs. Everyone Else',

      weekly_title: 'Weekly Plan & Insights', weekly_sub: "Your week at a glance, plus a rule-based 7-day plan built from your last check-in.",
      weekly_this_week: 'This Week', weekly_last_week: 'Previous Week',
      plan_empty_title: 'No plan yet', plan_empty_desc: 'Run a wellness check-in first — your plan is built from its real results.',

      coach_title: 'AI Coach', coach_sub: 'Your real, SHAP-driven recommendations from your most recent check-in.',
      coach_empty_title: 'No coaching yet', coach_empty_desc: "Run a wellness check-in and I'll read the real result to coach you — no generic advice.",

      analytics_title: 'Analytics', analytics_sub: 'Trends from your real check-in history.',
      analytics_trend_title: 'Wellness Score Over Time', analytics_weekday_title: 'Weekday Pattern', analytics_averages_title: 'Your Field Averages',

      model_title: 'Model Performance', model_sub: 'Real evaluation metrics saved at training time — not marketing numbers.',
      model_info_title: 'Model Metadata',

      profile_prefs_title: 'Preferences', profile_save: 'Save changes', profile_links_title: 'More',
      profile_view_model: 'View real model performance', profile_view_about: 'About this project',

      whatif_title: 'What-if Simulator', whatif_sub: 'Sweep one habit across its full range and see how your real model reacts.',
      whatif_empty_title: 'Nothing to simulate from yet', whatif_empty_desc: 'Run a wellness check-in first — the simulator starts from your real last submission.',
      whatif_field_label: 'Field to sweep', whatif_run: 'Run sweep',
      whatif_goalseek_title: 'Goal Seek', whatif_goalseek_sub: 'What value of this field gets me closest to a target score?',
      whatif_target_label: 'Target wellness score', whatif_run_goalseek: 'Find best value',

      about_title: 'Digital Wellness AI', about_lede: 'A real machine-learning system for reading digital habits — not a quiz, not a gimmick.',
      about_model_title: 'How the model works',
      about_model_p1: 'Every check-in is scored by two real trained models: a classifier (Healthy / Moderate / At Risk) and a regressor (0-100 wellness score), both trained on ~50 real behavioral and wellbeing signals.',
      about_model_p2: 'Every prediction ships with a SHAP explanation — the same numbers the model used, not a canned summary — plus a calibrated uncertainty estimate so you know how much to trust a given result.',
      about_privacy_title: 'Privacy & scope',
      about_privacy_p1: 'Your data is used only to compute your own predictions, history, and recommendations. Nothing is sold or shared with third parties.',
      about_privacy_p2: 'This is a research/demo project, not a certified medical product — recommendations are general digital-wellness guidance, not clinical advice.',
      about_quote: '"Explainable, not just a black-box score."',
    },
    fa: {
      nav_home: 'خانه', nav_features: 'قابلیت‌ها', nav_app: 'ورود به اپ', nav_login: 'ورود', nav_logout: 'خروج',
      hero_eyebrow: 'سلامت دیجیتال مبتنی بر هوش مصنوعی',
      hero_title: 'عادت‌های دیجیتالت را بشناس، قبل از اینکه آن‌ها تو را بشناسند.',
      hero_lede: 'یک مدل یادگیری ماشین واقعی، عادت‌های دیجیتال روزانه‌ات را می‌خواند و یک امتیاز سلامت صادقانه و قابل‌توضیح می‌دهد — به‌همراه برنامه‌ای برای بهتر کردنش.',
      hero_cta_primary: 'امتیاز سلامتم را بگیر', hero_cta_secondary: 'چطور کار می‌کند؟',
      stat_accuracy: 'دقت مدل', stat_features: 'سیگنال تحلیل‌شده', stat_users: 'بررسی امروز',
      features_eyebrow: 'چه چیزی به دست می‌آوری', features_title: 'یک بررسی، یک تصویر کامل',
      f1_title: 'پیش‌بینی‌های قابل‌توضیح', f1_desc: 'هر امتیاز با دلایل مبتنی بر SHAP همراه است — دقیقاً می‌بینی چه چیزی آن را بالا یا پایین برده.',
      f2_title: 'مربی‌گری شخصی', f2_desc: 'توصیه‌های بررسی‌شده، متناسب با عادت‌هایی که واقعاً امتیازت را می‌سازند.',
      f3_title: 'شخصیت رفتاری و مقایسه', f3_desc: 'ببین با کدام الگوی رفتاری هم‌خوانی داری و نسبت به بقیه کجا ایستاده‌ای.',
      f4_title: 'روندت را دنبال کن', f4_desc: 'تاریخچه‌ی روزانه و خلاصه‌ی هفتگی — نه فقط یک عدد یک‌باره.',
      f5_title: 'گزارش قابل دانلود', f5_desc: 'هر وقت خواستی یک گزارش PDF تمیز خروجی بگیر.',
      f6_title: 'حریم خصوصی از پایه', f6_desc: 'داده‌ات فقط پیش‌بینی خودت را می‌سازد — نه فروخته می‌شود، نه به اشتراک گذاشته می‌شود.',
      persona_eyebrow: 'ساخته‌شده برای همه', persona_title: 'هر که باشی، خودش را با تو تطبیق می‌دهد',
      persona_1_tag: 'دانشجو و گیمر', persona_1_title: 'حالت شب‌بیداری', persona_1_desc: 'تنظیم‌شده برای تشخیص توجه تکه‌تکه، بازی شبانه و فشار اجتماعی.',
      persona_2_tag: 'حرفه‌ای‌ها', persona_2_title: 'سیگنال‌های تمرکز و فرسودگی', persona_2_desc: 'موازنه‌ی بهره‌وری و زمان صفحه‌نمایش را با لحنی جدی و داده‌محور می‌خواند.',
      persona_3_tag: 'بقیه', persona_3_title: 'سلامت عمومی', persona_3_desc: 'یک بررسی متعادل برای هر کسی که درباره‌ی عادت‌های دیجیتالش کنجکاو است.',
      quote_text: '«توصیه‌ها واقعاً انگار داده‌ی من را خوانده بودند، نه یک فهرست کلیشه‌ای.»',
      quote_cite: '— کاربر آزمایشی',
      intake_title: 'قبل از شروع — چه چیزی تو را به اینجا آورد؟', intake_sub: 'این فقط تجربه‌ات را شخصی‌سازی می‌کند. هر وقت خواستی می‌توانی تغییرش بدهی.',
      intake_opt_sleep: 'خواب بهتر', intake_opt_focus: 'تمرکز بیشتر', intake_opt_balance: 'تعادل زندگی', intake_opt_curious: 'فقط کنجکاوم',
      intake_cta: 'ادامه به اپ',
      security_note: 'پاسخ‌هایت فقط برای محاسبه‌ی پیش‌بینی خودت استفاده می‌شود.',
      footer_rights: 'Digital Wellness AI — یک پروژه‌ی پژوهشی/نمایشی.', footer_terms: 'قوانین', footer_privacy: 'حریم خصوصی', footer_source: 'کد منبع',

      auth_login_title: 'خوش آمدی', auth_login_sub: 'وارد شو تا داشبورد سلامتت را ببینی.',
      auth_register_title: 'حساب کاربری بساز', auth_register_sub: 'کمتر از یک دقیقه طول می‌کشد.',
      auth_email: 'ایمیل', auth_password: 'رمز عبور', auth_name: 'نام نمایشی',
      auth_terms_prefix: 'با', auth_terms_link: 'قوانین و بیانیه‌ی حریم خصوصی موافقم',
      auth_login_btn: 'ورود', auth_register_btn: 'ساخت حساب',
      auth_have_account: 'از قبل حساب داری؟', auth_no_account: 'حساب نداری؟',
      auth_switch_login: 'ورود', auth_switch_register: 'ثبت‌نام',

      onboard_title: 'بیا همه‌چیز را برای تو تنظیم کنیم', onboard_sub: 'اختیاری — هر چه دوست داشتی جواب بده، بقیه را رد کن.',
      onboard_goal: 'بیشتر دوست داری چه چیزی را بهتر کنی؟', onboard_purpose: 'دستگاه‌هایت را عمدتاً برای چه کاری استفاده می‌کنی؟',
      onboard_schedule: 'برنامه‌ی روزانه‌ات چه شکلی است؟', onboard_skip: 'فعلاً رد کن', onboard_save: 'ذخیره و ادامه',

      predict_title: 'بررسی روزانه‌ی سلامت دیجیتال', predict_sub: 'صادقانه جواب بده — مدل فقط به‌اندازه‌ی داده‌ی تو خوب کار می‌کند.',
      demo_label: 'یا یک پروفایل نمونه را امتحان کن:', predict_next: 'بعدی', predict_back: 'قبلی', predict_submit: 'پیش‌بینی‌ام را بگیر',
      derived_title: 'محاسبه‌ی خودکار (از روی چیزی که بالا وارد کردی)',
      step_demographics: 'درباره‌ی تو', step_time: 'زمان', step_screen: 'زمان صفحه‌نمایش', step_device: 'عادت‌های دستگاه',
      step_sleep: 'خواب', step_mental: 'ذهن و حال', step_focus: 'تمرکز و سبک زندگی',

      think_1: 'در حال خواندن ورودی‌هایت…', think_2: 'در حال اجرای مدل دسته‌بندی…', think_3: 'در حال تخمین امتیاز سلامتت…',
      think_4: 'در حال توضیح نتیجه با SHAP…', think_5: 'در حال کالیبره‌کردن عدم قطعیت…', think_6: 'در حال ساخت توصیه‌هایت…',

      result_title: 'نتیجه‌ی سلامت دیجیتال تو', result_confidence: 'اطمینان', result_score_label: 'امتیاز سلامت',
      result_uncertainty: 'عدم قطعیت', result_shap_title: 'چه چیزی این امتیاز را ساخت', result_rec_title: 'پیشنهاد برای تو',
      result_download: 'دانلود گزارش PDF', result_again: 'یک بررسی دیگر', result_persona: 'الگوی رفتاری',
      empty_title: 'هنوز بررسی‌ای ثبت نشده', empty_desc: 'اولین بررسی سلامتت را انجام بده تا امتیاز، روندها و توصیه‌هایت اینجا ظاهر شوند.',
      empty_cta: 'شروع بررسی',

      settings_title: 'تنظیمات', settings_theme: 'حالت تاریک', settings_lang: 'زبان', settings_music: 'صدای محیطی',
      settings_animations: 'انیمیشن‌های کامل', settings_reduce_motion: 'کاهش حرکت',

      toast_login_ok: 'خوش برگشتی!', toast_register_ok: 'حساب ساخته شد — خوش آمدی!', toast_login_fail: 'ایمیل یا رمز عبور نادرست است.',
      toast_register_fail: 'ساخت حساب ممکن نشد.', toast_predict_ok: 'پیش‌بینی کامل شد!', toast_predict_fail: 'پیش‌بینی ناموفق بود — ورودی‌هایت را بررسی کن.',
      toast_terms_required: 'برای ادامه لطفاً قوانین را بپذیر.', toast_field_error: 'لطفاً فیلدهای مشخص‌شده را اصلاح کن.',
      toast_logged_out: 'خارج شدی.', toast_saved: 'ذخیره شد.',

      mascot_lines: [
        'سلام! من پیکسل‌ام، همراه سلامت دیجیتالت.',
        'من خروجی واقعی مدل را می‌خوانم — حدس نمی‌زنم.',
        'فرم را پر کن — قول می‌دهم از اسکرول بی‌هدف کم‌دردسرتر باشد.',
        'می‌دانستی؟ ثبات خواب تقریباً یک میان‌بر برای امتیازت است.',
      ],
      mascot_greeting: 'سلام! آماده‌ای عادت‌های دیجیتالت را بررسی کنیم؟',
      rec_none_title: 'فعلاً چیزی برای هشدار نیست',
      rec_none_desc: 'همه‌ی عوامل اصلی پشت این امتیاز به نفع تو کار می‌کنند — همین‌طور ادامه بده.',
      rec_success_label: 'معیار موفقیت',

      result_dimension_title: 'تفکیک ابعاد سلامت دیجیتال',
      result_dimension_hint: 'یک نمای شفاف و قانون‌محور از همین ورودی‌ها، دسته‌بندی‌شده بر اساس حوزه — جدا از امتیاز خود مدل در بالا.',
      result_rec_exclude_hint: 'به یک موضوع خاص علاقه نداری؟ از دکمه‌ی «درباره‌ی این موضوع مربی‌گری نکن» استفاده کن — این فقط توصیه‌های آینده را تغییر می‌دهد، نه امتیازت را.',
      rec_exclude_btn: 'درباره‌ی این موضوع مربی‌گری نکن',
      rec_exclude_confirm: 'باشه — توصیه‌های «{category}» بی‌صدا شدند. می‌تونی این را از تنظیمات برگردانی.',
      settings_excluded_topics: 'موضوعات بی‌صداشده',
      settings_reset: 'بازنشانی',
      settings_reset_done: 'موضوعات بی‌صداشده پاک شدند.',
      dim_sleep: 'خواب', dim_focus: 'تمرکز و بهره‌وری', dim_emotional: 'بهزیستی احساسی',
      dim_screen_habits: 'عادت‌های صفحه‌نمایش', dim_physical: 'فعالیت بدنی و سبک زندگی',

      profile_persona_title: 'پرسونای تو',
      profile_persona_alts: 'هم‌چنین شبیه:',
      profile_persona_empty: 'یک بررسی انجام بده تا پرسونایت از عادت‌های واقعی‌ات استخراج شود.',
      profile_badges_title: 'نشان‌های کسب‌شده',
      profile_badges_hint: 'هرکدام از یک مقدار واقعی ثبت‌شده می‌آید — نشانگر را ببر رویش تا شرطش را ببینی.',
      profile_badges_empty: 'هنوز نشانی نیست. این‌ها از مقادیر واقعی ثبت‌شده باز می‌شوند، نه از کلیک‌کردن.',
      profile_progress_title: 'پیشرفت تو',
      profile_avatar_change: 'تغییر تصویر',
      profile_tone_title: 'توصیه‌ها چه لحنی داشته باشند؟',
      profile_tone_hint: 'فقط نحوه‌ی بیان — این هرگز تغییر نمی‌دهد چه توصیه‌هایی می‌گیری یا اولویتشان چیست.',
      tone_gentle: 'ملایم', tone_direct: 'صریح', tone_clinical: 'بالینی',
      profile_privacy_title: 'داده‌ی تو',
      profile_privacy_hint: 'هرچه این اپ درباره‌ی تو ذخیره کرده مال توست که ببری یا پاک کنی.',
      profile_export: '⬇️ خروجی گرفتن از داده‌هایم',
      profile_delete: '🗑️ حذف حساب کاربری',
      profile_delete_confirm: 'این کار حساب و کل تاریخچه‌ات را برای همیشه حذف می‌کند. برای تأیید ایمیلت ({email}) را بنویس.',
      profile_delete_mismatch: 'با ایمیلت مطابقت نداشت — چیزی حذف نشد.',
      profile_delete_done: 'حساب و تاریخچه‌ات حذف شد.',
      progress_streak: 'رشته‌ی فعلی', progress_longest: 'بلندترین رشته', progress_entries: 'بررسی‌ها',
      progress_wins: 'از آخرین بررسی‌ات', progress_before_after: 'قبل در برابر بعد',
      progress_within_noise: 'در محدوده‌ی نویز مدل',

      csv_import_label: 'چند روز رو از قبل جای دیگه ثبت کردی؟',
      csv_download_template: '⬇️ دانلود قالب CSV',
      csv_upload_btn: '⬆️ آپلود CSV',
      csv_import_success: '{count} روز وارد و به تاریخچه‌ات اضافه شد.',
      csv_import_failed_count: '{count} ردیف وارد نشد:',
      csv_import_row_label: 'ردیف',
      csv_import_none_imported: 'هیچ‌چیز وارد نشد — فایل رو با قالب مقایسه کن و دوباره امتحان کن.',

      heatmap_include_tip: 'برای حذف {date} از میانگین‌های روندت کلیک کن',
      heatmap_excluded_tip: '{date} از میانگین‌های روندت حذف شده — برای برگرداندنش کلیک کن',
      heatmap_excluded_toast: 'اون روز الان از محاسبات روند/میانگین حذف شد. پیش‌بینی خود اون روز تغییری نکرده.',
      heatmap_included_toast: 'اون روز دوباره توی محاسبات روند/میانگین لحاظ می‌شه.',

      nav_dashboard: 'داشبورد', nav_checkin: 'بررسی', nav_weekly: 'برنامه‌ی هفتگی', nav_coach: 'مربی هوشمند',
      nav_analytics: 'تحلیل‌ها', nav_whatif: 'شبیه‌ساز', nav_model: 'مدل', nav_profile: 'پروفایل', nav_about: 'درباره',
      result_dashboard: 'رفتن به داشبورد',

      dash_hello: 'سلام', dash_sub: 'وضعیت سلامت دیجیتال تو امروز اینجاست.',
      dash_last_score: 'آخرین امتیاز', dash_week_avg: 'میانگین این هفته', dash_entries: 'تعداد بررسی‌ها',
      dash_heatmap_title: 'این هفته', dash_rec_title: 'از آخرین بررسی‌ات', dash_see_coach: 'مشاهده‌ی کامل مربی ←',
      dash_cohort_title: 'تو در مقایسه با بقیه',

      weekly_title: 'برنامه و بینش هفتگی', weekly_sub: 'نگاهی به هفته‌ات، به‌همراه یک برنامه‌ی ۷ روزه که از آخرین بررسی‌ات ساخته شده.',
      weekly_this_week: 'این هفته', weekly_last_week: 'هفته‌ی گذشته',
      plan_empty_title: 'هنوز برنامه‌ای نیست', plan_empty_desc: 'اول یک بررسی سلامت انجام بده — برنامه‌ات از نتیجه‌ی واقعی آن ساخته می‌شود.',

      coach_title: 'مربی هوشمند', coach_sub: 'توصیه‌های واقعی و مبتنی بر SHAP از آخرین بررسی‌ات.',
      coach_empty_title: 'هنوز مربی‌گری‌ای نیست', coach_empty_desc: 'یک بررسی سلامت انجام بده تا نتیجه‌ی واقعی را بخوانم و راهنمایی‌ات کنم — نه توصیه‌ی کلیشه‌ای.',

      analytics_title: 'تحلیل‌ها', analytics_sub: 'روندها از روی تاریخچه‌ی واقعی بررسی‌هایت.',
      analytics_trend_title: 'امتیاز سلامت در طول زمان', analytics_weekday_title: 'الگوی روزهای هفته', analytics_averages_title: 'میانگین‌های تو',

      model_title: 'عملکرد مدل', model_sub: 'معیارهای ارزیابی واقعی که هنگام آموزش ذخیره شده‌اند — نه اعداد تبلیغاتی.',
      model_info_title: 'اطلاعات مدل',

      profile_prefs_title: 'ترجیحات', profile_save: 'ذخیره‌ی تغییرات', profile_links_title: 'بیشتر',
      profile_view_model: 'مشاهده‌ی عملکرد واقعی مدل', profile_view_about: 'درباره‌ی این پروژه',

      whatif_title: 'شبیه‌ساز «چه می‌شود اگر»', whatif_sub: 'یک عادت را در کل بازه‌اش تغییر بده و ببین مدل واقعی‌ات چه واکنشی نشان می‌دهد.',
      whatif_empty_title: 'هنوز چیزی برای شبیه‌سازی نیست', whatif_empty_desc: 'اول یک بررسی سلامت انجام بده — شبیه‌ساز از آخرین ثبت واقعی تو شروع می‌کند.',
      whatif_field_label: 'فیلد مورد بررسی', whatif_run: 'اجرای شبیه‌سازی',
      whatif_goalseek_title: 'رسیدن به هدف', whatif_goalseek_sub: 'چه مقداری از این فیلد مرا به امتیاز هدف نزدیک‌تر می‌کند؟',
      whatif_target_label: 'امتیاز هدف', whatif_run_goalseek: 'پیدا کردن بهترین مقدار',

      about_title: 'Digital Wellness AI', about_lede: 'یک سامانه‌ی یادگیری ماشین واقعی برای خواندن عادت‌های دیجیتال — نه یک آزمون، نه یک ترفند تبلیغاتی.',
      about_model_title: 'مدل چطور کار می‌کند',
      about_model_p1: 'هر بررسی توسط دو مدل واقعی آموزش‌دیده امتیاز می‌گیرد: یک دسته‌بند (سالم / متوسط / در معرض خطر) و یک مدل رگرسیون (امتیاز ۰ تا ۱۰۰)، که هر دو روی حدود ۵۰ سیگنال واقعی رفتاری و بهزیستی آموزش دیده‌اند.',
      about_model_p2: 'هر پیش‌بینی با یک توضیح SHAP همراه است — همان اعدادی که مدل واقعاً استفاده کرده، نه یک خلاصه‌ی از پیش آماده — به‌علاوه‌ی یک تخمین کالیبره‌شده از عدم قطعیت تا بدانی چقدر می‌توانی به نتیجه اعتماد کنی.',
      about_privacy_title: 'حریم خصوصی و محدوده',
      about_privacy_p1: 'داده‌ات فقط برای محاسبه‌ی پیش‌بینی‌ها، تاریخچه و توصیه‌های خودت استفاده می‌شود. چیزی فروخته یا با شخص ثالثی به اشتراک گذاشته نمی‌شود.',
      about_privacy_p2: 'این یک پروژه‌ی پژوهشی/نمایشی است، نه یک محصول پزشکی تاییدشده — توصیه‌ها راهنمایی عمومی سلامت دیجیتال هستند، نه توصیه‌ی بالینی.',
      about_quote: '«قابل‌توضیح، نه فقط یک امتیاز جعبه‌سیاه.»',
    },
    ar: {
      nav_home: 'الرئيسية', nav_features: 'المزايا', nav_app: 'فتح التطبيق', nav_login: 'تسجيل الدخول', nav_logout: 'تسجيل الخروج',
      hero_eyebrow: 'عافية رقمية مدعومة بالذكاء الاصطناعي', hero_title: 'اعرف عاداتك الرقمية قبل أن تتحكم بك.',
      hero_lede: 'نموذج تعلّم آلي حقيقي يقرأ عاداتك الرقمية اليومية ويمنحك درجة عافية صادقة وقابلة للتفسير، مع خطة فعلية للتحسّن.',
      hero_cta_primary: 'احصل على درجتي', hero_cta_secondary: 'كيف يعمل؟',
      stat_accuracy: 'دقة النموذج', stat_features: 'مؤشر يُحلَّل', stat_users: 'فحص اليوم',
      features_eyebrow: 'ما الذي تحصل عليه', features_title: 'فحص واحد، صورة كاملة',
      f1_title: 'تنبؤات قابلة للتفسير', f1_desc: 'كل درجة تأتي بأسباب مبنية على SHAP — ترى بالضبط ما رفعها أو خفّضها.',
      f2_title: 'توجيه شخصي', f2_desc: 'توصيات مدروسة ومخصصة للعادات التي تؤثر فعلاً في درجتك.',
      f3_title: 'الشخصية السلوكية والمقارنة', f3_desc: 'اكتشف نمطك السلوكي وكيف تقارن بالآخرين.',
      f4_title: 'تابع تطورك', f4_desc: 'سجل يومي وملخصات أسبوعية، وليس مجرد رقم واحد.',
      f5_title: 'تقارير قابلة للتنزيل', f5_desc: 'صدّر تقرير PDF أنيقًا في أي وقت.',
      f6_title: 'خصوصية بالتصميم', f6_desc: 'بياناتك تُستخدم فقط لتوليد تنبؤاتك — لا تُباع ولا تُشارَك.',
      persona_eyebrow: 'مصمَّم للجميع', persona_title: 'أيًا كنت، يتكيّف هذا معك',
      persona_1_tag: 'طلاب ولاعبون', persona_1_title: 'وضع السهر الليلي', persona_1_desc: 'مضبوط لرصد تشتت الانتباه والألعاب الليلية والضغط الاجتماعي.',
      persona_2_tag: 'محترفون', persona_2_title: 'إشارات التركيز والاحتراق', persona_2_desc: 'يقرأ التوازن بين الإنتاجية ووقت الشاشة بنبرة جادة تعتمد على البيانات.',
      persona_3_tag: 'الجميع', persona_3_title: 'عافية عامة', persona_3_desc: 'فحص متوازن لأي شخص فضولي بشأن عاداته الرقمية.',
      quote_text: '"شعرت التوصيات وكأنها تقرأ بياناتي فعلاً، لا مجرد قائمة عامة."', quote_cite: '— مستخدم تجريبي',
      intake_title: 'قبل أن نبدأ — ما الذي أتى بك؟', intake_sub: 'هذا فقط لتخصيص تجربتك، ويمكنك تغييره لاحقًا.',
      intake_opt_sleep: 'نوم أفضل', intake_opt_focus: 'تركيز أكثر', intake_opt_balance: 'توازن حياتي', intake_opt_curious: 'مجرد فضول',
      intake_cta: 'المتابعة إلى التطبيق', security_note: 'تُستخدم إجاباتك فقط لحساب تنبؤاتك الخاصة.',
      footer_rights: 'Digital Wellness AI — مشروع بحثي/تجريبي.', footer_terms: 'الشروط', footer_privacy: 'الخصوصية', footer_source: 'المصدر',

      auth_login_title: 'أهلاً بعودتك', auth_login_sub: 'سجّل الدخول لرؤية لوحة عافيتك.',
      auth_register_title: 'أنشئ حسابك', auth_register_sub: 'يستغرق أقل من دقيقة.',
      auth_email: 'البريد الإلكتروني', auth_password: 'كلمة المرور', auth_name: 'الاسم المعروض',
      auth_terms_prefix: 'أوافق على', auth_terms_link: 'الشروط وسياسة الخصوصية',
      auth_login_btn: 'تسجيل الدخول', auth_register_btn: 'إنشاء حساب',
      auth_have_account: 'لديك حساب بالفعل؟', auth_no_account: 'ليس لديك حساب؟',
      auth_switch_login: 'تسجيل الدخول', auth_switch_register: 'إنشاء حساب',

      onboard_title: 'لنُخصص التجربة لك', onboard_sub: 'اختياري — أجب عمّا تريد وتخطَّ الباقي.',
      onboard_goal: 'ما الذي تودّ تحسينه أكثر؟', onboard_purpose: 'ما الاستخدام الرئيسي لأجهزتك؟',
      onboard_schedule: 'كيف يبدو جدولك اليومي؟', onboard_skip: 'تخطَّ الآن', onboard_save: 'حفظ ومتابعة',

      predict_title: 'فحص العافية اليومي', predict_sub: 'أجب بصدق — النموذج بجودة بياناتك فقط.',
      demo_label: 'أو جرّب ملفًا تجريبيًا:', predict_next: 'التالي', predict_back: 'رجوع', predict_submit: 'احصل على تنبؤي',
      derived_title: 'محسوبة تلقائيًا (مما أدخلته أعلاه)',
      step_demographics: 'عنك', step_time: 'التوقيت', step_screen: 'وقت الشاشة', step_device: 'عادات الجهاز',
      step_sleep: 'النوم', step_mental: 'الحالة النفسية', step_focus: 'التركيز ونمط الحياة',

      think_1: 'قراءة مدخلاتك…', think_2: 'تشغيل نموذج التصنيف…', think_3: 'تقدير درجة عافيتك…',
      think_4: 'تفسير النتيجة عبر SHAP…', think_5: 'معايرة عدم اليقين…', think_6: 'بناء توصياتك…',

      result_title: 'نتيجة عافيتك', result_confidence: 'الثقة', result_score_label: 'درجة العافية',
      result_uncertainty: 'عدم اليقين', result_shap_title: 'ما الذي أثّر في هذه الدرجة', result_rec_title: 'موصى به لك',
      result_download: 'تنزيل تقرير PDF', result_again: 'فحص جديد', result_persona: 'الشخصية السلوكية',
      empty_title: 'لا توجد فحوصات بعد', empty_desc: 'أجرِ أول فحص عافية لترى درجتك واتجاهاتك وتوصياتك هنا.',
      empty_cta: 'ابدأ الفحص',

      settings_title: 'الإعدادات', settings_theme: 'الوضع الداكن', settings_lang: 'اللغة', settings_music: 'صوت محيطي',
      settings_animations: 'حركات غنية', settings_reduce_motion: 'تقليل الحركة',

      toast_login_ok: 'أهلاً بعودتك!', toast_register_ok: 'تم إنشاء الحساب — أهلاً بك!', toast_login_fail: 'بريد إلكتروني أو كلمة مرور غير صحيحة.',
      toast_register_fail: 'تعذّر إنشاء الحساب.', toast_predict_ok: 'اكتمل التنبؤ!', toast_predict_fail: 'فشل التنبؤ — راجع مدخلاتك.',
      toast_terms_required: 'يرجى الموافقة على الشروط للمتابعة.', toast_field_error: 'يرجى تصحيح الحقول المظلّلة.',
      toast_logged_out: 'تم تسجيل الخروج.', toast_saved: 'تم الحفظ.',

      mascot_lines: [
        'مرحبًا! أنا بيكسل، رفيقك في العافية. اضغط عليّ إن شعرت بالملل 👋',
        'معلومة طريفة: أنا أراقب وقت شاشتك، لكن بمحبة.',
        'املأ النموذج — أعدك أنه أقل إيلامًا من التمرير بلا هدف.',
        'هل تعلم؟ النوم المنتظم يشبه اختصارًا سريًا لرفع درجتك.',
        'أنا 90% كود و10% حماس.',
      ],
      mascot_greeting: 'مرحبًا! هل أنت مستعد لفحص عاداتك الرقمية؟',
      rec_none_title: 'لا شيء يستدعي التنبيه الآن',
      rec_none_desc: 'كل العوامل الأساسية خلف هذه الدرجة تصب في مصلحتك — واصل.',
      rec_success_label: 'مؤشر النجاح',

      nav_dashboard: 'لوحة التحكم', nav_checkin: 'فحص جديد', nav_weekly: 'الخطة الأسبوعية', nav_coach: 'المدرّب الذكي',
      nav_analytics: 'التحليلات', nav_whatif: 'ماذا لو', nav_model: 'النموذج', nav_profile: 'الملف الشخصي', nav_about: 'حول',
      result_dashboard: 'الذهاب إلى لوحة التحكم',

      dash_hello: 'مرحبًا', dash_sub: 'هذا وضع عافيتك الرقمية اليوم.',
      dash_last_score: 'آخر درجة', dash_week_avg: 'متوسط هذا الأسبوع', dash_entries: 'عدد الفحوصات',
      dash_heatmap_title: 'هذا الأسبوع', dash_rec_title: 'من آخر فحص لك', dash_see_coach: 'عرض المدرّب الكامل ←',
      dash_cohort_title: 'أنت مقابل الجميع',

      weekly_title: 'الخطة الأسبوعية والرؤى', weekly_sub: 'نظرة على أسبوعك، بالإضافة إلى خطة ٧ أيام مبنية على آخر فحص لك.',
      weekly_this_week: 'هذا الأسبوع', weekly_last_week: 'الأسبوع الماضي',
      plan_empty_title: 'لا توجد خطة بعد', plan_empty_desc: 'أجرِ فحص عافية أولاً — تُبنى خطتك من نتائجه الحقيقية.',

      coach_title: 'المدرّب الذكي', coach_sub: 'توصياتك الحقيقية المبنية على SHAP من آخر فحص لك.',
      coach_empty_title: 'لا يوجد توجيه بعد', coach_empty_desc: 'أجرِ فحص عافية وسأقرأ النتيجة الحقيقية لتوجيهك — لا نصائح عامة.',

      analytics_title: 'التحليلات', analytics_sub: 'اتجاهات من سجل فحوصاتك الحقيقي.',
      analytics_trend_title: 'درجة العافية عبر الزمن', analytics_weekday_title: 'نمط أيام الأسبوع', analytics_averages_title: 'متوسطات حقولك',

      model_title: 'أداء النموذج', model_sub: 'مقاييس تقييم حقيقية محفوظة وقت التدريب — ليست أرقامًا تسويقية.',
      model_info_title: 'بيانات النموذج',

      profile_prefs_title: 'التفضيلات', profile_save: 'حفظ التغييرات', profile_links_title: 'المزيد',
      profile_view_model: 'عرض أداء النموذج الحقيقي', profile_view_about: 'حول هذا المشروع',

      whatif_title: 'محاكي ماذا لو', whatif_sub: 'غيّر عادة واحدة عبر نطاقها الكامل وشاهد كيف يستجيب نموذجك الحقيقي.',
      whatif_empty_title: 'لا يوجد شيء لمحاكاته بعد', whatif_empty_desc: 'أجرِ فحص عافية أولاً — يبدأ المحاكي من آخر إرسال حقيقي لك.',
      whatif_field_label: 'الحقل المراد تغييره', whatif_run: 'تشغيل المحاكاة',
      whatif_goalseek_title: 'البحث عن الهدف', whatif_goalseek_sub: 'ما القيمة التي تقرّبني أكثر من الدرجة المستهدفة؟',
      whatif_target_label: 'درجة العافية المستهدفة', whatif_run_goalseek: 'إيجاد أفضل قيمة',

      about_title: 'Digital Wellness AI', about_lede: 'نظام تعلّم آلي حقيقي لقراءة العادات الرقمية — ليس اختبارًا أو حيلة.',
      about_model_title: 'كيف يعمل النموذج',
      about_model_p1: 'كل فحص يُقيَّم بواسطة نموذجين حقيقيين مدرَّبين: مصنِّف (صحي / متوسط / معرض للخطر) ونموذج انحدار (درجة عافية من ٠-١٠٠)، كلاهما مدرَّب على نحو ٥٠ مؤشرًا سلوكيًا وصحيًا حقيقيًا.',
      about_model_p2: 'كل تنبؤ يأتي مع تفسير SHAP — الأرقام الحقيقية التي استخدمها النموذج، لا ملخص جاهز — إضافة إلى تقدير معايَر لعدم اليقين لتعرف مدى الثقة بالنتيجة.',
      about_privacy_title: 'الخصوصية والنطاق',
      about_privacy_p1: 'تُستخدم بياناتك فقط لحساب تنبؤاتك وسجلك وتوصياتك. لا تُباع ولا تُشارَك مع أي طرف ثالث.',
      about_privacy_p2: 'هذا مشروع بحثي/تجريبي، وليس منتجًا طبيًا معتمدًا — التوصيات إرشادات عامة للعافية الرقمية، لا نصيحة سريرية.',
      about_quote: '"قابل للتفسير، لا مجرد درجة صندوق أسود."',
    },
    zh: {
      nav_home: '首页', nav_features: '功能', nav_app: '打开应用', nav_login: '登录', nav_logout: '退出登录',
      hero_eyebrow: 'AI 驱动的数字健康', hero_title: '在屏幕习惯掌控你之前，先了解它。',
      hero_lede: '一个真实的机器学习模型会读取你每天的数字使用习惯，给出诚实、可解释的健康分数，并提供切实可行的改进方案。',
      hero_cta_primary: '获取我的健康分数', hero_cta_secondary: '了解运作方式',
      stat_accuracy: '模型准确率', stat_features: '分析的信号数', stat_users: '今日检测次数',
      features_eyebrow: '你将获得', features_title: '一次检测，完整画像',
      f1_title: '可解释的预测', f1_desc: '每个分数都附带基于 SHAP 的原因，让你清楚看到是什么拉高或拉低了它。',
      f2_title: '个性化建议', f2_desc: '经过审核的建议，专门针对真正影响你分数的习惯。',
      f3_title: '人格与群体洞察', f3_desc: '了解你属于哪种行为人格，以及与他人的比较情况。',
      f4_title: '追踪趋势', f4_desc: '每日历史记录、每周摘要，而不仅仅是一次性的数字。',
      f5_title: '可下载报告', f5_desc: '随时导出简洁的 PDF 健康报告。',
      f6_title: '隐私优先设计', f6_desc: '你的数据仅用于生成你自己的预测——绝不出售、绝不共享。',
      persona_eyebrow: '为每个人设计', persona_title: '无论你是谁，它都能适应你',
      persona_1_tag: '学生与玩家', persona_1_title: '深夜模式', persona_1_desc: '专门捕捉注意力碎片化、深夜游戏和社交压力。',
      persona_2_tag: '职场人士', persona_2_title: '专注与倦怠信号', persona_2_desc: '以数据为先、严肃的语气解读生产力与屏幕时间的权衡。',
      persona_3_tag: '所有人', persona_3_title: '通用健康检测', persona_3_desc: '适合任何对自己数字习惯感到好奇的人。',
      quote_text: '"这些建议感觉真的读懂了我的数据，而不是通用清单。"', quote_cite: '— 早期测试用户',
      intake_title: '开始之前——是什么带你来到这里？', intake_sub: '这只是为了个性化你的体验，随时可以修改。',
      intake_opt_sleep: '改善睡眠', intake_opt_focus: '提升专注', intake_opt_balance: '生活平衡', intake_opt_curious: '只是好奇',
      intake_cta: '继续进入应用', security_note: '你的回答仅用于计算你自己的预测结果。',
      footer_rights: 'Digital Wellness AI — 一个研究/演示项目。', footer_terms: '条款', footer_privacy: '隐私', footer_source: '源代码',

      auth_login_title: '欢迎回来', auth_login_sub: '登录查看你的健康仪表盘。',
      auth_register_title: '创建账户', auth_register_sub: '不到一分钟即可完成。',
      auth_email: '邮箱', auth_password: '密码', auth_name: '显示名称',
      auth_terms_prefix: '我同意', auth_terms_link: '条款与隐私声明',
      auth_login_btn: '登录', auth_register_btn: '创建账户',
      auth_have_account: '已经有账户？', auth_no_account: '还没有账户？',
      auth_switch_login: '登录', auth_switch_register: '注册',

      onboard_title: '让我们为你定制体验', onboard_sub: '可选——回答你愿意回答的，其余可跳过。',
      onboard_goal: '你最想改善什么？', onboard_purpose: '你使用设备的主要目的是什么？',
      onboard_schedule: '你的日常作息是怎样的？', onboard_skip: '暂时跳过', onboard_save: '保存并继续',

      predict_title: '每日健康检测', predict_sub: '请如实回答——模型的效果取决于你的数据质量。',
      demo_label: '或试用演示档案：', predict_next: '下一步', predict_back: '返回', predict_submit: '获取我的预测',
      derived_title: '自动计算（根据你上面输入的内容）',
      step_demographics: '关于你', step_time: '时间', step_screen: '屏幕时间', step_device: '设备使用习惯',
      step_sleep: '睡眠', step_mental: '心理与情绪', step_focus: '专注与生活方式',

      think_1: '正在读取你的输入…', think_2: '正在运行分类模型…', think_3: '正在估算你的健康分数…',
      think_4: '正在用 SHAP 解释结果…', think_5: '正在校准不确定性…', think_6: '正在生成你的建议…',

      result_title: '你的健康检测结果', result_confidence: '置信度', result_score_label: '健康分数',
      result_uncertainty: '不确定性', result_shap_title: '影响此分数的因素', result_rec_title: '为你推荐',
      result_download: '下载 PDF 报告', result_again: '再次检测', result_persona: '行为人格',
      empty_title: '暂无检测记录', empty_desc: '进行你的第一次健康检测，即可在此查看分数、趋势和建议。',
      empty_cta: '开始检测',

      settings_title: '设置', settings_theme: '深色模式', settings_lang: '语言', settings_music: '环境音效',
      settings_animations: '丰富动画', settings_reduce_motion: '减少动效',

      toast_login_ok: '欢迎回来！', toast_register_ok: '账户创建成功——欢迎！', toast_login_fail: '邮箱或密码不正确。',
      toast_register_fail: '无法创建账户。', toast_predict_ok: '预测完成！', toast_predict_fail: '预测失败——请检查你的输入。',
      toast_terms_required: '请先同意条款以继续。', toast_field_error: '请修正高亮显示的字段。',
      toast_logged_out: '已退出登录。', toast_saved: '已保存。',

      mascot_lines: [
        '嗨！我是 Pixel，你的健康小伙伴。无聊的话戳戳我 👋',
        '小知识：我会“评判”你的屏幕时间，但满怀爱意。',
        '填写表单吧——我保证比无脑刷手机轻松多了。',
        '你知道吗？规律的睡眠简直是提升分数的作弊码。',
        '我是 90% 代码，10% 热情。',
      ],
      mascot_greeting: '你好！准备好检测一下你的数字习惯了吗？',
      rec_none_title: '目前没有需要提醒的地方',
      rec_none_desc: '影响这个分数的每个主要因素都对你有利——继续保持。',
      rec_success_label: '成功指标',

      nav_dashboard: '仪表盘', nav_checkin: '检测', nav_weekly: '每周计划', nav_coach: 'AI 教练',
      nav_analytics: '分析', nav_whatif: '假设模拟', nav_model: '模型', nav_profile: '个人资料', nav_about: '关于',
      result_dashboard: '前往仪表盘',

      dash_hello: '你好', dash_sub: '这里是你今天的数字健康状况。',
      dash_last_score: '最近分数', dash_week_avg: '本周平均', dash_entries: '检测次数',
      dash_heatmap_title: '本周', dash_rec_title: '来自你上次检测', dash_see_coach: '查看完整 AI 教练 →',
      dash_cohort_title: '你与所有人的对比',

      weekly_title: '每周计划与洞察', weekly_sub: '一览你的一周，以及基于你上次检测生成的 7 天规则计划。',
      weekly_this_week: '本周', weekly_last_week: '上周',
      plan_empty_title: '还没有计划', plan_empty_desc: '请先进行一次健康检测——你的计划将基于真实结果生成。',

      coach_title: 'AI 教练', coach_sub: '基于你最近一次检测、真实 SHAP 驱动的建议。',
      coach_empty_title: '暂无指导', coach_empty_desc: '进行一次健康检测，我会读取真实结果来指导你——不是通用建议。',

      analytics_title: '分析', analytics_sub: '来自你真实检测历史的趋势。',
      analytics_trend_title: '健康分数变化趋势', analytics_weekday_title: '星期模式', analytics_averages_title: '你的各项平均值',

      model_title: '模型表现', model_sub: '训练时保存的真实评估指标——不是营销数字。',
      model_info_title: '模型元数据',

      profile_prefs_title: '偏好设置', profile_save: '保存更改', profile_links_title: '更多',
      profile_view_model: '查看真实模型表现', profile_view_about: '关于本项目',

      whatif_title: '假设模拟器', whatif_sub: '在完整范围内调整一个习惯，看看你的真实模型如何反应。',
      whatif_empty_title: '暂无可模拟的数据', whatif_empty_desc: '请先进行一次健康检测——模拟器将从你真实的最新提交开始。',
      whatif_field_label: '要调整的字段', whatif_run: '运行模拟',
      whatif_goalseek_title: '目标求解', whatif_goalseek_sub: '这个字段取什么值能让我最接近目标分数？',
      whatif_target_label: '目标健康分数', whatif_run_goalseek: '查找最佳值',

      about_title: 'Digital Wellness AI', about_lede: '一个真正用于解读数字习惯的机器学习系统——不是测验，也不是噱头。',
      about_model_title: '模型如何工作',
      about_model_p1: '每次检测都由两个真实训练的模型评分：一个分类器（健康/中等/高风险）和一个回归器（0-100 健康分数），二者都基于约 50 个真实的行为与健康信号训练而成。',
      about_model_p2: '每个预测都附带 SHAP 解释——模型实际使用的真实数字，而非套话总结——以及经过校准的不确定性估计，让你了解该结果的可信程度。',
      about_privacy_title: '隐私与范围',
      about_privacy_p1: '你的数据仅用于计算你自己的预测、历史记录和建议，绝不出售或与第三方共享。',
      about_privacy_p2: '这是一个研究/演示项目，并非经过认证的医疗产品——建议为通用数字健康指导，非临床建议。',
      about_quote: '"可解释，而不仅仅是一个黑箱分数。"',
    },
  };

  function get() {
    return localStorage.getItem(KEY) || 'en';
  }

  function t(key) {
    const lang = get();
    return (dict[lang] && dict[lang][key]) || dict.en[key] || key;
  }

  function applyToDom(root) {
    const scope = root || document;
    const lang = get();
    scope.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      el.textContent = t(key);
    });
    scope.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      el.setAttribute('placeholder', t(el.getAttribute('data-i18n-placeholder')));
    });
    // Tooltip/aria text for icon-only controls, which have no visible
    // label to translate via the textContent path above.
    scope.querySelectorAll('[data-i18n-title]').forEach((el) => {
      const label = t(el.getAttribute('data-i18n-title'));
      el.setAttribute('title', label);
      el.setAttribute('aria-label', label);
    });
    scope.querySelectorAll('[data-i18n-html]').forEach((el) => {
      el.innerHTML = t(el.getAttribute('data-i18n-html'));
    });
  }

  function setLang(lang) {
    localStorage.setItem(KEY, lang);
    document.documentElement.setAttribute('lang', lang);
    document.documentElement.setAttribute('dir', RTL_LANGS.includes(lang) ? 'rtl' : 'ltr');
    applyToDom();
    document.dispatchEvent(new CustomEvent('dwai:langchange', { detail: { lang } }));
  }

  function init() {
    setLang(get());
    document.querySelectorAll('[data-lang-select]').forEach((sel) => {
      sel.value = get();
      sel.addEventListener('change', (e) => setLang(e.target.value));
    });
  }

  window.DWI18n = { t, get, setLang, applyToDom, init, dict };
})();
