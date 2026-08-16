/*
  Weekly shareable card: a downloadable PNG summary of the user's real
  week, drawn entirely client-side on a <canvas> - no server render, no
  screenshot service. Every number on it comes from a real API response
  (progress summary, persona identity, current-week average, last real
  result); nothing is invented for the sake of filling the layout.
*/
(function () {
  const W = 1080, H = 1350;

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function scoreColor(score) {
    if (score == null) return '#7ffbe0';
    if (score >= 66) return '#2be08e';
    if (score >= 40) return '#ffb347';
    return '#ff6b7a';
  }

  async function buildData() {
    let result = null;
    try { result = window.DWLastResult.get(); } catch (e) {}
    const [progress, persona, week] = await Promise.allSettled([
      window.DWApi.progressSummary(), window.DWApi.personaIdentity(), window.DWApi.currentWeek(),
    ]);
    return {
      score: result ? result.regression_score : null,
      prediction: result ? result.prediction : null,
      topFeature: result && result.shap_features && result.shap_features[0] ? result.shap_features[0].feature : null,
      weekAvg: week.status === 'fulfilled' && week.value ? week.value.avg_health_score : null,
      streak: progress.status === 'fulfilled' ? progress.value.streak_days : null,
      entryCount: progress.status === 'fulfilled' ? progress.value.entry_count : null,
      persona: persona.status === 'fulfilled' && persona.value.primary ? persona.value.primary.title : null,
    };
  }

  const LOCALE_FOR_LANG = { en: 'en-US', fa: 'fa-IR', ar: 'ar-SA', zh: 'zh-CN' };

  async function render(canvas) {
    const data = await buildData();
    const ctx = canvas.getContext('2d');
    const lang = (window.DWI18n && window.DWI18n.get()) || 'en';
    const pick = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : t.en);

    // Background
    const grad = ctx.createLinearGradient(0, 0, W, H);
    grad.addColorStop(0, '#061019');
    grad.addColorStop(1, '#0c2436');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    // Decorative glow blobs
    const blob = (x, y, r, color) => {
      const g = ctx.createRadialGradient(x, y, 0, x, y, r);
      g.addColorStop(0, color); g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
    };
    blob(120, 140, 420, 'rgba(34,245,198,.22)');
    blob(960, 1200, 460, 'rgba(58,167,255,.20)');

    // Header
    ctx.fillStyle = '#eafcf6';
    ctx.font = '600 40px Sora, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(pick({
      en: 'My Digital Wellness Week', fa: 'سلامت دیجیتال هفته‌ی من',
      ar: 'أسبوعي في العافية الرقمية', zh: '我的数字健康周报',
    }), 70, 130);
    ctx.font = '400 26px Inter, sans-serif';
    ctx.fillStyle = 'rgba(234,252,246,.65)';
    ctx.fillText(new Date().toLocaleDateString(LOCALE_FOR_LANG[lang] || 'en-US', { year: 'numeric', month: 'long', day: 'numeric' }), 70, 172);

    // Score ring card
    roundRect(ctx, 70, 240, W - 140, 420, 36);
    ctx.fillStyle = 'rgba(255,255,255,.05)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,.12)';
    ctx.lineWidth = 2;
    ctx.stroke();

    const cx = W / 2, cy = 450, r = 150;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,.12)';
    ctx.lineWidth = 22;
    ctx.stroke();

    const col = scoreColor(data.score);
    if (data.score != null) {
      ctx.beginPath();
      ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + (Math.PI * 2 * Math.max(0, Math.min(1, data.score / 100))));
      ctx.strokeStyle = col;
      ctx.lineWidth = 22;
      ctx.lineCap = 'round';
      ctx.stroke();
    }

    ctx.fillStyle = '#fff';
    ctx.textAlign = 'center';
    ctx.font = '700 96px Space Grotesk, sans-serif';
    ctx.fillText(data.score != null ? String(Math.round(data.score)) : '--', cx, cy + 30);
    ctx.font = '500 26px Inter, sans-serif';
    ctx.fillStyle = 'rgba(234,252,246,.7)';
    ctx.fillText(pick({
      en: 'Wellness score', fa: 'امتیاز سلامت دیجیتال', ar: 'درجة العافية الرقمية', zh: '数字健康分数',
    }), cx, cy + 78);

    // Stats row
    const stats = [
      { label: pick({ en: 'Week avg', fa: 'میانگین هفته', ar: 'متوسط الأسبوع', zh: '本周平均' }), value: data.weekAvg != null ? Math.round(data.weekAvg) : '—' },
      { label: pick({ en: 'Streak', fa: 'رکورد پیاپی', ar: 'السلسلة المتتالية', zh: '连续记录' }), value: data.streak != null ? `${data.streak}d` : '—' },
      { label: pick({ en: 'Days logged', fa: 'روزهای ثبت‌شده', ar: 'الأيام المسجَّلة', zh: '已记录天数' }), value: data.entryCount != null ? data.entryCount : '—' },
    ];
    const statY = 740;
    const statW = (W - 140) / 3;
    ctx.textAlign = 'center';
    stats.forEach((s, i) => {
      const x = 70 + statW * i + statW / 2;
      ctx.font = '700 54px Space Grotesk, sans-serif';
      ctx.fillStyle = '#7ffbe0';
      ctx.fillText(String(s.value), x, statY);
      ctx.font = '400 24px Inter, sans-serif';
      ctx.fillStyle = 'rgba(234,252,246,.65)';
      ctx.fillText(s.label, x, statY + 36);
    });

    // Persona + top factor card
    roundRect(ctx, 70, 830, W - 140, 300, 30);
    ctx.fillStyle = 'rgba(255,255,255,.05)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,.1)';
    ctx.stroke();

    ctx.textAlign = 'left';
    ctx.font = '600 30px Sora, sans-serif';
    ctx.fillStyle = '#fff';
    ctx.fillText(pick({ en: 'Persona', fa: 'پرسونا', ar: 'الشخصية', zh: '人格画像' }), 110, 900);
    ctx.font = '500 40px Inter, sans-serif';
    ctx.fillStyle = '#22f5c6';
    ctx.fillText(data.persona || pick({
      en: 'Not yet determined', fa: 'هنوز مشخص نشده', ar: 'لم تُحدَّد بعد', zh: '尚未确定',
    }), 110, 950);

    ctx.font = '600 30px Sora, sans-serif';
    ctx.fillStyle = '#fff';
    ctx.fillText(pick({ en: 'Top factor', fa: 'مهم‌ترین عامل', ar: 'أهم عامل', zh: '最重要的因素' }), 110, 1030);
    ctx.font = '500 36px Inter, sans-serif';
    ctx.fillStyle = 'rgba(234,252,246,.85)';
    const topLabel = data.topFeature
      ? (window.DWCoachLabels && window.DWCoachLabels[data.topFeature]) || String(data.topFeature).replace(/_/g, ' ')
      : pick({ en: 'Not enough data', fa: 'داده‌ی کافی نیست', ar: 'لا بيانات كافية', zh: '数据不足' });
    ctx.fillText(topLabel, 110, 1080);

    // Footer
    ctx.textAlign = 'center';
    ctx.font = '500 26px Inter, sans-serif';
    ctx.fillStyle = 'rgba(234,252,246,.55)';
    ctx.fillText(pick({
      en: 'Made with Digital Wellness AI — real ML scores, not a template',
      fa: 'ساخته‌شده با Digital Wellness AI — امتیازها واقعی‌اند',
      ar: 'صُنع بواسطة Digital Wellness AI — درجات حقيقية من نموذج تعلّم آلي، لا قالب جاهز',
      zh: '由 Digital Wellness AI 制作——真实的机器学习分数，不是模板',
    }), W / 2, 1300);

    return canvas;
  }

  function download(canvas, filename) {
    canvas.toBlob((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    }, 'image/png');
  }

  function init(canvasId, buttonId) {
    const canvas = document.getElementById(canvasId);
    const btn = document.getElementById(buttonId);
    if (!canvas || !btn) return;
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      try {
        await render(canvas);
        download(canvas, `digital-wellness-week-${new Date().toISOString().slice(0, 10)}.png`);
      } catch (e) {
        if (window.DWToast) window.DWToast.error(e.message);
      } finally {
        btn.disabled = false;
      }
    });
  }

  window.DWWeeklyCard = { init, render, download };
})();
