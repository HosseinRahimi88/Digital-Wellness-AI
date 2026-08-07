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
        p.textContent = `Also evaluated: ${otherModels.join(', ')} (this model performed best on cross-validation).`;
        container.appendChild(p);
      }
    }
  }

  const pct = (v) => `${Math.round(v * 1000) / 10}%`;
  renderTask(
    perf.classification, document.getElementById('clfMetrics'), document.getElementById('clfModelName'),
    [['accuracy', 'Accuracy', pct], ['precision', 'Precision', pct], ['recall', 'Recall', pct], ['f1', 'F1 Score', pct], ['roc_auc', 'ROC AUC', pct]]
  );
  renderTask(
    perf.regression, document.getElementById('regMetrics'), document.getElementById('regModelName'),
    [['R2', 'R² Score', (v) => (Math.round(v * 1000) / 1000)], ['MAE', 'MAE', (v) => Math.round(v * 100) / 100], ['RMSE', 'RMSE', (v) => Math.round(v * 100) / 100]]
  );

  const infoWrap = document.getElementById('modelInfoRows');
  const infoRows = [
    ['Classification target', perf.classification.model_info.target_column],
    ['Regression target', perf.regression.model_info.target_column],
    ['Features used (classification)', perf.classification.model_info.number_of_features],
    ['Features used (regression)', perf.regression.model_info.number_of_features],
    ['scikit-learn version', perf.classification.model_info.sklearn_version],
    ['Trained at', perf.classification.model_info.saved_at],
  ];
  infoRows.forEach(([label, val]) => {
    const div = document.createElement('div');
    div.className = 'metric-row';
    div.innerHTML = `<span class="name">${label}</span><span class="value">${val ?? '—'}</span>`;
    infoWrap.appendChild(div);
  });
});
