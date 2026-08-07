(function () {
  let stack;

  function ensureStack() {
    if (!stack) {
      stack = document.createElement('div');
      stack.className = 'toast-stack';
      document.body.appendChild(stack);
    }
    return stack;
  }

  const ICONS = { success: '✅', danger: '⚠️', info: 'ℹ️', warning: '⏳' };

  function show(message, type = 'info', duration = 4200) {
    const el = document.createElement('div');
    el.className = `toast toast--${type} toast-in`;
    el.innerHTML = `
      <span class="icon">${ICONS[type] || ICONS.info}</span>
      <span class="msg"></span>
      <span class="bar"></span>
    `;
    el.querySelector('.msg').textContent = message;
    ensureStack().appendChild(el);

    const bar = el.querySelector('.bar');
    requestAnimationFrame(() => {
      bar.style.transition = `width ${duration}ms linear`;
      bar.style.width = '0%';
      bar.style.width = '100%';
      requestAnimationFrame(() => { bar.style.width = '0%'; });
    });

    const remove = () => {
      el.classList.remove('toast-in');
      el.classList.add('toast-out');
      setTimeout(() => el.remove(), 340);
    };
    const timer = setTimeout(remove, duration);
    el.addEventListener('click', () => { clearTimeout(timer); remove(); });
    return el;
  }

  window.DWToast = {
    success: (m, d) => show(m, 'success', d),
    error: (m, d) => show(m, 'danger', d),
    info: (m, d) => show(m, 'info', d),
    warning: (m, d) => show(m, 'warning', d),
  };
})();
