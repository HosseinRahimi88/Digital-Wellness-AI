/* Model Performance page controller: renders the real, current model
   metrics from GET /model-performance (accuracy/F1/R2/etc., read
   straight from artifacts/metrics*.json) - never a hardcoded number. */
document.addEventListener('DOMContentLoaded', async () => {
  const account = await window.DWShell.init('model');
  if (!account) return;

  const canvas = document.getElementById('bgCanvas');
  if (canvas) window.DWParticles.initNetwork(canvas, { density: 0.00005, linkDist: 125, speed: 0.14 });

  let perf;
  try {
    perf = await window.DWApi.modelPerformance();
  } catch (e) {
    window.DWToast.error(e.message);
    return;
  }

  function renderTask(task, container, nameEl, keyMetrics) {
    nameEl.textContent = task.model_name;
    const best = task.metrics.validation ? task.metrics.validation[task.metrics.best_model] : null;
    container.innerHTML = '';
    if (best) {
      keyMetrics.forEach(([key, label, fmt]) => {
        if (!(key in best)) return;
        const div = document.createElement('div');
        div.className = 'metric-row';
        const val = fmt ? fmt(best[key]) : best[key];
        div.innerHTML = `<span class="name">${label}</span><span class="value">${val}</span>`;
        container.appendChild(div);
      });
    }
    if (task.metrics.validation) {
      const otherModels = Object.keys(task.metrics.validation).filter((m) => m !== task.metrics.best_model);
      if (otherModels.length) {
        const p = document.createElement('p');
        p.className = 'muted'; p.style.fontSize = '.76rem'; p.style.marginTop = '10px';
        p.textContent = `${P(M.also_eval)}: ${otherModels.join(', ')} (${P(M.best_cv)}).`;
        container.appendChild(p);
      }
    }
  }

  const P = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : t.en);
  const M = {
    accuracy: { en: 'Accuracy', fa: 'دقت', ar: 'الدقة', zh: '准确率' },
    precision: { en: 'Precision', fa: 'صحت', ar: 'الإحكام', zh: '精确率' },
    recall: { en: 'Recall', fa: 'بازخوانی', ar: 'الاستدعاء', zh: '召回率' },
    f1: { en: 'F1 Score', fa: 'امتیاز F1', ar: 'درجة F1', zh: 'F1 分数' },
    roc: { en: 'ROC AUC', fa: 'ROC AUC', ar: 'ROC AUC', zh: 'ROC AUC' },
    r2: { en: 'R² Score', fa: 'امتیاز R²', ar: 'درجة R²', zh: 'R² 分数' },
    mae: { en: 'MAE', fa: 'MAE', ar: 'MAE', zh: 'MAE' },
    rmse: { en: 'RMSE', fa: 'RMSE', ar: 'RMSE', zh: 'RMSE' },
    clf_target: { en: 'Classification target', fa: 'هدف دسته‌بندی', ar: 'هدف التصنيف', zh: '分类目标' },
    reg_target: { en: 'Regression target', fa: 'هدف رگرسیون', ar: 'هدف الانحدار', zh: '回归目标' },
    feats_clf: { en: 'Features used (classification)', fa: 'ویژگی‌های استفاده‌شده (دسته‌بندی)', ar: 'الميزات المستخدمة (التصنيف)', zh: '使用的特征（分类）' },
    feats_reg: { en: 'Features used (regression)', fa: 'ویژگی‌های استفاده‌شده (رگرسیون)', ar: 'الميزات المستخدمة (الانحدار)', zh: '使用的特征（回归）' },
    sklearn: { en: 'scikit-learn version', fa: 'نسخه‌ی scikit-learn', ar: 'إصدار scikit-learn', zh: 'scikit-learn 版本' },
    trained_at: { en: 'Trained at', fa: 'زمان آموزش', ar: 'وقت التدريب', zh: '训练时间' },
    also_eval: { en: 'Also evaluated', fa: 'همچنین ارزیابی شد', ar: 'جرى تقييم أيضاً', zh: '同时评估了' },
    best_cv: { en: 'this model performed best on cross-validation', fa: 'این مدل در اعتبارسنجی متقابل بهترین عملکرد را داشت', ar: 'قدّم هذا النموذج أفضل أداء في التحقق المتقاطع', zh: '该模型在交叉验证中表现最佳' },
  };

  const pct = (v) => `${Math.round(v * 1000) / 10}%`;
  renderTask(
    perf.classification, document.getElementById('clfMetrics'), document.getElementById('clfModelName'),
    [['accuracy', P(M.accuracy), pct], ['precision', P(M.precision), pct], ['recall', P(M.recall), pct], ['f1', P(M.f1), pct], ['roc_auc', P(M.roc), pct]]
  );
  renderTask(
    perf.regression, document.getElementById('regMetrics'), document.getElementById('regModelName'),
    [['R2', P(M.r2), (v) => (Math.round(v * 1000) / 1000)], ['MAE', P(M.mae), (v) => Math.round(v * 100) / 100], ['RMSE', P(M.rmse), (v) => Math.round(v * 100) / 100]]
  );

  // "Why this model?" - built entirely from the real selection_score
  // (0.5 * validation metric + 0.5 * 5-fold CV metric mean, see
  // models/evaluator.py) already saved in metrics.json, never a
  // hand-picked marketing explanation.
  function prettyModelName(name) {
    return (name || '').split('_').map((w) => {
      if (w === 'xgboost') return 'XGBoost';
      return w.charAt(0).toUpperCase() + w.slice(1);
    }).join(' ');
  }

  function explainChoice(task, metricKey, metricLabel, fmt) {
    const val = task.metrics.validation;
    if (!val) return '';
    const pick = (t) => (window.DWI18n && window.DWI18n.pick ? window.DWI18n.pick(t) : t.en);
    const entries = Object.entries(val)
      .map(([name, m]) => ({ name, m }))
      .filter((e) => typeof e.m.selection_score === 'number')
      .sort((a, b) => b.m.selection_score - a.m.selection_score);
    if (!entries.length) return '';
    const winner = entries[0];
    const runnerUp = entries[1];
    const winnerName = prettyModelName(winner.name);
    let text = pick({
      en: `${winnerName} was selected because it had the highest overfitting-aware selection score (${winner.m.selection_score.toFixed(4)}) — a score that blends the validation-split ${metricLabel} with its 5-fold cross-validation ${metricLabel} mean 50/50, so the winner is a model that generalizes consistently, not just one that happens to look best on a single split.`,
      fa: `${winnerName} انتخاب شد چون بالاترین «امتیاز انتخاب مقاوم در برابر بیش‌برازش» را داشت (${winner.m.selection_score.toFixed(4)}) — امتیازی که ${metricLabel} روی داده‌ی اعتبارسنجی را با میانگین ${metricLabel} در اعتبارسنجی متقابل ۵-لایه، پنجاه‌پنجاه ترکیب می‌کند، تا مدلی انتخاب شود که پایدار تعمیم می‌یابد نه فقط روی یک تقسیم‌بندی خاص خوب به نظر می‌رسد.`,
      ar: `اختير ${winnerName} لأنه حصل على أعلى «درجة اختيار مقاومة للإفراط في التخصيص» (${winner.m.selection_score.toFixed(4)}) — وهي درجة تمزج ${metricLabel} على تقسيم التحقق مع متوسط ${metricLabel} في التحقق المتقاطع الخماسي بنسبة خمسين-خمسين، بحيث يكون الفائز نموذجاً يعمّم باستقرار لا نموذجاً بدا جيداً على تقسيم واحد فقط.`,
      zh: `${winnerName} 之所以被选中，是因为它拥有最高的「抗过拟合选择分数」（${winner.m.selection_score.toFixed(4)}）——这个分数把验证集上的 ${metricLabel} 与五折交叉验证 ${metricLabel} 均值按五五比例混合，因此胜出的是一个能稳定泛化的模型，而不只是在某一次划分上恰好表现好看的模型。`,
    });
    if (runnerUp && typeof runnerUp.m[metricKey] === 'number' && runnerUp.m[metricKey] > winner.m[metricKey]) {
      const runnerName = prettyModelName(runnerUp.name);
      text += pick({
        en: ` For full transparency: ${runnerName} actually had a higher raw ${metricLabel} on that same validation split (${fmt(runnerUp.m[metricKey])} vs ${fmt(winner.m[metricKey])}), but ${winnerName} was more stable and less overfit across cross-validation, which is exactly why it was picked instead.`,
        fa: ` برای شفافیت کامل: ${runnerName} در واقع ${metricLabel} خام بالاتری روی همان تقسیم اعتبارسنجی داشت (${fmt(runnerUp.m[metricKey])} در برابر ${fmt(winner.m[metricKey])})، اما در اعتبارسنجی متقابل ${winnerName} پایدارتر و کمتر بیش‌برازش‌شده بود، و دقیقاً به همین دلیل نهایتاً انتخاب شد.`,
        ar: ` لمزيد من الشفافية: حصل ${runnerName} فعلاً على ${metricLabel} خام أعلى على تقسيم التحقق نفسه (${fmt(runnerUp.m[metricKey])} مقابل ${fmt(winner.m[metricKey])})، لكن ${winnerName} كان أكثر استقراراً وأقل إفراطاً في التخصيص عبر التحقق المتقاطع، وهذا بالضبط سبب اختياره بدلاً منه.`,
        zh: ` 完全透明地说：${runnerName} 在同一个验证集划分上的原始 ${metricLabel} 其实更高（${fmt(runnerUp.m[metricKey])} 对比 ${fmt(winner.m[metricKey])}），但 ${winnerName} 在交叉验证中更稳定、过拟合更少，这正是它最终被选中的原因。`,
      });
    }
    return text;
  }

  document.getElementById('clfChoiceExplain').textContent =
    explainChoice(perf.classification, 'accuracy', 'accuracy', pct);
  document.getElementById('regChoiceExplain').textContent =
    explainChoice(perf.regression, 'R2', 'R²', (v) => (Math.round(v * 1000) / 1000));

  const infoWrap = document.getElementById('modelInfoRows');
  const infoRows = [
    [P(M.clf_target), perf.classification.model_info.target_column],
    [P(M.reg_target), perf.regression.model_info.target_column],
    [P(M.feats_clf), perf.classification.model_info.number_of_features],
    [P(M.feats_reg), perf.regression.model_info.number_of_features],
    [P(M.sklearn), perf.classification.model_info.sklearn_version],
    [P(M.trained_at), perf.classification.model_info.saved_at],
  ];
  infoRows.forEach(([label, val]) => {
    const div = document.createElement('div');
    div.className = 'metric-row';
    div.innerHTML = `<span class="name">${label}</span><span class="value">${val ?? '—'}</span>`;
    infoWrap.appendChild(div);
  });
});
