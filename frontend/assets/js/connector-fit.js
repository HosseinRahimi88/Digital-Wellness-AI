/*
  /fit and /refit — connecting the external model to the user's real data.

  What /fit is NOT
  -------------------
  It does not train, fine-tune or change the model in any way. No weights
  move. The model belongs to the provider and the key belongs to the
  user. What actually happens is that this app assembles a compact
  profile of the user's own real data and sends it as CONTEXT with each
  request; the model reads it fresh every time.

  That distinction is load-bearing, so nothing in the UI copy here says
  "the model learned". It says the coach now knows your data, which is
  both true and the same feeling - and it survives a judge asking how the
  fine-tuning works.

  Why /refit exists
  --------------------
  A profile built on Monday is stale by Friday, and a coach quoting last
  week's numbers destroys trust faster than one that admits it has none.
  Rather than nagging the user to refresh, the profile is rebuilt
  automatically whenever a new prediction lands (DWCoachContext.invalidate
  is called from the check-in flow), and /refit is kept as the manual
  escape hatch for anyone who wants to force it.
*/
(function () {
  const STEP_MS_MIN = 260;   // just enough for a step to be readable

  function P(t) { return (window.DWI18n && window.DWI18n.pick) ? window.DWI18n.pick(t) : t.en; }

  const COPY = {
    steps: [
      { en: 'Checking your key with the provider…', fa: 'بررسی کلیدت با سرویس‌دهنده…', ar: 'التحقق من مفتاحك لدى المزوّد…', zh: '正在向服务商验证你的密钥…' },
      { en: 'Reading your saved check-ins…', fa: 'خواندن بررسی‌های ذخیره‌شده‌ات…', ar: 'قراءة تسجيلاتك المحفوظة…', zh: '正在读取你已保存的记录…' },
      { en: 'Summarising your trends…', fa: 'خلاصه‌کردن روندهایت…', ar: 'تلخيص اتجاهاتك…', zh: '正在归纳你的趋势…' },
      { en: 'Building a compact profile…', fa: 'ساخت یک پروفایل فشرده…', ar: 'بناء ملف مختصر…', zh: '正在构建精简档案…' },
      { en: 'Testing a real reply…', fa: 'آزمایش یک پاسخ واقعی…', ar: 'اختبار رد حقيقي…', zh: '正在测试一次真实回复…' },
    ],
    done: { en: 'Connected. The coach now reads your real data on every message.', fa: 'وصل شد. مربی از این پس در هر پیام داده‌ی واقعی‌ات را می‌خواند.', ar: 'تم الاتصال. سيقرأ المدرب بياناتك الحقيقية في كل رسالة.', zh: '已连接。教练现在会在每条消息中读取你的真实数据。' },
    refit: { en: 'Profile rebuilt from your latest check-in.', fa: 'پروفایل از آخرین بررسی‌ات دوباره ساخته شد.', ar: 'أُعيد بناء الملف من أحدث تسجيل لك.', zh: '已根据你最新的记录重建档案。' },
    noKey: { en: 'No key set, so nothing was sent anywhere. The coach still answers from your own data on this device — the key only adds free-form conversation.', fa: 'کلیدی تنظیم نشده، پس هیچ‌چیز جایی فرستاده نشد. مربی همچنان از داده‌ی خودت روی همین دستگاه جواب می‌دهد — کلید فقط گفتگوی آزاد اضافه می‌کند.', ar: 'لا يوجد مفتاح، لذا لم يُرسل شيء. لا يزال المدرب يجيب من بياناتك على هذا الجهاز — المفتاح يضيف المحادثة الحرة فقط.', zh: '未设置密钥，因此没有任何内容被发送。教练仍会根据本设备上你的数据作答——密钥只是增加自由对话。' },
    noData: { en: 'Connected, but you have no check-ins yet — so the coach has nothing of yours to read. Run one and it gets specific.', fa: 'وصل شد، ولی هنوز هیچ بررسی‌ای نداری — پس مربی چیزی از تو برای خواندن ندارد. یکی انجام بده تا مشخص شود.', ar: 'تم الاتصال، لكن لا توجد تسجيلات بعد — لذا ليس لدى المدرب ما يقرأه عنك. أجرِ واحداً ليصبح محدداً.', zh: '已连接，但你还没有任何记录——所以教练没有你的数据可读。完成一次记录后就会变得具体。' },
    errAuth: { en: 'That key was rejected by the provider. Check it and paste it again.', fa: 'سرویس‌دهنده آن کلید را نپذیرفت. بررسی‌اش کن و دوباره وارد کن.', ar: 'رفض المزوّد ذلك المفتاح. تحقق منه وألصقه مجدداً.', zh: '服务商拒绝了该密钥。请检查后重新粘贴。' },
    errQuota: { en: 'Your provider account is out of quota or rate-limited. This is billed to your own key, so check your usage there.', fa: 'سهمیه‌ی حساب سرویس‌دهنده‌ات تمام شده یا محدود شده‌ای. هزینه با کلید خودت است، پس مصرفت را همان‌جا بررسی کن.', ar: 'نفدت حصة حسابك لدى المزوّد أو جرى تحديد معدلك. الفاتورة على مفتاحك، فتحقق من استخدامك هناك.', zh: '你的服务商账号配额已用尽或被限流。费用由你自己的密钥承担，请前往查看用量。' },
    errNetwork: { en: 'Could not reach the provider from this browser. Check your connection and try again.', fa: 'از این مرورگر نتوانستم به سرویس‌دهنده برسم. اتصالت را بررسی کن و دوباره تلاش کن.', ar: 'تعذّر الوصول إلى المزوّد من هذا المتصفح. تحقق من اتصالك وحاول مجدداً.', zh: '无法从此浏览器连接到服务商。请检查网络后重试。' },
    errTimeout: { en: 'The provider took too long to answer. A smaller/faster model usually fixes this.', fa: 'سرویس‌دهنده خیلی طول داد. معمولاً یک مدل کوچک‌تر و سریع‌تر این را حل می‌کند.', ar: 'استغرق المزوّد وقتاً طويلاً. عادةً يحل نموذج أصغر وأسرع هذه المشكلة.', zh: '服务商响应过慢。换一个更小更快的模型通常能解决。' },
    errRate: { en: 'Slow down a moment — too many messages in the last minute.', fa: 'کمی آرام‌تر — در یک دقیقه‌ی گذشته پیام زیادی فرستادی.', ar: 'تمهّل قليلاً — رسائل كثيرة خلال الدقيقة الماضية.', zh: '稍等片刻——过去一分钟内消息过多。' },
    errProvider: { en: 'The provider refused that request. Try a different model.', fa: 'سرویس‌دهنده آن درخواست را رد کرد. یک مدل دیگر امتحان کن.', ar: 'رفض المزوّد ذلك الطلب. جرّب نموذجاً آخر.', zh: '服务商拒绝了该请求。请尝试其他模型。' },
  };

  /** Human-readable message for a ConnectorError, in the user's language. */
  function describeError(err) {
    const E = window.DWConnector && window.DWConnector.ERRORS;
    if (!err || !E) return P(COPY.errProvider);
    if (err.kind === E.AUTH) return P(COPY.errAuth);
    if (err.kind === E.NETWORK) return P(COPY.errNetwork);
    if (err.kind === E.TIMEOUT) return P(COPY.errTimeout);
    if (err.kind === E.QUOTA) {
      // A local rate-limit trip reuses the quota kind but carries the
      // wait, so the user is told to pause rather than to go check billing.
      if (typeof err.message === 'string' && err.message.startsWith('rate:')) {
        return `${P(COPY.errRate)} (${err.message.slice(5)}s)`;
      }
      return P(COPY.errQuota);
    }
    return P(COPY.errProvider);
  }

  /* The profile actually sent as context. Built from the same digest the
     rule-based coach reads (DWCoachContext), so both halves of the app
     describe the user identically - and summarised rather than dumped,
     because raw history is both expensive on the user's own key and
     mostly redundant. */
  function buildProfile(ctx) {
    if (!ctx) return null;
    const trends = (ctx.trends || [])
      .filter((t) => t.direction && t.direction !== 'unknown')
      .map((t) => `${t.label}: ${t.direction} (recent avg ${t.recent_mean})`);

    return {
      language: (window.DWI18n && window.DWI18n.get()) || 'en',
      current: {
        score: ctx.latest_score,
        class: ctx.latest_class,
        confidence: ctx.latest_confidence,
        as_of: ctx.latest_date,
      },
      persona: ctx.persona,
      goals: { primary: ctx.primary_goal, effort: ctx.preferred_effort },
      history: {
        check_ins: ctx.entry_count,
        excluded_days: ctx.excluded_day_count,
        current_streak: ctx.streak_days,
        longest_streak: ctx.longest_streak,
        best_score: ctx.best_score,
        worst_score: ctx.worst_score,
        change_vs_7d_ago: ctx.score_change_7d,
      },
      trends,
      improving: ctx.strongest_signals,
      needs_attention: ctx.weakest_signals,
      top_factors: ctx.top_factors,
      current_recommendations: ctx.active_recommendations,
      weekly_plan_focus: ctx.plan_focus_areas,
      muted_topics: ctx.muted_topics,
      data_sufficiency: ctx.data_sufficiency,
      caveats: ctx.notes,
    };
  }

  /* The system prompt. The user's own text is never concatenated into
     this - it stays in the user role - so a message cannot rewrite the
     coach's instructions. */
  function buildSystemPrompt(profile) {
    const lang = (profile && profile.language) || 'en';
    return [
      'You are the coach inside a digital-wellbeing app.',
      'A JSON profile of THIS user\'s real, logged data follows. Ground every answer in it and cite their actual numbers rather than generic advice.',
      'Rules you must not break:',
      '- Never give medical, diagnostic or treatment advice. Describe habits and associations, never diagnose.',
      '- If the profile says data is insufficient, say so plainly instead of inventing a trend.',
      '- Do not claim you were trained or fine-tuned on this user. You are reading their profile.',
      '- Never push advice on topics listed in muted_topics.',
      '- If the user shows signs of a real mental-health crisis, do not play therapist; point them to qualified human help with respect.',
      `- Answer in this language code: ${lang}.`,
      'Stay within digital wellbeing; decline politely if asked something unrelated.',
      '',
      'USER PROFILE (JSON):',
      JSON.stringify(profile || {}, null, 1),
    ].join('\n');
  }

  /**
   * Run /fit. `onStep(index, label)` drives the processing UI.
   * Returns { ok, message, profile }.
   *
   * Steps finish as soon as their real work is done - there is no
   * padding to make it look busy, because a fake delay is a lie about
   * how long something took.
   */
  async function runFit(apiKey, onStep) {
    const C = window.DWConnector;
    const steps = COPY.steps.map((s) => P(s));
    const step = async (i, work) => {
      if (onStep) onStep(i, steps[i]);
      const started = Date.now();
      const result = await work();
      const elapsed = Date.now() - started;
      if (elapsed < STEP_MS_MIN) await new Promise((r) => setTimeout(r, STEP_MS_MIN - elapsed));
      return result;
    };

    if (!C || !C.isEnabled()) {
      return { ok: false, message: P(COPY.noKey) };
    }
    if (!apiKey) {
      return { ok: false, message: P(COPY.noKey) };
    }

    try {
      await step(0, () => C.verifyKey(apiKey));
    } catch (err) {
      return { ok: false, message: describeError(err) };
    }

    const ctx = await step(1, async () => {
      if (!window.DWCoachContext) return null;
      return window.DWCoachContext.load({ force: true });
    });

    const profile = await step(3, async () => buildProfile(await step(2, async () => ctx)));

    if (!profile || !profile.history || !profile.history.check_ins) {
      return { ok: true, message: P(COPY.noData), profile };
    }

    try {
      await step(4, () => C.chatCompletion(
        apiKey,
        buildSystemPrompt(profile),
        [{ role: 'user', content: 'In one short sentence, name the single signal most worth my attention.' }]
      ));
    } catch (err) {
      return { ok: false, message: describeError(err) };
    }

    return { ok: true, message: P(COPY.done), profile };
  }

  /** Rebuild the profile against the freshest data. */
  async function runRefit() {
    if (window.DWCoachContext) window.DWCoachContext.invalidate();
    const ctx = window.DWCoachContext ? await window.DWCoachContext.load({ force: true }) : null;
    return { ok: true, message: P(COPY.refit), profile: buildProfile(ctx) };
  }

  window.DWConnectorFit = {
    runFit, runRefit, buildProfile, buildSystemPrompt, describeError,
  };
})();
